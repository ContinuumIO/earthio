from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os

import numpy as np
import pytest

from earthio.hdf5 import (load_hdf5_meta,
                          load_subdataset,
                          load_hdf5_array)

from earthio.tests.util import (EARTHIO_EXAMPLE_DATA_PATH,
                                HDF5_FILES,
                                assertions_on_metadata,
                                assertions_on_layer_metadata)

from earthio.util import LayerSpec

if HDF5_FILES:
    HDF5_DIR = os.path.dirname(HDF5_FILES[0])

def get_layer_specs(filename):
    if os.path.basename(filename).startswith('3B-MO'):
        sub_dataset_names = ('/precipitation',)
    else:
        sub_dataset_names = ('HQobservationTime',
                             'HQprecipSource',
                             'HQprecipitation',
                             'IRkalmanFilterWeight',
                             'IRprecipitation',
                             'precipitationCal',
                             'precipitationUncal',
                             'probabilityLiquidPrecipitation',)
    layer_specs = []
    for sub in sub_dataset_names:
        layer_specs.append(LayerSpec(search_key='sub_dataset_name',
                               search_value=sub + '$', # line ender regex
                               name=sub,
                               meta_to_geotransform="earthio.util:grid_header_to_geo_transform",
                               stored_coords_order=("x", "y")))
    return sub_dataset_names, layer_specs


@pytest.mark.parametrize('hdf', HDF5_FILES or [])
@pytest.mark.skipif(not HDF5_FILES,
               reason='elm-data repo has not been cloned')
def test_read_meta(hdf):
    meta = load_hdf5_meta(hdf)
    assertions_on_metadata(meta)


@pytest.mark.skipif(not HDF5_FILES,
                   reason='elm-data repo has not been cloned')
def test_load_subdataset():
    import gdal
    f = HDF5_FILES[0]
    _ , layer_specs = get_layer_specs(f)
    data_file = gdal.Open(f)
    meta = load_hdf5_meta(f)
    data_array = load_subdataset(data_file.GetSubDatasets()[0][0],
                                 meta['layer_meta'][0],
                                 layer_specs[0])
    assert data_array.data is not None


@pytest.mark.skipif(not HDF5_FILES, reason='elm-data repo has not been cloned')
@pytest.mark.parametrize('filename', HDF5_FILES)
def test_read_array(filename):
    sub_dataset_names, layer_specs = get_layer_specs(filename)
    meta = load_hdf5_meta(filename)
    dset = load_hdf5_array(filename, meta, layer_specs)
    assert len(dset.data_vars) == len(sub_dataset_names)
    for layer in dset.data_vars:
        sample = getattr(dset, layer)
        assert sample.y.size == 1800
        assert sample.x.size == 3600
        assert len(dset.data_vars) == len(layer_specs)
        assertions_on_layer_metadata(sample.attrs)


@pytest.mark.skipif(not HDF5_FILES,
               reason='elm-data repo has not been cloned')
def test_reader_kwargs():
    sub_dataset_names, layer_specs = get_layer_specs(HDF5_FILES[0])
    layer_specs_kwargs = []
    for b in layer_specs:
        b = b.get_params()
        b['buf_xsize'], b['buf_ysize'] = 200, 300
        layer_specs_kwargs.append(LayerSpec(**b))
    meta = load_hdf5_meta(HDF5_FILES[0])
    dset = load_hdf5_array(HDF5_FILES[0], meta, layer_specs_kwargs)
    for b in dset.layer_order:
        assert getattr(dset, b).values.shape == (300, 200)

