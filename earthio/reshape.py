'''
-----------------------

``earthio.reshape``
~~~~~~~~~~~~~~~~~~~~~~~

'''

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import namedtuple, OrderedDict
import copy
from functools import wraps
import gc
import logging
import os

import attr
import numpy as np
import scipy.interpolate as spi
import xarray as xr

from earthio import Canvas
from earthio.util import (canvas_to_coords,
                              VALID_X_NAMES,
                              VALID_Y_NAMES,
                              get_shared_canvas)

logger = logging.getLogger(__name__)

AGG_METHODS = tuple('all any argmax argmin max mean median min prod sum std var'.split())

__all__ = ['select_canvas',
           'drop_na_rows',
           'flatten',
           'filled_flattened',
           'check_is_flat',
           'inverse_flatten',
           'aggregate_simple',
           'transpose',
           ]

def transpose(es, new_dims):
    '''Transpose an xr.Dataset - elm.pipeline.steps.Transpose

    Parameters:
        :new_dims: passed to xarray.DataArray.transpose
    Returns:
        :Dataset: transposed
    '''
    trans = OrderedDict()
    for layer in es.data_vars:
        data_arr = getattr(es, layer)
        if not len(set(new_dims) & set(data_arr.dims)) == len(new_dims):
            raise ValueError('At least one of new_dims is not an existing dim (new_dims {}, existing {})'.format(new_dims, data_arr.dims))
        trans[layer] = data_arr.transpose(*new_dims)
        canvas = attr.asdict(trans[layer].canvas)
        canvas['dims'] = new_dims
        trans[layer].attrs['canvas'] = Canvas(**canvas)
    return xr.Dataset(trans, attrs=es.attrs)


def aggregate_simple(es, **kwargs):
    '''aggregate xr.Dataset - elm.pipeline.steps.Agg

    Parameters:
        :kwargs: Keywords may contain
            - :func: aggregation func name like "mean", "std"
            - :dim: dimension name
            - :axis: dimension integer

    Returns:
        :Dataset: aggregated

    '''
    func = kwargs['func']
    if not func in AGG_METHODS:
        raise ValueError('Expected an agg "func" among: {}'.format(AGG_METHODS))

    kw = {k: v for k, v in kwargs.items()
          if k not in ('func',)}

    dim = kwargs.get('dim')
    axis = kwargs.get('axis')
    if isinstance(axis, int) and dim or (not isinstance(axis, int) and not dim):
        raise ValueError('kwargs given to aggregate_simple must include *one* of "dim" or "axis"')
    agged = OrderedDict()
    lost_axes = []
    for layer in es.data_vars:

        data_arr = getattr(es, layer)
        lost_axes.append(data_arr.dims.index(dim) if dim else axis)
        agged[layer] = getattr(data_arr, func)(**kw)
    if len(set(lost_axes)) != 1:
        raise ValueError('Cannot aggregate when the axis (dim) of aggregation is not the same for all DataArrays in xr.Dataset')
    return xr.Dataset(agged, attrs=es.attrs, add_canvas=False, lost_axis=lost_axes[0])


def select_canvas(es, new_canvas):
    '''reindex_like new_canvas for every layer (DataArray) in xr.Dataset

    Parameters:
        :es: xr.Dataset
        :new_canvas: an earthio.Canvas object

    Returns:
        :es: xr.Dataset where every layer (DataArray) has the same
            coordinates - those of new_canvas
    '''
    if getattr(es, '_dummy_canvas', False):
        raise ValueError('This xr.Dataset cannot be run through select_canvas because geo transform was not read correctly from input data')
    es_new_dict = OrderedDict()
    for layer in es.data_vars:
        data_arr = getattr(es, layer)
        if data_arr.canvas == new_canvas:
            new_arr = data_arr
            attrs = data_arr.attrs
        else:
            new_coords = canvas_to_coords(new_canvas)
            old_coords = canvas_to_coords(data_arr.canvas)
            old_dims = data_arr.canvas.dims
            new_dims = new_canvas.dims
            shp_order = []
            attrs = copy.deepcopy(data_arr.attrs)
            attrs['canvas'] = new_canvas
            for nd in new_dims:
                if not nd in old_dims:
                    raise ValueError()
                shp_order.append(old_dims.index(nd))
            index_to_make = xr.Dataset(new_coords)
            data_arr = data_arr.reindex_like(index_to_make, method='nearest')
        es_new_dict[layer] = data_arr
    attrs = copy.deepcopy(es.attrs)
    attrs['canvas'] = new_canvas
    es_new = xr.Dataset(es_new_dict, attrs=attrs)

    return es_new


def drop_na_rows(flat):
    '''Drop any NA rows from xr.Dataset flat'''
    check_is_flat(flat)
    flat_dropped = flat.flat.dropna(dim='space')
    flat_dropped.attrs.update(flat.attrs)
    flat_dropped.attrs['drop_na_rows'] = flat.flat.values.shape[0] - flat_dropped.shape[0]
    attrs = copy.deepcopy(flat.attrs)
    attrs.update(flat_dropped.attrs)
    attrs['shape_before_drop_na_rows'] = flat.flat.values.shape
    no_na = xr.Dataset({'flat': flat_dropped}, attrs=attrs)
    return no_na


