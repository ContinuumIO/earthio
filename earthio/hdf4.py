'''
--------------------

``earthio.hdf4``
~~~~~~~~~~~~~~~~~~~~~

Tools for reading HDF4 files.  Typically use the interface through

    - :func:`earthio.load_layers`
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
                          LayerSpec,
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
    '''Load meta and layer_meta for a datafile'''
    import gdal
    from gdalconst import GA_ReadOnly
    f = gdal.Open(datafile, GA_ReadOnly)
    sds = f.GetSubDatasets()

    dat0 = gdal.Open(sds[0][0], GA_ReadOnly)
    layer_metas = []
    for s in sds:
        f2 = gdal.Open(s[0], GA_ReadOnly)
        layer_metas.append(f2.GetMetadata())
        layer_metas[-1]['sub_dataset_name'] = s[0]
    meta = {
             'meta': f.GetMetadata(),
             'layer_meta': layer_metas,
             'sub_datasets': sds,
             'name': datafile,
            }
    return meta_strings_to_dict(meta)


def load_hdf4_array(datafile, meta, layer_specs=None):
    '''Return an xr.Dataset where each subdataset is a xr.DataArray

    Parameters:
        :datafile: filename
        :meta:     meta from earthio.load_hdf4_meta
        :layer_specs: list of earthio.LayerSpec objects,
                    defaulting to reading all subdatasets
                    as layers

    Returns:
        :Elmstore: Elmstore of teh hdf4 data
    '''
    import gdal
    from gdalconst import GA_ReadOnly
    from earthio.metadata_selection import match_meta
    logger.debug('load_hdf4_array: {}'.format(datafile))
    f = gdal.Open(datafile, GA_ReadOnly)

    sds = meta['sub_datasets']
    layer_metas = meta['layer_meta']
    layer_order_info = []
    if layer_specs:
        for layer_meta, s in zip(layer_metas, sds):
            #layer_meta['name'] = s[0]
            for idx, layer_spec in enumerate(layer_specs):
                if match_meta(layer_meta, layer_spec):
                    layer_order_info.append((idx, layer_meta, s, layer_spec))
                    break

        layer_order_info.sort(key=lambda x:x[0])
        if len(layer_order_info) != len(layer_specs):
            raise ValueError('No matching layers with '
                             'layer_specs {} (meta = {})'.format(layer_specs, layer_meta))
    else:
        layer_order_info = [(idx, layer_meta, s, 'layer_{}'.format(idx))
                           for idx, (layer_meta, s) in enumerate(zip(layer_metas, sds))]
    native_dims = ('y', 'x')
    elm_store_data = OrderedDict()

    layer_order = []
    for _, layer_meta, s, layer_spec in layer_order_info:
        attrs = copy.deepcopy(meta)
        attrs.update(copy.deepcopy(layer_meta))
        if isinstance(layer_spec, LayerSpec):
            name = layer_spec.name
            reader_kwargs = {k: getattr(layer_spec, k)
                             for k in READ_ARRAY_KWARGS
                             if getattr(layer_spec, k)}
            geo_transform = take_geo_transform_from_meta(layer_spec, **attrs)
        else:
            reader_kwargs = {}
            name = layer_spec
            geo_transform = None
        reader_kwargs = window_to_gdal_read_kwargs(**reader_kwargs)
        handle = gdal.Open(s[0], GA_ReadOnly)
        layer_meta.update(reader_kwargs)
        np_arr = handle.ReadAsArray(**reader_kwargs)
        out = _np_arr_to_coords_dims(np_arr,
                 layer_spec,
                 reader_kwargs,
                 geo_transform=geo_transform,
                 layer_meta=layer_meta,
                 handle=handle)
        np_arr, coords, dims, attrs2 = out
        attrs.update(attrs2)
        elm_store_data[name] = xr.DataArray(np_arr,
                               coords=coords,
                               dims=dims,
                               attrs=attrs)

        layer_order.append(name)
    del handle
    attrs = copy.deepcopy(attrs)
    attrs['layer_order'] = layer_order
    gc.collect()
    return xr.Dataset(elm_store_data, attrs=attrs)
