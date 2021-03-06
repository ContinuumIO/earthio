'''
------------

``elm.reader.util``
~~~~~~~~~~~~~~~~~~~
'''

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple, OrderedDict, Sequence
from itertools import product
import logging
import numbers
import re

import numpy as np
from rasterio.coords import BoundingBox
import scipy.interpolate as spi

from six import string_types, PY2
from xarray_filters.pipeline import Step

__all__ = ['xy_to_row_col', 'row_col_to_xy',
           'geotransform_to_coords', 'geotransform_to_bounds',
           'VALID_X_NAMES', 'VALID_Y_NAMES',
           'LayerSpec', 'set_na_from_meta',
           'take_geo_transform_from_meta', 'import_callable',
           'meta_strings_to_dict']
logger = logging.getLogger(__name__)

SPATIAL_KEYS = ('height', 'width', 'geo_transform', 'bounds')

READ_ARRAY_KWARGS = ('window', 'buf_xsize', 'buf_ysize',)

DEFAULT_COORDS_ORDER = ['y', 'x']
try:
    unicode
except NameError:
    unicode = str

def is_string(s):
    typ = (str, unicode)
    return isinstance(s, typ)


def mkdir_p(d):
    if not os.path.exists(d):
        os.mkdir(d)

def import_callable(func_or_not, required=True, context=''):
    '''Given a string spec of a callable like "numpy:mean",
    import the module and callable, returning the callable
    Parameters:
        func_or_not: function or string callable like "numpy:median"
        required: True, False whether to raise error or return None
        context: message to include in ValueError
    Returns:
        imported function if ok
    Raises:
        ValueError if not importable / callable and
        required=True (default)
    '''
    # TODO make sure this import_callable func is
    # not defined in two packages - this is a
    # copy currently from what was earthio.config
    if callable(func_or_not):
        return func_or_not
    context = context + ' -  e' if context else 'E'
    if func_or_not and (not isinstance(func_or_not, string_types) or func_or_not.count(':') != 1):
        raise ValueError('{}xpected {} to be an module:callable '
                         'if given'.format(context, repr(func_or_not)))
    if not func_or_not and not required:
        return
    elif not func_or_not:
        raise ValueError('{}xpected a callable, '
                         'got {}'.format(context, repr(func_or_not)))
    module, func = func_or_not.split(':')
    try:
        # The import statement in Python 2 expects (decoded) str types instead of unicode strings
        if PY2 and isinstance(func, unicode):
            func = func.encode('utf-8')
        mod = __import__(module, globals(), locals(), [func], 0)
    except Exception as e:
        tb = traceback.format_exc()
        raise ValueError('{}xpected module {} to be '
                         'imported but failed:\n{}'.format(context,func_or_not, tb))
    func = getattr(mod, func, None)
    if not callable(func):
        raise ValueError('{}xpected {} to be callable - '
                         'module was imported but attribute not found or is not '
                         'callable'.format(context, func_or_not))
    return func


class LayerSpec(Step): # get_params/set_params
    search_key = None
    search_value = None
    name = None
    key_re_flags = None
    value_re_flags = None
    buf_xsize = None
    buf_ysize = None
    window = None
    meta_to_geotransform = None
    stored_coords_order = None


VALID_X_NAMES = ('lon','longitude', 'x') # compare with lower-casing
VALID_Y_NAMES = ('lat','latitude', 'y') # same comment
VALID_Z_NAMES = ('depth', 'pressure', 'height', 'altitude', 'elevation', 'z')
VALID_TIME_NAMES = ('t', 'time', 'datetime', 'date')

DEFAULT_GEO_TRANSFORM = (-180, .1, 0, 90, 0, -.1)


def xy_to_row_col(x, y, geo_transform):
    ''' Get row and column idx's from x and y where
    x and y are the coordinates matching the upper left
    corner of cell'''
    col = np.int32((x - geo_transform[0]) / geo_transform[1])
    row = np.int32((y - geo_transform[3]) / geo_transform[5])
    return row, col

def row_col_to_xy(row, col, geo_transform):
    '''Return the x, y coords that correspond to the
    upper left corners of cells at row, col'''
    x = (col * geo_transform[1]) + geo_transform[0]
    y = (row * geo_transform[5]) + geo_transform[3]
    return x, y


