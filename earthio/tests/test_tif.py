from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os
import sys

import attr
import numpy as np
import pytest

from earthio.tif import (load_dir_of_tifs_meta,
                             load_dir_of_tifs_array,
                             load_tif_meta,
                             ls_tif_files)
from earthio.tests.util import (EARTHIO_HAS_EXAMPLES,
                                    EARTHIO_EXAMPLE_DATA_PATH,
                                    TIF_FILES,
                                    assertions_on_metadata,
                                    assertions_on_layer_metadata)
from earthio.util import LayerSpec


if TIF_FILES:
    TIF_DIR = os.path.dirname(TIF_FILES[0])
layer_specs = [
    LayerSpec('name', '_B1.TIF', 'layer_1'),
    LayerSpec('name', '_B2.TIF', 'layer_2'),
    LayerSpec('name', '_B3.TIF', 'layer_3'),
    LayerSpec('name', '_B4.TIF', 'layer_4'),
    LayerSpec('name', '_B5.TIF', 'layer_5'),
    LayerSpec('name', '_B6.TIF', 'layer_6'),
    LayerSpec('name', '_B7.TIF', 'layer_7'),
    LayerSpec('name', '_B9.TIF', 'layer_9'),
    LayerSpec('name', '_B10.TIF', 'layer_10'),
    LayerSpec('name', '_B11.TIF', 'layer_11'),
]

@pytest.mark.skipif(not TIF_FILES,
               reason='elm-data repo has not been cloned')
def test_read_meta():
    for tif in TIF_FILES:
        raster, meta = load_tif_meta(tif)
        assert hasattr(raster, 'read')
        assert hasattr(raster, 'width')
        layer_specs_with_layer_8 = layer_specs + [LayerSpec('name', '_B8.TIF', 'layer_8')]
        meta = load_dir_of_tifs_meta(TIF_DIR, layer_specs_with_layer_8)
        layer_meta = meta['layer_meta']
        heights_names = [(m['height'], m['name']) for m in layer_meta]
        # layer 8 is panchromatic with 15 m resolution
        # other layers have 30 m resolution.  They
        # have the same bounds, so layer 8 has 4 times as many pixels
        heights_names.sort(key=lambda x:x[0])
        assert heights_names[-1][-1].endswith('_B8.TIF')


@pytest.mark.skipif(not TIF_FILES,
               reason='elm-data repo has not been cloned')
def test_read_array():
    meta = load_dir_of_tifs_meta(TIF_DIR, layer_specs)
    es = load_dir_of_tifs_array(TIF_DIR, meta, layer_specs)
    for var in es.data_vars:
        sample = getattr(es, var)
        mean_y = np.mean(sample.y)
        mean_x = np.mean(sample.x)
        layer_names = np.array([b.name for b in layer_specs])
        assert sorted((mean_x,
                sample.canvas.bounds.left,
                sample.canvas.bounds.right))[1] == mean_x
        assert sorted((mean_y,
                sample.canvas.bounds.top,
                sample.canvas.bounds.bottom))[1] == mean_y
        assert np.all(layer_names == es.layer_order)
        assertions_on_layer_metadata(sample.attrs)


@pytest.mark.skipif(not TIF_FILES,
               reason='elm-data repo has not been cloned')
def test_reader_kwargs():
    layer_specs_kwargs = []
    for b in layer_specs:
        b = attr.asdict(b)
        b['buf_xsize'], b['buf_ysize'] = 200, 300
        layer_specs_kwargs.append(LayerSpec(**b))
    meta = load_dir_of_tifs_meta(TIF_DIR, layer_specs_kwargs)
    es = load_dir_of_tifs_array(TIF_DIR, meta, layer_specs_kwargs)
    for b in es.layer_order:
        assert getattr(es, b).values.shape == (300, 200)

