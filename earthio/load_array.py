'''
------------------

``earthio.load_array``
++++++++++++++++++++++++++
load_array returns an MLDataset for HDF, NetCDF, GeoTiff files
'''

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import logging
import os
import re

from earthio.netcdf import load_netcdf_array, load_netcdf_meta
from earthio.hdf4 import load_hdf4_array, load_hdf4_meta
from earthio.hdf5 import load_hdf5_array, load_hdf5_meta
from earthio.tif import load_dir_of_tifs_meta,load_dir_of_tifs_array

__all__ = ['load_array', 'load_meta']

EXT = OrderedDict([
    ('netcdf', ('nc', 'nc\d',)),
    ('hdf5', ('h5', 'hdf5', 'hd5',)),
    ('hdf4', ('hdf4', 'h4', 'hd4',)),
    ('hdf', ('hdf',))
])

logger = logging.getLogger(__name__)

def _find_file_type(filename):
    '''Guess file type on extension or "tif" if
    filename is directory, default: netcdf'''
    if os.path.isdir(filename):
        ftype = 'tif'
    else:
        this_ext = filename.split('.')[-1]
        for ftype, exts in EXT.items():
            if any(re.search(ext, this_ext, re.IGNORECASE) for ext in exts):
                break
            else:

                ftype = 'netcdf'
    return ftype


def load_array(filename, meta=None, layer_specs=None, reader=None):
    '''Create MLDataset from HDF4 / 5 or NetCDF files or TIF directories

    Parameters:
        :filename:   filename (HDF4 / 5 or NetCDF) or directory name (TIF)
        :meta:       meta data from "filename" already loaded
        :layer_specs: list of strings or earthio.LayerSpec objects
        :reader:     named reader from earthio - one of:  ('tif', 'hdf4', 'hdf5', 'netcdf')

    Returns:
        :es:         MLDataset (xarray.Dataset) with layers specified by layer_specs as DataArrays in "data_vars" attribute
    '''
    ftype = reader or _find_file_type(filename)
    if meta is None:
        if ftype == 'tif':
            meta = _load_meta(filename, ftype, layer_specs=layer_specs)
        else:
            meta = _load_meta(filename, ftype)
    if ftype == 'netcdf':
        return load_netcdf_array(filename, meta, layer_specs=layer_specs)
    elif ftype == 'hdf5':
        return load_hdf5_array(filename, meta, layer_specs=layer_specs)
    elif ftype == 'hdf4':
        return load_hdf4_array(filename, meta, layer_specs=layer_specs)
    elif ftype == 'tif':
        return load_dir_of_tifs_array(filename, meta, layer_specs=layer_specs)
    elif ftype == 'hdf':
        try:
            es = load_hdf4_array(filename, meta, layer_specs=layer_specs)
        except Exception as e:
            logger.info('NOTE: guessed HDF4 type. Failed: {}. \nTrying HDF5'.format(repr(e)))
            es = load_hdf5_array(filename, meta, layer_specs=layer_specs)
        return es


def _load_meta(filename, ftype, **kwargs):

    if ftype == 'netcdf':
        return load_netcdf_meta(filename)
    elif ftype == 'hdf5':
        return load_hdf5_meta(filename)
    elif ftype == 'hdf4':
        return load_hdf4_meta(filename)
    elif ftype == 'tif':
        return load_dir_of_tifs_meta(filename, **kwargs)
    elif ftype == 'hdf':
        try:
            return load_hdf4_meta(filename, **kwargs)
        except Exception as e:
            logger.info('NOTE: guessed HDF4 type. Failed: {}. \nTrying HDF5'.format(repr(e)))
            return load_hdf5_meta(filename, **kwargs)


def load_meta(filename, **kwargs):
    '''Load metadata for a HDF4 / HDF5 or NetCDF file or TIF directory

    Parameters:
        :filename:       filename (HDF4 / 5 and NetCDF) or directory (TIF)
        :kwargs:         keyword args that may include "layer_specs", \
                        a list of string layer names or earthio.LayerSpec objects

    Returns:
        :meta:           dict with the following keys
    '''

    reader = kwargs.get('reader')
    if isinstance(reader, dict):
        kw = {k: v for k, v in reader.items() if k != 'reader'}
        ftype = _find_file_type(filename)
    else:
        kw = kwargs
        ftype = reader
    return _load_meta(filename, ftype, **kw)
