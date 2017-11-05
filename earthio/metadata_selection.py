'''
----------------------------------

``elm.sample_util.meta_selection``
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

'''

from __future__ import absolute_import, division, print_function, unicode_literals

from collections import OrderedDict

import logging
import pandas as pd
import re

from earthio.util import LayerSpec
from six import string_types

logger = logging.getLogger(__name__)

def _strip_key(k):
    if isinstance(k, string_types):
        for delim in ('.', '_', '-', ' '):
            k = k.lower().replace(delim,'')
    return k

def match_meta(meta, layer_spec):
    '''
    Parmeters:
        :meta: dataset meta information object
        :layer_spec: LayerSpec object

    Returns:
        :boolean: of whether layer_spec matches meta

    '''
    if not isinstance(layer_spec, LayerSpec):
        raise ValueError('layer_spec must be earthio.LayerSpec object')
    dir_re = dir(re)
    for mkey in meta:
        key_re = layer_spec.key_re_flags or []
        if isinstance(key_re, string_types):
            key_re = [key_re]
        value_re = layer_spec.value_re_flags or []
        if isinstance(value_re, string_types):
            key_re = [value_re]
        key_re_flags = [getattr(re, att) for att in (key_re) if att in dir_re]
        value_re_flags = [getattr(re, att) for att in (value_re) if att in dir_re]
        if bool(re.search(layer_spec.search_key, mkey, *key_re_flags)):
            if bool(re.search(layer_spec.search_value, meta[mkey], *value_re_flags)):
                return True
    return False


def meta_is_day(attrs):
    '''Helper to find day/ night flags in nested dict

    Parmeters:
        :d: dict

    Returns:
        :True: if day, **False** if night, else None

    '''
    dicts = []
    for k, v in attrs.items():
        if isinstance(v, dict):
            dicts.append(v)
            continue
        key2 = _strip_key(k)
        dayflag = 'day' in key2
        nightflag = 'night' in key2
        if dayflag and nightflag:
            value2 = _strip_key(v)
            return 'day' in value2.lower()
        elif dayflag or nightflag:
            return bool(v)
    if dicts:
        return any(meta_is_day(d2) for d2 in dicts)
    return False
