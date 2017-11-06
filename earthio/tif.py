'''
------------------

``earthio.tif``
~~~~~~~~~~~~~~~~~~~

Tools for reading GeoTiff files.  Typically use the interface through

    - :func:`earthio.load_layers`
    - :func:`earthio.`load_meta`

'''
from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import copy
import gc
import logging
import os

import numpy as np
import rasterio as rio
import xarray as xr

from earthio.metadata_selection import match_meta
from earthio.util import (geotransform_to_coords,
                          geotransform_to_bounds,
                          SPATIAL_KEYS,
                          _np_arr_to_coords_dims,
                          READ_ARRAY_KWARGS,
                          take_geo_transform_from_meta,
                          LayerSpec,
                          meta_strings_to_dict)

from six import string_types

logger = logging.getLogger(__name__)


__all__ = ['load_tif_meta',
           'load_dir_of_tifs_meta',
           'load_dir_of_tifs_array',]


def load_tif_meta(filename):
    '''Read the metadata of one TIF file

    Parameters:
        :filename: str: path and filename of TIF to read

    Returns:
        :file: TIF file
        :meta: Dictionary with meta data about the file, including;

            - **meta**: Meta attributes of the TIF file
            - **geo_transform**: transform
            - **bounds**: Bounds of the TIF
            - **height**: Hight of the TIF
            - **width**: Width of the TIF
            - **name**: The filename
            - **sub_dataset_name**: The filename

    '''
    r = rio.open(filename, driver='GTiff')
    if r.count != 1:
        raise ValueError('earthio.tif only reads tif files with 1 layer (shape of [1, y, x]). Found {} layers'.format(r.count))
    meta = {'meta': r.meta}
    meta['geo_transform'] = r.get_transform()
    meta['bounds'] = r.bounds
    meta['height'] = r.height
    meta['width'] = r.width
    meta['name'] = meta['sub_dataset_name'] = filename
    return r, meta_strings_to_dict(meta)


def ls_tif_files(dir_of_tiffs):
    tifs = os.listdir(dir_of_tiffs)
    tifs = [f for f in tifs if f.lower().endswith('.tif') or f.lower().endswith('.tiff')]
    return [os.path.join(dir_of_tiffs, t) for t in tifs]


def array_template(r, meta, **reader_kwargs):
    dtype = getattr(np, r.dtypes[0])

    if not 'window' in reader_kwargs:
        if 'height' in reader_kwargs:
            height = reader_kwargs['height']
        else:
            height = meta['height']
        if 'width' in reader_kwargs:
            width = reader_kwargs['width']
        else:
            width = meta['width']
    else:
        if 'height' in reader_kwargs:
            height = reader_kwargs['height']
        else:
            height = np.diff(reader_kwargs['window'][0])[0]
        if 'width' in reader_kwargs:
            width = reader_kwargs['width']
        else:
            width = np.diff(reader_kwargs['window'][0])[0]
    return np.empty((1, height, width), dtype=dtype)


def load_dir_of_tifs_meta(dir_of_tiffs, layer_specs=None, **meta):
    '''Load metadata from same-directory GeoTiffs representing
    different layers of the same image.

    Parameters:
        :dir_of_tiffs: Directory with GeoTiffs
        :layer_specs:   List of earthio.LayerSpec objects
        :meta:         included in returned metadata'''
    logger.debug('load_dir_of_tif_meta {}'.format(dir_of_tiffs))
    tifs = ls_tif_files(dir_of_tiffs)
    meta = copy.deepcopy(meta)
    layer_order_info = []
    for layer_idx, tif in enumerate(tifs):
        raster, layer_meta = load_tif_meta(tif)

        if layer_specs:
            for idx, layer_spec in enumerate(layer_specs):
                if (isinstance(layer_spec, LayerSpec) and match_meta(layer_meta, layer_spec)) or (isinstance(layer_spec, string_types) and layer_spec in tif):
                    layer_order_info.append((idx, tif, layer_spec, layer_meta))
                    break

        else:
            layer_name = 'layer_{}'.format(layer_idx)
            layer_order_info.append((layer_idx, tif, layer_name, layer_meta))

    if not layer_order_info or (layer_specs and (len(layer_order_info) != len(layer_specs))):
        logger.debug('len(layer_order_info) {}'.format(len(layer_order_info)))
        raise ValueError('Failure to find all layers specified by '
                         'layer_specs with length {}.\n'
                         'Found only {} of '
                         'them.'.format(len(layer_specs), len(layer_order_info)))
    # error if they do not share coords at this point
    layer_order_info.sort(key=lambda x:x[0])
    meta['layer_meta'] = [b[-1] for b in layer_order_info]
    meta['layer_order_info'] = [b[:-1] for b in layer_order_info]
    return meta

