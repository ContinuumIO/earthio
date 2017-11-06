from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os

import numpy as np
import pytest

from earthio.hdf4 import (load_hdf4_meta,
                              load_hdf4_array)

from earthio.util import LayerSpec

from earthio.tests.util import (EARTHIO_EXAMPLE_DATA_PATH,
                                HDF4_FILES,
                                assertions_on_metadata,
                                assertions_on_layer_metadata)
if HDF4_FILES:
    HDF4_DIR = os.path.dirname(HDF4_FILES[0])

kwargs = {}
ls = lambda n: LayerSpec(search_key='long_name',
                         search_value='Band {} '.format(n),
                         name='layer_{}'.format(n),
                         **kwargs)
layer_specs = [ls(n) for n in range(1, 6)]

@pytest.mark.parametrize('hdf', HDF4_FILES or [])
@pytest.mark.skipif(not HDF4_FILES,
               reason='elm-data repo has not been cloned')
def test_read_meta(hdf):
    meta = load_hdf4_meta(hdf)
    assertions_on_metadata(meta)
    assert 'GranuleBeginningDateTime' in meta['meta']
    for layer_meta in meta['layer_meta']:
        assert 'GranuleBeginningDateTime' in layer_meta


@pytest.mark.skipif(not HDF4_FILES,
                   reason='elm-data repo has not been cloned')
@pytest.mark.parametrize('hdf', HDF4_FILES or [])
def test_read_array(hdf):

    meta = load_hdf4_meta(hdf)
    es = load_hdf4_array(hdf, meta, layer_specs)
    for layer in es.data_vars:
        sample = getattr(es, layer)
        mean_y = np.mean(sample.y)
        mean_x = np.mean(sample.x)
        layer_names = np.array([b.name for b in layer_specs])
        assert sample.y.size == 1200
        assert sample.x.size == 1200
        assert len(es.data_vars) == len(layer_specs)
        assert np.all(es.layer_order == [x.name for x in layer_specs])
        assertions_on_layer_metadata(sample.attrs)
    es2 = load_hdf4_array(hdf, meta, layer_specs=None)
    assert len(es2.data_vars) > len(es.data_vars)

@pytest.mark.skipif(not HDF4_FILES,
               reason='elm-data repo has not been cloned')
def test_reader_kwargs():
    layer_specs_kwargs = []
    for b in layer_specs:
        b = b.get_params()
        b['buf_xsize'], b['buf_ysize'] = 200, 300
        layer_specs_kwargs.append(LayerSpec(**b))
    meta = load_hdf4_meta(HDF4_FILES[0])
    es = load_hdf4_array(HDF4_FILES[0], meta, layer_specs_kwargs)
    for b in es.layer_order:
        assert getattr(es, b).values.shape == (300, 200)

