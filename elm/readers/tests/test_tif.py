import glob
import os
import sys

import attr
import numpy as np
import pytest

from elm.readers.tif import (load_dir_of_tifs_meta,
                             load_dir_of_tifs_array,
                             load_tif_meta,
                             ls_tif_files)
from elm.readers.tests.util import (ELM_HAS_EXAMPLES,
                                    ELM_EXAMPLE_DATA_PATH,
                                    TIF_FILES,
                                    assertions_on_metadata,
                                    assertions_on_band_metadata)

from elm.readers.util import BandSpec

TIF_DIR = os.path.dirname(TIF_FILES[0])
band_specs = [
    BandSpec('name', '_B1.TIF', 'band_1'),
    BandSpec('name', '_B2.TIF', 'band_2'),
    BandSpec('name', '_B3.TIF', 'band_3'),
    BandSpec('name', '_B4.TIF', 'band_4'),
    BandSpec('name', '_B5.TIF', 'band_5'),
    BandSpec('name', '_B6.TIF', 'band_6'),
    BandSpec('name', '_B7.TIF', 'band_7'),
    BandSpec('name', '_B9.TIF', 'band_9'),
    BandSpec('name', '_B10.TIF', 'band_10'),
    BandSpec('name', '_B11.TIF', 'band_11'),
]
@pytest.mark.skipif(not ELM_HAS_EXAMPLES,
               reason='elm-data repo has not been cloned')
def test_read_meta():
    for tif in TIF_FILES:
        raster, meta = load_tif_meta(tif)
        assert hasattr(raster, 'read')
        assert hasattr(raster, 'width')
        band_specs_with_band_8 = band_specs + [BandSpec('name', '_B8.TIF', 'band_8')]
        meta = load_dir_of_tifs_meta(TIF_DIR, band_specs_with_band_8)
        band_meta = meta['band_meta']
        heights_names = [(m['height'], m['name']) for m in band_meta]
        # band 8 is panchromatic with 15 m resolution
        # other bands have 30 m resolution.  They
        # have the same bounds, so band 8 has 4 times as many pixels
        heights_names.sort(key=lambda x:x[0])
        assert heights_names[-1][-1].endswith('_B8.TIF')


@pytest.mark.skipif(not ELM_HAS_EXAMPLES,
               reason='elm-data repo has not been cloned')
def test_read_array():
    meta = load_dir_of_tifs_meta(TIF_DIR, band_specs)
    es = load_dir_of_tifs_array(TIF_DIR, meta, band_specs)
    for var in es.data_vars:
        sample = getattr(es, var)
        mean_y = np.mean(sample.y)
        mean_x = np.mean(sample.x)
        band_names = np.array([b.name for b in band_specs])
        assert sorted((mean_x,
                sample.canvas.bounds.left,
                sample.canvas.bounds.right))[1] == mean_x
        assert sorted((mean_y,
                sample.canvas.bounds.top,
                sample.canvas.bounds.bottom))[1] == mean_y
        assert np.all(band_names == es.band_order)
        assertions_on_band_metadata(sample.attrs)


@pytest.mark.skipif(not ELM_HAS_EXAMPLES,
               reason='elm-data repo has not been cloned')
def test_reader_kwargs():
    band_specs_kwargs = []
    for b in band_specs:
        b = attr.asdict(b)
        b['buf_xsize'], b['buf_ysize'] = 200, 300
        band_specs_kwargs.append(BandSpec(**b))
    meta = load_dir_of_tifs_meta(TIF_DIR, band_specs_kwargs)
    es = load_dir_of_tifs_array(TIF_DIR, meta, band_specs_kwargs)
    for b in es.band_order:
        assert getattr(es, b).values.shape == (300, 200)