def flatten(es, ravel_order='C'):
    '''Given an xr.Dataset with different rasters (DataArray) as layers,
    flatten the rasters into a single 2-D DataArray called "flat"
    in a new xr.Dataset.

    Params:
        :elm_store:  3-d xr.Dataset (layer, y, x)

    Returns:
        :elm_store:  2-d xr.Dataset (space, layer)
    '''
    if check_is_flat(es, raise_err=False):
        return es
    shared_canvas = get_shared_canvas(es)
    if not shared_canvas:
        raise ValueError('es.select_canvas should be called before flatten when, as in this case, the layers do not all have the same Canvas')
    store = None
    layer_names = [layer for idx, layer in enumerate(es.layer_order)]
    old_canvases = []
    old_dims = []
    for idx, layer in enumerate(layer_names):
        data_arr = getattr(es, layer, None)
        canvas = getattr(data_arr, 'canvas', None)
        old_canvases.append(canvas)
        old_dims.append(data_arr.dims)
        if store is None:
            # TODO consider canvas here instead
            # of assume fixed size, but that
            # makes reverse transform harder (is that important?)
            store = np.empty((data_arr.values.size,
                              len(es.data_vars))) * np.NaN
        if data_arr.values.ndim == 1:
            # its already flat
            new_values = data_arr.values
        else:
            new_values = data_arr.values.ravel(order=ravel_order)
        store[:, idx] = new_values
    attrs = {}
    attrs['canvas'] = shared_canvas
    attrs['old_canvases'] = old_canvases
    attrs['old_dims'] = old_dims
    attrs['flatten_data_array'] = True
    attrs.update(copy.deepcopy(es.attrs))
    flat = xr.Dataset({'flat': xr.DataArray(store,
                        coords=[('space', np.arange(store.shape[0])),
                                ('layer', layer_names)],
                        dims=('space',
                              'layer'),
                        attrs=attrs)},
                    attrs=attrs)
    return flat


def filled_flattened(na_dropped):
    '''Used by inverse_flatten to fill areas that were dropped
    out of X due to NA/NaN'''
    shp = getattr(na_dropped, 'shape_before_drop_na_rows', None)
    if not shp:
        return na_dropped
    shp = (shp[0], len(na_dropped.layer_order))
    filled = np.empty(shp) * np.NaN
    filled[na_dropped.space, :] = na_dropped.flat.values
    attrs = copy.deepcopy(na_dropped.attrs)
    attrs.update(copy.deepcopy(na_dropped.flat.attrs))
    attrs.pop('shape_before_drop_na_rows', None)
    attrs['notnull_shape'] = na_dropped.flat.values.shape
    layer = attrs['layer_order']
    filled_es = xr.Dataset({'flat': xr.DataArray(filled,
                                     coords=[('space', np.arange(shp[0])),
                                            ('layer', layer)],
                                     dims=('space', 'layer'),
                                     attrs=attrs)},
                                attrs=attrs)

    return filled_es


def check_is_flat(flat, raise_err=True):
    '''Check if an xr.Dataset has a DataArray called flat with dimensions (space, layer)

    Parameters:
        :flat: an xr.Dataset
        :raise_err: raise or not

    Returns:
        :bool: ``True`` if flat ``False`` or ``ValueError`` if not flat (raise_err=True)
    '''
    if not hasattr(flat, 'flat') or not all(hasattr(flat.flat, at) for at in ('space', 'layer')):
        msg = 'Expected an xr.Dataset with attribute "flat" and dims ("space", "layer")'
        if raise_err:
            raise ValueError(msg)
        else:
            return False
    return True


def inverse_flatten(flat, add_canvas=False, **attrs):
    '''Given an xr.Dataset that has been flattened to (space, layer) dims,
    return a 3-d xr.Dataset with dims (layer, y, x).  Requires that metadata
    about x,y dims were preserved when the 2-d input xr.Dataset was created

    Params:
        :flat: a 2-d xr.Dataset (space, layer)
        :attrs: attribute dict to update the dict of the returned xr.Dataset

    Returns:
        :es:  xr.Dataset (layer, y, x)
    '''
    flat = filled_flattened(flat)
    attrs2 = copy.deepcopy(flat.attrs)
    attrs3 = copy.deepcopy(flat.flat.attrs)
    attrs = copy.deepcopy(attrs)
    for idx, a in enumerate((attrs2, attrs3)):
        for k, v in a.items():
            if k == 'canvas' and idx == 1: continue
            attrs[k] = v
    layer_list = zip(flat.flat.layer_order, flat.old_dims)
    es_new_dict = OrderedDict()
    #raise ValueError(repr(attrs))
    if 'canvas' in attrs:
        new_coords = canvas_to_coords(attrs['canvas'])
    else:
        new_coords = attrs['old_coords']
    for idx, (layer, dims) in enumerate(layer_list):
        if idx >= flat.flat.values.shape[1]:
            break
        new_arr = flat.flat.values[:, idx]
        shp = tuple(new_coords[k].size for k in dims)
        new_arr = new_arr.reshape(shp, order='C')
        data_arr = xr.DataArray(new_arr,
                                coords=new_coords,
                                dims=dims,
                                attrs=attrs)
        es_new_dict[layer] = data_arr
    return xr.Dataset(es_new_dict, attrs=attrs, add_canvas=add_canvas)
