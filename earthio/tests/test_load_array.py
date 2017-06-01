import os

import pytest

from earthio import *
from earthio.tests.util import (TIF_FILES, HDF5_FILES,
                                    HDF4_FILES, NETCDF_FILES,
                                    ELM_HAS_EXAMPLES)
from earthio.tests.test_tif import band_specs as tif_band_specs
TRIALS = {'tif': os.path.dirname(TIF_FILES[0]) if TIF_FILES else 'tif',
          'hdf5': HDF5_FILES[0] if HDF5_FILES else 'hdf5',
          'hdf4': HDF4_FILES[0] if HDF4_FILES else 'hdf4',
          'netcdf': NETCDF_FILES[0] if NETCDF_FILES else 'netcdf'}

@pytest.mark.skipif(not ELM_HAS_EXAMPLES,
               reason='elm-data repo has not been cloned')
@pytest.mark.parametrize('ftype,filename', sorted(TRIALS.items()))
def test_load_array(ftype, filename):
    if ftype == 'tif':
        # avoid memory trouble
        band_specs = tif_band_specs[:3]
    else:
        band_specs = None
    assert isinstance(load_array(filename, band_specs=band_specs), ElmStore)

