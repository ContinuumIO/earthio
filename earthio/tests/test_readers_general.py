from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict

import numpy as np
import pytest
import xarray as xr

from earthio import *
from earthio.tests.util import (EARTHIO_HAS_EXAMPLES,
                                HDF4_FILES, HDF5_FILES, TIF_FILES,
                                random_raster)

if HDF4_FILES:
    from earthio.tests.test_hdf4 import layer_specs as hdf4_layer_specs
else:
    hdf4_layer_specs = None
if HDF5_FILES:
    from earthio.tests.test_hdf5 import get_layer_specs
else:
    get_layer_specs = None
if TIF_FILES:
    from earthio.tests.test_tif import TIF_DIR, layer_specs as tif_layer_specs
else:
    TIF_DIR = tif_layer_specs = None


@pytest.mark.skipIf(not EARTHIO_HAS_EXAMPLES, reason='test data has not been downloaded')
@pytest.mark.parametrize('ftype', ('hdf4', 'hdf5', 'tif',))
def test_reader_kwargs_window(ftype):

    '''Assert that "window" can be passed in a LayerSpec
    to control the (ymin, ymax), (xmin, xmax) window to read'''
    if not HDF5_FILES or not HDF4_FILES or not TIF_DIR:
        pytest.skip('test data has not been downloaded')

    if ftype == 'hdf5':
        _, layer_specs = get_layer_specs(HDF5_FILES[0])
        meta = load_hdf5_meta(HDF5_FILES[0])
        full_es = load_hdf5_array(HDF5_FILES[0], meta, layer_specs)
    elif ftype == 'hdf4':
        layer_specs = hdf4_layer_specs
        meta = load_hdf4_meta(HDF4_FILES[0])
        full_es = load_hdf4_array(HDF4_FILES[0], meta, layer_specs)
    elif ftype == 'tif':
        layer_specs = tif_layer_specs[:2]
        meta = load_dir_of_tifs_meta(TIF_DIR, layer_specs=layer_specs)
        full_es = load_dir_of_tifs_array(TIF_DIR, meta, layer_specs)
    layer_specs_window = []
    windows = {}
    for b in layer_specs:
        name = b.name
        val = getattr(full_es, name).values
        shp = val.shape
        b = b.get_params()
        b['window'] = windows[name] = (((10, 200), (210, 400)))
        layer_specs_window.append(LayerSpec(**b))

    if ftype == 'hdf4':
        es = load_hdf4_array(HDF4_FILES[0], meta, layer_specs_window)
    elif ftype == 'hdf5':
        es = load_hdf5_array(HDF5_FILES[0], meta, layer_specs_window)
    elif ftype == 'tif':
        meta_small = load_dir_of_tifs_meta(TIF_DIR, layer_specs=layer_specs_window)
        es = load_dir_of_tifs_array(TIF_DIR, meta_small, layer_specs_window)

    for layer in es.data_vars:
        window = windows[layer]
        subset = getattr(es, layer, None)
        assert subset is not None
        subset = subset.values
        expected_shape = tuple(map(np.diff, window))
        assert subset.shape == expected_shape

