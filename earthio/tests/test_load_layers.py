from __future__ import absolute_import, division, print_function, unicode_literals

import os

import pytest
import xarray as xr
from earthio import *
from earthio.tests.util import (TIF_FILES, HDF5_FILES,
                                HDF4_FILES, NETCDF_FILES)
TRIALS = {}

if TIF_FILES:
    from earthio.tests.test_tif import layer_specs as tif_layer_specs
    TRIALS['tif'] = os.path.dirname(TIF_FILES[0])
if HDF4_FILES:
    TRIALS['hdf4'] = HDF4_FILES[0]
if HDF5_FILES:
    TRIALS['hdf5'] = HDF5_FILES[0]
if NETCDF_FILES:
    TRIALS['netcdf'] = NETCDF_FILES[0]

@pytest.mark.parametrize('ftype,filename', sorted(TRIALS.items()))
def test_load_layers(ftype, filename):
    if ftype == 'tif':
        # avoid memory trouble
        layer_specs = tif_layer_specs[:3]
    else:
        layer_specs = None
    assert isinstance(load_layers(filename, layer_specs=layer_specs), xr.Dataset)

