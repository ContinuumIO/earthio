'''
--------------------

``earthio.hdf5``
~~~~~~~~~~~~~~~~~~~~~

Tools for reading HDF5 files.  Typically use the interface through

    - :func:`earthio.load_array`
    - :func:`earthio.load_meta`

'''

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import copy
import gc
import logging

import numpy as np
import xarray as xr

from earthio.util import (geotransform_to_bounds,
                          geotransform_to_coords,
                          Canvas,
                          BandSpec,
                          row_col_to_xy,
                          raster_as_2d,
                          READ_ARRAY_KWARGS,
                          take_geo_transform_from_meta,
                          window_to_gdal_read_kwargs,
                          meta_strings_to_dict)

from earthio import ElmStore
from earthio.metadata_selection import match_meta

__all__ = [
    'load_hdf5_meta',
    'load_hdf5_array',
]

logger = logging.getLogger(__name__)


def _nc_str_to_dict(nc_str):
    str_list = [g.split('=') for g in nc_str.split(';\n')]
    return dict([g for g in str_list if len(g) == 2])


def load_hdf5_meta(datafile):
    '''Load dataset and subdataset metadata from HDF5 file'''
    import gdal
    from gdalconst import GA_ReadOnly

    f = gdal.Open(datafile, GA_ReadOnly)
    sds = f.GetSubDatasets()
    band_metas = []
    for s in sds:
        f2 = gdal.Open(s[0], GA_ReadOnly)
        bm = dict()
        for k, v in f2.GetMetadata().items():
            vals = _nc_str_to_dict(v)
            bm.update(vals)
        band_metas.append(bm)
        band_metas[-1]['sub_dataset_name'] = s[0]

    meta = dict()
    for k, v in f.GetMetadata().items():
        vals = _nc_str_to_dict(v)
        meta.update(vals)

    return meta_strings_to_dict(dict(meta=meta,
                                band_meta=band_metas,
                                sub_datasets=sds,
                                name=datafile))

def load_subdataset(subdataset, attrs, band_spec, **reader_kwargs):
    '''Load a single subdataset'''
    import gdal
    data_file = gdal.Open(subdataset)
    raster = raster_as_2d(data_file.ReadAsArray(**reader_kwargs))
    #raster = raster.T
    if getattr(band_spec, 'stored_coords_order', ['y', 'x'])[0] == 'y':
        rows, cols = raster.shape
        dims = ('y', 'x')
    else:
        rows, cols = raster.T.shape
        dims = ('x', 'y')
    geo_transform = take_geo_transform_from_meta(band_spec, **attrs)
    if geo_transform is None:
        geo_transform = data_file.GetGeoTransform()
    coord_x, coord_y = geotransform_to_coords(cols,
                                              rows,
                                              geo_transform)


    canvas = Canvas(geo_transform=geo_transform,
                    buf_xsize=cols,
                    buf_ysize=rows,
                    dims=dims,
                    bounds=geotransform_to_bounds(cols, rows, geo_transform),
                    ravel_order='C')

    attrs['canvas'] = canvas
    attrs['geo_transform'] = geo_transform

    if dims == ('y', 'x'):
        coords = [('y', coord_y), ('x', coord_x)]
    else:
        coords = [('x', coord_x), ('y', coord_y)]
    return xr.DataArray(data=raster,
                        coords=coords,
                        dims=dims,
                        attrs=attrs)


def load_hdf5_array(datafile, meta, band_specs):
    '''Return an ElmStore where each subdataset is a DataArray

    Parameters:
        :datafile: filename
        :meta:     meta from earthio.load_hdf5_meta
        :band_specs: list of earthio.BandSpec objects,
                    defaulting to reading all subdatasets
                    as bands

    Returns:
        :es: An ElmStore
    '''
    import gdal
    from gdalconst import GA_ReadOnly

    logger.debug('load_hdf5_array: {}'.format(datafile))
    f = gdal.Open(datafile, GA_ReadOnly)
    sds = meta['sub_datasets']
    band_metas = meta['band_meta']
    band_order_info = []
    for band_idx, (band_meta, sd) in enumerate(zip(band_metas, sds)):
        if band_specs:
            for idx, bs in enumerate(band_specs):
                if match_meta(band_meta, bs):
                    band_order_info.append((idx, band_meta, sd, bs))
                    break
        else:
            band_order_info.append((band_idx, band_meta, sd, 'band_{}'.format(band_idx)))

    if band_specs and len(band_order_info) != len(band_specs):
        raise ValueError('Number of bands matching band_specs {} was not equal '
                         'to the number of band_specs {}'.format(len(band_order_info), len(band_specs)))

    band_order_info.sort(key=lambda x:x[0])
    elm_store_data = OrderedDict()
    band_order = []
    for _, band_meta, sd, band_spec in band_order_info:
        if isinstance(band_spec, BandSpec):
            name = band_spec.name
            reader_kwargs = {k: getattr(band_spec, k)
                             for k in READ_ARRAY_KWARGS
                             if getattr(band_spec, k)}
        else:
            reader_kwargs = {}
            name = band_spec
        reader_kwargs = window_to_gdal_read_kwargs(**reader_kwargs)
        attrs = copy.deepcopy(meta)
        attrs.update(copy.deepcopy(band_meta))
        elm_store_data[name] = load_subdataset(sd[0], attrs, band_spec, **reader_kwargs)

        band_order.append(name)
    attrs = copy.deepcopy(attrs)
    attrs['band_order'] = band_order
    gc.collect()
    return ElmStore(elm_store_data, attrs=attrs)
