from __future__ import absolute_import, division, print_function, unicode_literals

import os

import pytest

from earthio import *
from earthio.tests.util import (TIF_FILES, HDF5_FILES,
                                HDF4_FILES, NETCDF_FILES)
TRIALS = {}

if TIF_FILES:
    from earthio.tests.test_tif import band_specs as tif_band_specs
    TRIALS['tif'] = os.path.dirname(TIF_FILES[0])
if HDF4_FILES:
    TRIALS['hdf4'] = HDF4_FILES[0]
if HDF5_FILES:
    TRIALS['hdf5'] = HDF5_FILES[0]
if NETCDF_FILES:
    TRIALS['netcdf'] = NETCDF_FILES[0]

@pytest.mark.parametrize('ftype,filename', sorted(TRIALS.items()))
def test_load_array(ftype, filename):
    if ftype == 'tif':
        # avoid memory trouble
        band_specs = tif_band_specs[:3]
    else:
        band_specs = None
    assert isinstance(load_array(filename, band_specs=band_specs), ElmStore)

