from __future__ import absolute_import, division, print_function, unicode_literals

import glob
import os

from xarray_filters.tests.test_data import ts_clustering_example

EARTHIO_EXAMPLE_DATA_PATH = os.environ.get('EARTHIO_EXAMPLE_DATA_PATH')
if not EARTHIO_EXAMPLE_DATA_PATH:
    EARTHIO_EXAMPLE_DATA_PATH = os.environ.get('ELM_EXAMPLE_DATA_PATH')
if EARTHIO_EXAMPLE_DATA_PATH:
    if not os.path.exists(EARTHIO_EXAMPLE_DATA_PATH):
        raise ValueError('EARTHIO_EXAMPLE_DATA_PATH {} does not exist'.format(EARTHIO_EXAMPLE_DATA_PATH))
    EARTHIO_HAS_EXAMPLES = True
    EARTHIO_EXAMPLE_DATA_PATH = os.path.expanduser(EARTHIO_EXAMPLE_DATA_PATH)
    args = ('landsat-pds',
            'L8',
            '015',
            '033',
            '*',
            '*.TIF',)
    TIF_FILES = glob.glob(os.path.join(EARTHIO_EXAMPLE_DATA_PATH, *args))
    if not TIF_FILES:
        # handling system for saving example GeoTiffs
        # ("landsat-pds" was not part of local file name)
        TIF_FILES = glob.glob(os.path.join(EARTHIO_EXAMPLE_DATA_PATH, *(('tif',)  + args[1:])))
    HDF5_FILES = glob.glob(os.path.join(EARTHIO_EXAMPLE_DATA_PATH,
                                        'hdf5',
                                        '2016',
                                        '01',
                                        '01',
                                        'imerg',
                                        '*.HDF5'))
    HDF4_FILES = glob.glob(os.path.join(EARTHIO_EXAMPLE_DATA_PATH,
                                        'hdf4',
                                        '*.hdf'))
    NETCDF_FILES = glob.glob(os.path.join(EARTHIO_EXAMPLE_DATA_PATH,
                                          'netcdf',
                                          '*.nc'))
else:
    EARTHIO_HAS_EXAMPLES = False
    EARTHIO_EXAMPLE_DATA_PATH = None
    TIF_FILES = []
    HDF5_FILES = []
    HDF4_FILES = []
    NETCDF_FILES = []

def assertions_on_metadata(meta):
    required_keys = ('meta', 'layer_meta')
    for key in required_keys:
        assert key in meta

def assertions_on_layer_metadata(layer_meta):
    required_keys = ('sub_dataset_name', )
    for key in required_keys:
        assert key in layer_meta

def random_raster(width=100, height=200):
    layers = ['layer_1', 'layer_2']

    return ts_clustering_example(n_features=len(layers),
                                 shape=(height, width),
                                 layers=layers)

