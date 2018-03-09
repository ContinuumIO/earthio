from __future__ import absolute_import, division, print_function, unicode_literals

import os
import sys

import pytest
import numpy as np

from earthio.netcdf import load_netcdf_meta, load_netcdf_array
from earthio.tests.util import (EARTHIO_HAS_EXAMPLES,
                                NETCDF_FILES,
                                assertions_on_metadata)
from earthio.util import LayerSpec

if NETCDF_FILES:
    NETCDF_DIR = os.path.dirname(NETCDF_FILES[0])

variables_dict = dict(HQobservationTime='HQobservationTime')
variables_list = ['HQobservationTime']


@pytest.mark.skipif(not EARTHIO_HAS_EXAMPLES,
                    reason='elm-data repo has not been cloned')
def test_read_meta():
    for nc_file in NETCDF_FILES:
        meta = load_netcdf_meta(nc_file)
        assertions_on_metadata(meta)


def _validate_array_test_result(ds):
    sample = ds.HQobservationTime
    mean_y = np.mean(sample.y)
    mean_x = np.mean(sample.x)

    assert ds.y.size == 1800
    assert ds.x.size == 3600

@pytest.mark.skipif(not EARTHIO_HAS_EXAMPLES,
                   reason='elm-data repo has not been cloned')
def test_read_using_dict_of_variables():
    for nc_file in NETCDF_FILES:
        meta = load_netcdf_meta(nc_file)
        ds = load_netcdf_array(nc_file, meta, variables_dict)
        _validate_array_test_result(ds)


@pytest.mark.skipif(not EARTHIO_HAS_EXAMPLES,
                   reason='elm-data repo has not been cloned')
def test_read_using_list_of_variables():
    for nc_file in NETCDF_FILES:
        meta = load_netcdf_meta(nc_file)
        ds = load_netcdf_array(nc_file, meta, variables_list)
        _validate_array_test_result(ds)
        variables_list2 = [LayerSpec('', 'HQobservationTime', v) for v in variables_list]
        ds = load_netcdf_array(nc_file, meta, variables_list2)
        _validate_array_test_result(ds)


