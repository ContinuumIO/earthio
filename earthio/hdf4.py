'''
--------------------

``earthio.hdf4``
~~~~~~~~~~~~~~~~~~~~~

Tools for reading HDF4 files.  Typically use the interface through

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
                          row_col_to_xy,
                          _np_arr_to_coords_dims,
                          Canvas,
                          BandSpec,
                          READ_ARRAY_KWARGS,
                          take_geo_transform_from_meta,
                          window_to_gdal_read_kwargs,
                          meta_strings_to_dict)

__all__ = [
    'load_hdf4_meta',
    'load_hdf4_array',
]

logger = logging.getLogger(__name__)

def load_hdf4_meta(datafile):
    '''Load meta and band_meta for a datafile'''
    import gdal
    from gdalconst import GA_ReadOnly
    f = gdal.Open(datafile, GA_ReadOnly)
    sds = f.GetSubDatasets()

    dat0 = gdal.Open(sds[0][0], GA_ReadOnly)
    band_metas = []
    for s in sds:
        f2 = gdal.Open(s[0], GA_ReadOnly)
        band_metas.append(f2.GetMetadata())
        band_metas[-1]['sub_dataset_name'] = s[0]
    meta = {
             'meta': f.GetMetadata(),
             'band_meta': band_metas,
             'sub_datasets': sds,
             'name': datafile,
            }
    return meta_strings_to_dict(meta)


def load_hdf4_array(datafile, meta, band_specs=None):
    '''Return an MLDataset where each subdataset is a DataArray

    Parameters:
        :datafile: filename
        :meta:     meta from earthio.load_hdf4_meta
        :band_specs: list of earthio.BandSpec objects,
                    defaulting to reading all subdatasets
                    as bands

    Returns:
        :Elmstore: Elmstore of teh hdf4 data
    '''
    import gdal
    from gdalconst import GA_ReadOnly
    from earthio import MLDataset
    from earthio.metadata_selection import match_meta
    logger.debug('load_hdf4_array: {}'.format(datafile))
    f = gdal.Open(datafile, GA_ReadOnly)

    sds = meta['sub_datasets']
    band_metas = meta['band_meta']
    band_order_info = []
    if band_specs:
        for band_meta, s in zip(band_metas, sds):
            for idx, band_spec in enumerate(band_specs):
                if match_meta(band_meta, band_spec):
                    band_order_info.append((idx, band_meta, s, band_spec))
                    break

        band_order_info.sort(key=lambda x:x[0])
        if not len(band_order_info):
            raise ValueError('No matching bands with '
                             'band_specs {}'.format(band_specs))
    else:
        band_order_info = [(idx, band_meta, s, 'band_{}'.format(idx))
                           for idx, (band_meta, s) in enumerate(zip(band_metas, sds))]
    native_dims = ('y', 'x')
    elm_store_data = OrderedDict()

    band_order = []
    for _, band_meta, s, band_spec in band_order_info:
        attrs = copy.deepcopy(meta)
        attrs.update(copy.deepcopy(band_meta))
        if isinstance(band_spec, BandSpec):
            name = band_spec.name
            reader_kwargs = {k: getattr(band_spec, k)
                             for k in READ_ARRAY_KWARGS
                             if getattr(band_spec, k)}
            geo_transform = take_geo_transform_from_meta(band_spec, **attrs)
        else:
            reader_kwargs = {}
            name = band_spec
            geo_transform = None
        reader_kwargs = window_to_gdal_read_kwargs(**reader_kwargs)
        handle = gdal.Open(s[0], GA_ReadOnly)
        band_meta.update(reader_kwargs)
        np_arr = handle.ReadAsArray(**reader_kwargs)
        out = _np_arr_to_coords_dims(np_arr,
                 band_spec,
                 reader_kwargs,
                 geo_transform=geo_transform,
                 band_meta=band_meta,
                 handle=handle)
        np_arr, coords, dims, canvas, geo_transform = out
        attrs['geo_transform'] = geo_transform
        attrs['canvas'] = canvas
        elm_store_data[name] = xr.DataArray(raster,
                               coords=coords,
                               dims=dims,
                               attrs=attrs)

        band_order.append(name)
    del handle
    attrs = copy.deepcopy(attrs)
    attrs['band_order'] = band_order
    gc.collect()
    return MLDataset(elm_store_data, attrs=attrs)