def geotransform_to_coords(buf_xsize, buf_ysize, geo_transform):
    return row_col_to_xy(np.arange(buf_ysize), np.arange(buf_xsize), geo_transform)


def geotransform_to_bounds(buf_xsize, buf_ysize, geo_transform):
    left, bottom = row_col_to_xy(0, 0, geo_transform)
    right, top = row_col_to_xy(buf_ysize - 1, buf_xsize - 1, geo_transform)
    return BoundingBox(left, bottom, right, top)



def _np_arr_to_coords_dims(np_arr,
                 layer_spec,
                 reader_kwargs,
                 geo_transform=None,
                 layer_meta=None,
                 handle=None):

    layer_meta = layer_meta or OrderedDict()
    stored_coords_order = getattr(layer_spec, 'stored_coords_order', None)
    if stored_coords_order is None:
        stored_coords_order = DEFAULT_COORDS_ORDER
    yfirst = stored_coords_order[0] == 'y'
    shp = np_arr.shape
    if 1 in shp:
        np_arr = np_arr.squeeze()
    shp = np_arr.shape
    extra_dim = None
    stacks = None
    if len(shp) == 3:
        idx = np.argmin(shp)
        if idx == 0:
            xyshp = shp[1:]
        elif idx == 2:
            xyshp = shp[:-1]
        else:
            xyshp = None
        extra_dim = idx
        stacks = shp[idx]
    elif len(shp) == 2:
        xyshp = shp
    else:
        xyshp = None
    if xyshp:
        if yfirst:
            rows, cols = xyshp
            dims = ('y', 'x')
        else:
            rows, cols = xyshp
            dims = ('x', 'y')
        if extra_dim == 0:
            dims = ('level',) + dims
        elif extra_dim == 2:
            dims = dims + ('level',)
    else:
        dims = tuple('dim_{}'.format(idx) for idx in range(len(shp)))
    layer_meta.update(reader_kwargs)
    if geo_transform is not None:
        layer_meta['geo_transform'] = geo_transform
    else:
        geo_transform = take_geo_transform_from_meta(layer_spec, **layer_meta)
        layer_meta['geo_transform'] = geo_transform
    if stored_coords_order[0] == 'y':
        rows, cols = np_arr.shape
    else:
        rows, cols = np_arr.T.shape
    if reader_kwargs and 'buf_ysize' in layer_meta or 'buf_xsize' in layer_meta:
        h = layer_meta.get('height', layer_meta['buf_ysize'])
        w = layer_meta.get('width', layer_meta['buf_xsize'])
        multy = h / reader_kwargs.get('height', h)
        multx = w / reader_kwargs.get('width', w)
    else:
        multx = multy = 1.
    if geo_transform is None:
        trans_funcs = ('GetGeoTransform', # GDAL handle
                       'get_transform',   # rasterio handle
                       )
        for func in trans_funcs:
            func = getattr(handle, func, None)
            if func:
                break
        if not callable(func):
            raise ValueError('Expected file handle with .get_transform method')
        layer_meta['geo_transform'] = func()
    else:
        layer_meta['geo_transform'] = geo_transform
    layer_meta['geo_transform'] = np.array(layer_meta['geo_transform'], dtype=np.float64)
    layer_meta['geo_transform'][1]  *= multx
    layer_meta['geo_transform'][-1] *= multy

    coords_x, coords_y = geotransform_to_coords(cols,
                                                rows,
                                                layer_meta['geo_transform'])
    coords = [('y', coords_y), ('x', coords_x)]
    if not yfirst:
        coords = coords[::-1]
    if stacks:
        coords_stacks = [('level', np.arange(stacks))]
    if extra_dim == 0:
        coords = coords_stacks + coords
    elif extra_dim == 2:
        coords += coords_stacks
    attrs = dict(geo_transform=layer_meta['geo_transform'],
                 buf_xsize=cols,
                 buf_ysize=rows,
                 dims=dims,
                 bounds=geotransform_to_bounds(cols, rows, layer_meta['geo_transform']),
                 ravel_order='C')
    return np_arr, coords, dims, attrs


