from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os

import attr
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
layer_specs = [
    LayerSpec('long_name', 'Band 1 ', 'layer_1', **kwargs),
    LayerSpec('long_name', 'Band 2 ', 'layer_2', **kwargs),
    LayerSpec('long_name', 'Band 3 ', 'layer_3', **kwargs),
    LayerSpec('long_name', 'Band 4 ', 'layer_4', **kwargs),
    LayerSpec('long_name', 'Band 5 ', 'layer_5', **kwargs),
    LayerSpec('long_name', 'Band 7 ', 'layer_7', **kwargs),
    LayerSpec('long_name', 'Band 8 ', 'layer_8', **kwargs),
    LayerSpec('long_name', 'Band 10 ', 'layer_10', **kwargs),
    LayerSpec('long_name', 'Band 11 ', 'layer_11', **kwargs),
]

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
        assert sorted((mean_x,
                sample.canvas.bounds.left,
                sample.canvas.bounds.right))[1] == mean_x
        assert sorted((mean_y,
                sample.canvas.bounds.top,
                sample.canvas.bounds.bottom))[1] == mean_y
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
        b = attr.asdict(b)
        b['buf_xsize'], b['buf_ysize'] = 200, 300
        layer_specs_kwargs.append(LayerSpec(**b))
    meta = load_hdf4_meta(HDF4_FILES[0])
    es = load_hdf4_array(HDF4_FILES[0], meta, layer_specs_kwargs)
    for b in es.layer_order:
        assert getattr(es, b).values.shape == (300, 200)

