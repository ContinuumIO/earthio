'''
----------------------

``earthio.netcdf``
~~~~~~~~~~~~~~~~~~~~~~

Tools for reading NetCDF files.  Typically use the interface through

    - :func:`earthio.load_layers`
    - :func:`earthio.load_meta`

'''

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import logging

from affine import Affine
import netCDF4 as nc
import xarray as xr

from earthio.util import (geotransform_to_bounds,
                          VALID_X_NAMES, VALID_Y_NAMES,
                          take_geo_transform_from_meta,
                          meta_strings_to_dict)
from earthio.metadata_selection import match_meta
from six import string_types

__all__ = ['load_netcdf_meta', 'load_netcdf_array']

logger = logging.getLogger(__name__)


def _nc_str_to_dict(nc_str):
    if isinstance(nc_str, string_types):
        str_list = [g.split('=') for g in nc_str.split(';\n')]
        d = dict([g for g in str_list if len(g) == 2])
        if d:
            return d
        return nc_str
    return nc_str


def _get_nc_attrs(nc_dataset):

    return {k: _nc_str_to_dict(nc_dataset.getncattr(k))
            for k in nc_dataset.ncattrs()}


def _get_subdatasets(nc_dataset):
    sds = []
    for k in nc_dataset.variables.keys():
        var_obj = nc_dataset.variables[k]
        obj = {d: var_obj.getncattr(d) for d in var_obj.ncattrs()}
        sds.append(obj)
    return sds


def _normalize_coords(ds):
    '''
    Makes sure that output dataset has `x` and `y` coordinates.

    Parameters:
        :ds:

    Returns:
        :coords: Dictionary with 'x_coord' coordinates and 'y_coord' coordinates
    '''

    coord_names = [k for k in ds.coords.keys()]

    x_coord = next((c for c in coord_names if c.lower() in VALID_X_NAMES), None)
    y_coord = next((c for c in coord_names if c.lower() in VALID_Y_NAMES), None)

    if x_coord is None:
        raise ValueError('x coordinate not found within input dataset')
    if y_coord is None:
        raise ValueError('y coordinate not found within input dataset')

    coords = dict(x=ds[x_coord], y=ds[y_coord])
    return coords


def load_netcdf_meta(datafile):
    '''
    Loads metadata for NetCDF

    Parameters:
        :datafile: str: Path on disk to NetCDF file

    Returns:
        :meta: Dictionary of metadata
    '''
    ras = nc.Dataset(datafile)
    attrs = _get_nc_attrs(ras)
    sds = _get_subdatasets(ras)
    meta = {'meta': attrs,
            'layer_meta': sds,
            'name': datafile,
            'variables': list(ras.variables.keys()),
            }
    return meta_strings_to_dict(meta)


def load_netcdf_array(datafile, meta, layer_specs=None):
    '''
    Loads metadata for NetCDF

    Parameters:
        :datafile: str: Path on disk to NetCDF file
        :meta: dict: netcdf metadata object
        :variables: dict<str:str>, list<str>: list of variables to load

    Returns:
        :new_es: xr.Dataset
    '''
    logger.debug('load_netcdf_array: {}'.format(datafile))
    ds = xr.open_dataset(datafile)
    if layer_specs:
        data = []
        if isinstance(layer_specs, dict):
            data = { k: ds[getattr(v, 'name', v)] for k, v in layer_specs.items() }
            layer_spec = tuple(layer_specs.values())[0]
        if isinstance(layer_specs, (list, tuple)):
            data = {getattr(v, 'name', v): ds[getattr(v, 'name', v)]
                    for v in layer_specs }
            layer_spec = layer_specs[0]
        data = OrderedDict(data)
    else:
        data = OrderedDict([(v, ds[v]) for v in meta['variables']])
        layer_spec = None
    geo_transform = take_geo_transform_from_meta(layer_spec=layer_spec,
                                                 required=True,
                                                 **meta)
    for b, sub_dataset_name in zip(meta['layer_meta'], data):
        b['geo_transform'] = meta['geo_transform'] = geo_transform
        b['sub_dataset_name'] = sub_dataset_name
    new_es = xr.Dataset(data,
                    coords=_normalize_coords(ds),
                    attrs=meta)
    return new_es
