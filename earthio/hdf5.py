'''
--------------------

``earthio.hdf5``
~~~~~~~~~~~~~~~~~~~~~

Tools for reading HDF5 files.  Typically use the interface through

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
                          LayerSpec,
                          row_col_to_xy,
                          _np_arr_to_coords_dims,
                          READ_ARRAY_KWARGS,
                          take_geo_transform_from_meta,
                          window_to_gdal_read_kwargs,
                          meta_strings_to_dict)

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
    layer_metas = []
    for s in sds:
        f2 = gdal.Open(s[0], GA_ReadOnly)
        bm = dict()
        for k, v in f2.GetMetadata().items():
            vals = _nc_str_to_dict(v)
            bm.update(vals)
        layer_metas.append(bm)
        layer_metas[-1]['sub_dataset_name'] = s[0]

    meta = dict()
    for k, v in f.GetMetadata().items():
        vals = _nc_str_to_dict(v)
        meta.update(vals)

    return meta_strings_to_dict(dict(meta=meta,
                                layer_meta=layer_metas,
                                sub_datasets=sds,
                                name=datafile))

def load_subdataset(subdataset, attrs, layer_spec, **reader_kwargs):
    '''Load a single subdataset'''
    import gdal
    data_file = gdal.Open(subdataset)
    np_arr = data_file.ReadAsArray(**reader_kwargs)
    out = _np_arr_to_coords_dims(np_arr,
                 layer_spec,
                 reader_kwargs,
                 geo_transform=None,
                 layer_meta=attrs,
                 handle=data_file)
    np_arr, coords, dims, attrs2 = out
    attrs.update(attrs2)
    return xr.DataArray(data=np_arr,
                        coords=coords,
                        dims=dims,
                        attrs=attrs)


def load_hdf5_array(datafile, meta, layer_specs):
    '''Return an xr.Dataset where each subdataset is a xr.DataArray

    Parameters:
        :datafile: filename
        :meta:     meta from earthio.load_hdf5_meta
        :layer_specs: list of earthio.LayerSpec objects,
                    defaulting to reading all subdatasets
                    as layers

    Returns:
        :dset: An xr.Dataset
    '''
    import gdal
    from gdalconst import GA_ReadOnly

    logger.debug('load_hdf5_array: {}'.format(datafile))
    f = gdal.Open(datafile, GA_ReadOnly)
    sds = meta['sub_datasets']
    layer_metas = meta['layer_meta']
    layer_order_info = []
    for layer_idx, (layer_meta, sd) in enumerate(zip(layer_metas, sds)):
        if layer_specs:
            for idx, bs in enumerate(layer_specs):
                if match_meta(layer_meta, bs):
                    layer_order_info.append((idx, layer_meta, sd, bs))
                    break
        else:
            layer_order_info.append((layer_idx, layer_meta, sd, 'layer_{}'.format(layer_idx)))

    if layer_specs and len(layer_order_info) != len(layer_specs):
        raise ValueError('Number of layers matching layer_specs {} was not equal '
                         'to the number of layer_specs {}'.format(len(layer_order_info), len(layer_specs)))

    layer_order_info.sort(key=lambda x:x[0])
    elm_store_data = OrderedDict()
    layer_order = []
    for _, layer_meta, sd, layer_spec in layer_order_info:
        if isinstance(layer_spec, LayerSpec):
            name = layer_spec.name
            reader_kwargs = {k: getattr(layer_spec, k)
                             for k in READ_ARRAY_KWARGS
                             if getattr(layer_spec, k)}
        else:
            reader_kwargs = {}
            name = layer_spec
        reader_kwargs = window_to_gdal_read_kwargs(**reader_kwargs)
        attrs = copy.deepcopy(meta)
        attrs.update(copy.deepcopy(layer_meta))
        elm_store_data[name] = load_subdataset(sd[0], attrs, layer_spec, **reader_kwargs)

        layer_order.append(name)
    attrs = copy.deepcopy(attrs)
    attrs['layer_order'] = layer_order
    gc.collect()
    return xr.Dataset(elm_store_data, attrs=attrs)