def window_to_gdal_read_kwargs(**reader_kwargs):
    if 'window' in reader_kwargs:
        window = reader_kwargs['window']
        y, x = map(tuple, window)
        xsize = int(np.diff(x)[0])
        ysize = int(np.diff(y)[0])
        xoff = x[0]
        yoff = y[0]
        r = {'xoff': xoff,
             'yoff': yoff,
             'xsize': xsize,
             'ysize': ysize,}
        r.update({k: v for k, v in reader_kwargs.items()
                  if k != 'window'})
        return r
    return reader_kwargs


def take_geo_transform_from_meta(layer_spec=None, required=True, **meta):
    if layer_spec and getattr(layer_spec, 'meta_to_geotransform', False):
        func = import_callable(layer_spec.meta_to_geotransform)
        geo_transform = func(**meta)
        if not isinstance(geo_transform, Sequence) or len(geo_transform) != 6:
            raise ValueError('layer_spec.meta_to_geotransform {} did not return a sequence of len 6'.format(layer_spec.meta_to_geotransform))
        return geo_transform
    elif required:
        geo_transform = grid_header_to_geo_transform(**meta)
        return geo_transform
    return None

GRID_HEADER_WORDS = ('REGISTRATION', 'BINMETHOD',
                     'LATITUDERESOLUTION', 'LONGITUDERESOLUTION',
                     ('NORTHBOUNDINGCOORD', 'NORTHERNMOSTLAT'),
                     ('SOUTHBOUNDINGCOORD', 'SOUTHERNMOSTLAT'),
                     ('EASTBOUNDINGCOORD', 'EASTERNMOSTLON'),
                     ('WESTBOUNDINGCOORD', 'WESTERNMOSTLON'),
                     'ORIGIN',)

def grid_header_to_geo_transform(**meta):
    '''Unwind an attrs dict, trying to find bounding box words
    that can be used to make a geo_transform object.

    Parameters:
        :meta:  some dict
    Returns:
        :geo_transform: tuple
    '''
    grid_header = {}
    for word1, v in meta.items():
        if isinstance(v, dict):
            geo_transform1 = grid_header_to_geo_transform(**v)
            if geo_transform1:
                return geo_transform1
            else:
                continue
        word1 = word1.upper()
        word = None
        for g in GRID_HEADER_WORDS:
            if isinstance(g, tuple):
                if any(gi for gi in g if gi in word1):
                    word = g[0]
            else:
                if g in word1:
                    word = g
        if not word:
            continue
        if "RESOLUTION" in word or "COORD" in word or 'MOSTLAT' in word or 'MOSTLON' in word:
            grid_header[word] = float(v)
        else:
            grid_header[word] = v
    if not len(grid_header) >= 6:
        return None
    lat_res, s, n = (grid_header['LATITUDERESOLUTION'],
           grid_header['SOUTHBOUNDINGCOORD'],
           grid_header['NORTHBOUNDINGCOORD'])
    lon_res, e, w = (grid_header['LONGITUDERESOLUTION'],
           grid_header['EASTBOUNDINGCOORD'],
           grid_header['WESTBOUNDINGCOORD'])
    origin = grid_header.get('ORIGIN', 'NORTHWEST')
    if origin == 'SOUTHWEST':
        geo_transform = (w, lon_res, 0, s, 0, lat_res)
    elif origin == 'NORTHWEST':
        geo_transform = (w, lon_res, 0, n, 0, -lat_res)
    else:
        raise ValueError('Did not expect origin: {}'.format(origin))
    return geo_transform



VALID_RANGE_WORDS = ('^valid[\s\-_]*range',)
INVALID_RANGE_WORDS = ('invalid[\s\-_]*range',)
MISSING_VALUE_WORDS = ('missing[\s\-_]*value', 'invalid[\s\-\_]*value',)

def _case_insensitive_lookup(dic, lookup_list, has_seen):
    for k, pattern in product(dic, lookup_list):
        match = re.search(pattern, k, re.IGNORECASE)
        val = dic[k]
        if match:
            if isinstance(val, string_types):
                if ',' in val:
                    val = val.split(',')
                else:
                    val = val.split()
            if isinstance(val, Sequence):
                val = [float(v) for v in val]
            else:
                val = float(val)
            logger.debug('{} {}'.format(match, val))

            return val
        elif isinstance(val, dict):
            key = tuple(val) + (k, pattern)
            if key not in has_seen:
                has_seen.add(key)
                ret = _case_insensitive_lookup(val, lookup_list, has_seen)
                if ret:
                    return ret