def open_prefilter(filename, meta, **reader_kwargs):
    '''Placeholder for future operations on open file rasterio
    handle like resample / aggregate or setting width, height, etc
    on load.  TODO see optional kwargs to rasterio.open'''
    try:
        r = rio.open(filename)
        raster = array_template(r, meta, **reader_kwargs)
        logger.debug('reader_kwargs {} raster template shape {}'.format(reader_kwargs, raster.shape))
        r.read(out=raster)
        return r, raster
    except Exception as e:
        logger.info('Failed to rasterio.open {}'.format(filename))
        raise

def load_dir_of_tifs_array(dir_of_tiffs, meta, layer_specs=None):
    '''Return an xr.Dataset where each subdataset is a DataArray

    Parameters:
        :dir_of_tiffs: directory of GeoTiff files where each is a
                      single layer raster
        :meta:     meta from earthio.load_dir_of_tifs_meta
        :layer_specs: list of earthio.LayerSpec objects,
                    defaulting to reading all subdatasets
                    as layers
    Returns:
        :X: xr.Dataset

    '''

    logger.debug('load_dir_of_tifs_array: {}'.format(dir_of_tiffs))
    layer_order_info = meta['layer_order_info']
    tifs = ls_tif_files(dir_of_tiffs)
    logger.info('Load tif files from {}'.format(dir_of_tiffs))

    if not len(layer_order_info):
        raise ValueError('No matching layers with '
                         'layer_specs {}'.format(layer_specs))
    native_dims = ('y', 'x')
    elm_store_dict = OrderedDict()
    attrs = {'meta': meta}
    attrs['layer_order'] = []
    for (idx, filename, layer_spec), layer_meta in zip(layer_order_info, meta['layer_meta']):
        layer_name = getattr(layer_spec, 'name', layer_spec)
        if not isinstance(layer_spec, string_types):
            reader_kwargs = {k: getattr(layer_spec, k)
                             for k in READ_ARRAY_KWARGS
                             if getattr(layer_spec, k)}
        else:
            reader_kwargs = {}
        if 'buf_xsize' in reader_kwargs:
            reader_kwargs['width'] = reader_kwargs.pop('buf_xsize')
        if 'buf_ysize' in reader_kwargs:
            reader_kwargs['height'] = reader_kwargs.pop('buf_ysize')
        if 'window' in reader_kwargs:
            reader_kwargs['window'] = tuple(map(tuple, reader_kwargs['window']))
            # TODO multx, multy should be handled here as well?

        handle, np_arr = open_prefilter(filename, layer_meta, **reader_kwargs)
        out = _np_arr_to_coords_dims(np_arr,
                 layer_spec,
                 reader_kwargs,
                 geo_transform=layer_meta.get('geo_transform'),
                 layer_meta=layer_meta,
                 handle=handle)
        np_arr, coords, dims, canvas, geo_transform = out
        elm_store_dict[layer_name] = xr.DataArray(np_arr,
                                                 coords=coords,
                                                 dims=dims,
                                                 attrs=layer_meta)

        attrs['layer_order'].append(layer_name)
    gc.collect()
    return xr.Dataset(elm_store_dict, attrs=attrs)
