from __future__ import absolute_import, division, print_function, unicode_literals

'''
-----------------------------------

``earthio.sample_util.sample_pipeline``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Utilities for taking the "pipelines" section of an elm
config and creating an elm.pipeline.Pipeline from them
'''

from collections import Sequence
import copy
from functools import partial
import logging
from pprint import pformat

from xarray_filters.mldataset import MLDataset
from earthio.reshape import flatten as _flatten
import numpy as np
import xarray as xr
from sklearn.utils import check_array as _check_array
import sklearn.preprocessing as skpre
import sklearn.feature_selection as skfeat

from xarray_filters.func_signatures import get_args_kwargs_defaults
from earthio.filters.change_coords import CHANGE_COORDS_ACTIONS
from earthio.filters.preproc_scale import SKLEARN_PREPROCESSING
try:
    from .. import load_meta, load_array
except ImportError:
    load_array = load_meta = None

from six import string_types

logger = logging.getLogger(__name__)

_SAMPLE_PIPELINE_SPECS = {}


def _split_pipeline_output(output, X, y,
                           sample_weight, context):
    '''Util to ensure a Pipeline func always returns (X, y, sample_weight) tuple'''
    if not isinstance(output, (tuple, list)):
        ret = output, y, sample_weight
    elif output is None:
        ret = X, y, sample_weight
    elif len(output) == 1:
        ret = output[0], y, sample_weight
    elif len(output) == 2:
        xx = output[0] if output[0] is not None else X
        yy = output[1] if output[1] is not None else y
        ret = (xx, yy, sample_weight,)
    elif len(output) == 3:
        xx = output[0] if output[0] is not None else X
        yy = output[1] if output[1] is not None else y
        sw = output[2] if output[2] is not None else sample_weight
        ret = (xx, yy, sw)
    else:
        raise ValueError('{} pipeline func returned '
                         'more than 3 outputs in a '
                         'tuple/list'.format(context))
    assert isinstance(ret, tuple) and not isinstance(ret[0], tuple)
    return ret


def create_sample_from_data_source(config=None, **data_source):
    '''Given sampling specs in a pipeline train or predict step,
    return pipe, a list of (func, args, kwargs) actions

    Params:
        :train_or_predict_dict: a "train" or "predict" dict from config
        :config:                full config
        :step:                  a dictionary that is the current step in the pipeline, like a "train" or "predict" step

    '''
    sampler_func = data_source['sampler'] # TODO: this needs to be
                                                        # added to ConfigParser
                                                        # validation (sampler requirement)
    sampler_args = data_source.get('sampler_args') or ()
    if not isinstance(sampler_args, (tuple, list)):
        sampler_args = (sampler_args,)
    reader_name = data_source.get('reader') or None
    if isinstance(reader_name, string_types) and reader_name:
        if config and reader_name in config.readers:
            reader = config.readers[reader_name]
        _load_meta = partial(load_meta, reader=reader_name)
        _load_array = partial(load_array, reader=reader_name)
    elif isinstance(reader_name, dict):
        reader = reader_name
        _load_meta = reader['load_meta']
        _load_array = reader['load_array']
    else:
        _load_array = load_array
        _load_meta = load_meta
    data_source['load_meta'] = _load_meta
    data_source['load_array'] = _load_array
    return sampler_func(*sampler_args, **data_source)


def check_array(arr, msg, **kwargs):
    '''Util func for checking sample remains finite and not-NaN'''
    if arr is None:
        raise ValueError('Array cannot be None ({}): '.format(msg))
    try:
        _check_array(arr, **kwargs)
    except Exception as e:
        shp = getattr(arr, 'shape', '(has no shape attribute)')
        logger.info('Failed on check_array on array with shape '
                    '{}'.format(shp))

        raise ValueError('check_array ({}) failed with {}'.format(msg, repr(e)))


def _has_arg(a):
    return not (a is None or (isinstance(a, list) and not a) or (hasattr(a, 'size') and a.size == 0))


def final_on_sample_step(fitter,
                         model, X,
                         fit_kwargs,
                         y=None,
                         sample_weight=None,
                         require_flat=True,
                         prepare_for='train'):
    '''This is the final transformation before the last estimator
    in a Pipeline is called.  It takes the numpy array for X
    needed by the estimator from X as an MLDataset

    Parameters:
        :fitter: fit function object
        :model:  the final estimator in a Pipeline
        :X:      MLDataset with DataArray "flat"
        :fit_kwargs: kwargs to fitter
        :y:      numpy array y if needed
        :sample_weight: numpy array if needed
        :require_flat: raise an error if the MLDataset has no "flat" band
        :prepare_for:  determines whether y is included in fit_args

    Returns
        :args, kwargs: that fitter should use

    '''
    fit_kwargs = copy.deepcopy(fit_kwargs or {})
    if y is None:
        y = fit_kwargs.pop('y', None)
    else:
        fit_kwargs.pop('y', None)
    if sample_weight is None:
        sample_weight = fit_kwargs.pop('sample_weight', None)
    else:
        fit_kwargs.pop('sample_weight', None)
    if isinstance(X, np.ndarray):
        X_values = X             # numpy array 2-d
    elif isinstance(X, (MLDataset, xr.Dataset)):
        if hasattr(X, 'flat'):
            X_values = X.flat.values
        else:
            logger.info("After running Pipeline, X is not an MLDataset with a DataArray called 'flat' and X is not a numpy array.  Found {}".format(type(X)))
            logger.info("Trying earthio.reshape:flatten on X. If this fails, try a elm.pipeline.steps:ModifySample step to create MLDataset with 'flat' DataArray")
            X = _flatten(X)
            X_values = X.flat.values
    else:
        X_values = X # may not be okay for sklearn models,e.g KMEans but can be passed thru Pipeline
    if X_values.ndim == 1:
        X_values = X_values.reshape(-1, 1)
    args, kwargs, var_keyword = get_args_kwargs_defaults(fitter)

    has_y = _has_arg(y)
    has_sw = _has_arg(sample_weight)
    if has_sw:
        fit_kwargs['sample_weight'] = sample_weight
    if 'check_input' in kwargs:
        fit_kwargs['check_input'] = True
    if has_y:
        if prepare_for == 'train':
            fit_args = (X_values, y)
        else:
            fit_args = (X,)
        logger.debug('X (shape {}) and y (shape {})'.format(X_values.shape, y.shape))
    else:
        if prepare_for == 'train':
            fit_args = (X_values,)
        else:
            fit_args = (X,)
        logger.debug('X (shape {})'.format(X_values.shape))
    check_array(X_values, "final_on_sample_step - X")
    if has_y:
        if y.size != X_values.shape[0]:
            raise ValueError("Bad size for y ({}) - does not match X.shape[0] ({})".format(y.size, X_values.shape[0]))
    if has_sw:
        if not sample_weight.size == X_values.shape[0]:
            raise ValueError("Bad size for sample_weight ({}) - does not match X.shape[0] ({})".format(sample_weight.size, X_values.shape[0]))
    if 'batch_size' in model.get_params():
        logger.debug('set batch_size {}'.format(X_values.shape[0]))
        model.set_params(batch_size=X_values.shape[0])
    return fit_args, fit_kwargs

