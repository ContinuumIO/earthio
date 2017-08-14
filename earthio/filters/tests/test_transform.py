from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict
import copy
import glob
import os

import pytest
import yaml

from sklearn.decomposition import IncrementalPCA

from earthio.filters.config.tests.fixtures import *
from earthio.reshape import *
from earthio import ElmStore
from earthio.filters.make_blobs import random_elm_store

X = flatten(random_elm_store())

def _run_assertions(trans, y, sample_weight):
    assert y is None
    assert sample_weight is None
    assert isinstance(trans, ElmStore)
    assert hasattr(trans, 'flat')
    assert tuple(trans.flat.dims) == ('space', 'band')
    assert trans.flat.values.shape[1] == 3
    assert trans.flat.values.shape[0] == X.flat.values.shape[0]


@pytest.mark.skip('Depends on elm.pipeline.steps')
def test_fit_transform():
    t = steps.Transform(IncrementalPCA(n_components=3))
    trans, y, sample_weight = t.fit_transform(X)
    _run_assertions(trans, y, sample_weight)

reason = ('Partial fit and Pipeline will be refactored '
          'significantly soon.  We need to make sure '
          'partial_fit of PCA is handled and tested, '
          'but not efficient to do so now.  A regression'
          ' test failure arose here due to bug fixed '
          'elsewhere for July 11 2017 NLDAS demo.')
@pytest.mark.skip('Depends on elm.pipeline.steps')
@pytest.mark.xfail(strict=False, reason=reason)
def test_partial_fit_transform():
    t = steps.Transform(IncrementalPCA(n_components=3), partial_fit_batches=3)
    trans, y, sample_weight = t.fit_transform(X)
    _run_assertions(trans, y, sample_weight)
    t2 = steps.Transform(IncrementalPCA(n_components=3), partial_fit_batches=3)
    with pytest.raises(TypeError):
        t2.partial_fit = None # will try to call this and get TypeError
        t2.fit_transform(X)


@pytest.mark.skip('Depends on elm.pipeline.steps')
def test_fit():
    t = steps.Transform(IncrementalPCA(n_components=3), partial_fit_batches=2)
    fitted = t.fit(X)
    assert isinstance(fitted, steps.Transform)
    assert isinstance(fitted._estimator, IncrementalPCA)
    trans, y, sample_weight = fitted.transform(X)
    _run_assertions(trans, y, sample_weight)

