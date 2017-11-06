from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os
import sys

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

ls = lambda n: LayerSpec(search_key='name',
                         search_value='_B{}.TIF'.format(n),
                         name='layer_{}'.format(n))
layer_specs = [ls(n) for n in (list(range(1, 8)) + list(range(9, 12)))]

@pytest.mark.skipif(not TIF_FILES,
               reason='elm-data repo has not been cloned')
def test_read_meta():
    for tif in TIF_FILES:
        raster, meta = load_tif_meta(tif)
        assert hasattr(raster, 'read')
        assert hasattr(raster, 'width')
        layer_specs_with_layer_8 = layer_specs + [ls(8)]
        meta = load_dir_of_tifs_meta(TIF_DIR,
                                     layer_specs=layer_specs_with_layer_8)
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
    dset = load_dir_of_tifs_array(TIF_DIR, meta, layer_specs)
    for var in dset.data_vars:
        sample = getattr(dset, var)
        mean_y = np.mean(sample.y)
        mean_x = np.mean(sample.x)
        layer_names = np.array([b.name for b in layer_specs])
        assertions_on_layer_metadata(sample.attrs)


@pytest.mark.skipif(not TIF_FILES,
               reason='elm-data repo has not been cloned')
def test_reader_kwargs():
    layer_specs_kwargs = []
    for b in layer_specs:
        b = b.get_params()
        b['buf_xsize'], b['buf_ysize'] = 200, 300
        layer_specs_kwargs.append(LayerSpec(**b))
    meta = load_dir_of_tifs_meta(TIF_DIR, layer_specs_kwargs)
    dset = load_dir_of_tifs_array(TIF_DIR, meta, layer_specs_kwargs)
    for b in dset.layer_order:
        assert getattr(dset, b).values.shape == (300, 200)