def extract_valid_range(**attrs):
    return _case_insensitive_lookup(attrs, VALID_RANGE_WORDS, set())


def extract_missing_value(**attrs):
    return _case_insensitive_lookup(attrs, MISSING_VALUE_WORDS, set())


def extract_invalid_range(**attrs):
    return _case_insensitive_lookup(attrs, INVALID_RANGE_WORDS, set())


def _set_invalid_na(values, invalid):
    invalid = np.array(invalid, dtype=values.dtype)
    if len(invalid) == 2:
        values[(values > invalid[0])&(values < invalid[1])] = np.NaN
    else:
        values[values == invalid] = np.NaN


def _set_na_from_valid_range(values, valid_range):
    logger.debug('valid_range {}'.format(valid_range))
    valid_range = np.array(valid_range, dtype=values.dtype)
    if len(valid_range) == 2:
        logger.debug('==2')
        values[~((values >= valid_range[0])&(values <= valid_range[1]))] = np.NaN
    else:
        logger.info('Ignoring valid range metadata (does not have length of 2)')



def set_na_from_meta(dset, **kwargs):
    '''Set NaNs based on "valid_range" "invalid_range" and/or "missing"
     in xr.Dataset attrs or xr.DataArray attrs

    Parameters:
        :dset: xr.Dataset
        :kwargs: ignored

    Recursively searches dset's attrs for keys loosely matching:

     - "valid_range": expected value is a sequence of length 2
     - "invalid_range": expected value is a sequence of length 2
     - "missing": expected value is scalar

    Band attributes are also searched.

    For example with ``dset.layer_1.attrs.valid_range == [0, 1]`` all values in layer_1 outside (0, 1)
    would be NaN. With ``dset.attrs.valid_range == [0, 1]`` all values in all layers
    outside of (0, 1) would be assigned NaN.

    '''
    attrs = dset.attrs
    for layer in dset.data_vars:
        layer_arr = getattr(dset, layer)
        if 'int' in str(layer_arr.values.dtype):
            layer_arr.values = layer_arr.values.astype(np.float32)
    for idx, layer in enumerate(dset.data_vars):
        layer_arr = getattr(dset, layer)
        val = layer_arr.values
        invalid_range_b = extract_invalid_range(**layer_arr.attrs)
        if invalid_range_b is not None:
            logger.debug('Invalid range {}'.format(invalid_range_b))
            _set_invalid_na(val, invalid_range_b)
        valid_range_b = extract_valid_range(**layer_arr.attrs)
        if valid_range_b is not None:
            logger.debug('Valid range {}'.format(valid_range_b))
            _set_na_from_valid_range(val, valid_range_b)
        missing_value_b = extract_missing_value(**layer_arr.attrs)
        if missing_value_b is not None:
            logger.debug('Missing value {}'.format(missing_value_b))
            val[val == np.array([missing_value_b], dtype=val.dtype)[0]] = np.NaN


def _meta_strings_to_dict(s):
    if ';' in s and '=' in s and s.index('=') < s.index(';'):
        items = [_.strip() for _ in s.split(';')]
        items = [tuple(item.split('=')) for item in items]
        items = [(item if len(item) == 2 else item + (None,))
                 for item in items]
        return dict(items)
    return s


def meta_strings_to_dict(meta):
    '''Parses strings within old GDAL meta like:
    {u'HDF5_GLOBAL.FileHeader': u'DOI=Realtime;\nDOIshortName=3IMERGHH;\n}

    Splitting on ";" for items then on "="
    for key/value.  Value isNone where empty string is right of =
    '''
    if hasattr(meta, 'items'):
        for k, v in meta.items():
            if is_string(v):
                meta[k] = _meta_strings_to_dict(v)
            else:
                meta[k] = meta_strings_to_dict(v)
    elif isinstance(meta, Sequence) and not is_string(meta):
        meta = [meta_strings_to_dict(item) for item in meta]
    return meta

