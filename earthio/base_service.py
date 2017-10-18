import json
import logging
import os

import pandas as pd



logger = logging.getLogger()

reserved_feature_fields = [
    'display_name',
    'description',
    'reserved',
    'geometry',

]
reserved_geometry_fields = [
    'latitude',
    'longitude',
    'geom_type',
    'latitudes',
    'longitudes',
    'bbox',
]

reserved_feature_fields.extend(reserved_geometry_fields)

SERVICES = []

class BaseService(object):

    def __init__(self, name=None):
        self.name = name
        self._register()

    def get_features(self, service, update_cache=False):
        """Get Features associated with service.

        Take a series of query parameters and return a list of
        locations as a geojson python dictionary
        """
        cache_file = os.path.join(util.get_cache_dir(self.name), service + '_features.geojson')
        if not update_cache:
            try:
                features = gpd.read_file(cache_file)
                features.set_index('id', inplace=True)
                return features
            except:
                logger.info('updating cache')
                pass

        # get features from service
        features = self._get_features(service)

        # convert geometry into shapely objects
        if 'bbox' in features.columns:
            features['geometry'] = features['bbox'].apply(lambda row: box(*[float(x) for x in row]))
            del features['bbox']

        if all(x in features.columns for x in ['latitude', 'longitude']):
            fn = lambda row: Point((
                                    float(row['longitude']),
                                    float(row['latitude'])
                                    ))
            features['geometry'] = features.apply(fn, axis=1)
            features['geometry'] = features.apply(fn, axis=1)

        if 'geometry' in features.columns:
            # TODO
            # check for geojson str or shapely object
            pass

        # if no geometry fields are found then this is a geotypical feature
        if 'geometry' not in features.columns:
            features['geometry'] = None

        # add defaults values
        if 'display_name' not in features.columns:
            features['display_name'] = features.index

        if 'description' not in features.columns:
            features['description'] = ''

        # merge extra data columns/fields into metadata as a dictionary
        extra_fields = list(set(features.columns.tolist()) - set(reserved_feature_fields))
        # change NaN to None so it can be JSON serialized properly
        features['metadata'] = [{k: None if v != v else v for k, v in record.items()}
                                for record in features[extra_fields].to_dict(orient='records')]
        features.drop(extra_fields, axis=1, inplace=True)
        columns = list(set(features.columns.tolist()).intersection(reserved_geometry_fields))
        features.drop(columns, axis=1, inplace=True)

        params = self._get_parameters(service, features)
        if isinstance(params, pd.DataFrame):
            groups = params.groupby('service_id').groups
            features['parameters'] = features.index.map(lambda x: ','.join(filter(None, params.loc[groups[x]]['parameter'].tolist())) if x in groups.keys() else '')
            #features['parameter_codes'] = features.index.map(lambda x: ','.join(filter(None, params.loc[groups[x]]['_parameter_code'].tolist())) if x in groups.keys() else '')
        else:
            features['parameters'] = ','.join(params['parameters'])
            #features['parameter_codes'] = ','.join(params['parameter_codes'])

        # convert to GeoPandas GeoDataFrame
        features = gpd.GeoDataFrame(features, geometry='geometry')

        # write to cache_file
        util.mkdir_if_doesnt_exist(os.path.split(cache_file)[0])
        with open(cache_file, 'w') as f:
            f.write(features.to_json(default=util.to_json_default_handler))

        return features

    def get_services(self):
        return self._get_services()

    def get_parameters(self, service):
        return self._get_parameters(service)

    def download(self, service, feature, file_path, **kwargs):
        return self._download(service, feature, file_path, **kwargs)

    def download_options(self, service, fmt):
        return self._download_options(service, fmt)

    @abc.abstractmethod
    def _register(self):
        """"""
        global SERVICES

        SERVICES[self.name] = self
    @abc.abstractmethod
    def _get_services(self):
        """
        """

    @abc.abstractmethod
    def _get_features(self, service):
        """
        should return a pandas dataframe or a python dictionary with
        indexed by feature uid and containing the following columns

        reserved column/field names
            display_name -> will be set to uid if not provided
            description -> will be set to '' if not provided
            download_url -> optional download url

            defining geometry options:
                1) geometry -> geojson string or shapely object
                2) latitude & longitude columns/fields
                3) geometry_type, latitudes, longitudes columns/fields
                4) bbox column/field -> tuple with order (lon min, lat min, lon max, lat max)

        all other columns/fields will be accumulated in a dict and placed
        in a metadata field.

        """

    @abc.abstractmethod
    def _get_parameters(self, services):
        """
        """

    @abc.abstractmethod
    def _download(self, path, service, feature, parameter, **kwargs):
        """
        needs to return dictionary
        eg. {'path': /path/to/dir/or/file, 'format': 'raster'}
        """

    @abc.abstractmethod
    def _download_options(self, service, fmt):
        """
        needs to return dictionary
        eg. {'path': /path/to/dir/or/file, 'format': 'raster'}
        """


class SingleFileBase(WebServiceBase):
    """Base file for datasets that are a single file download
    eg elevation raster etc
    """
    def _download(self, service, feature, file_path, **kwargs):
        feature = self.get_features(service).loc[feature]
        reserved = feature.get('reserved')
        download_url = reserved['download_url']
        fmt = reserved.get('extract_from_zip', '')
        filename = reserved.get('filename', util.uuid('dataset'))
        datatype = self._get_services()[service].get('datatype')
        file_path = self._download_file(file_path, download_url, fmt, filename)
        return {
            'file_path': file_path,
            'file_format': reserved.get('file_format'),
            'parameter': feature.get('parameters'),
            'datatype': datatype,
        }

    def _download_options(self, service, fmt):
        return {}

    def _download_file(self, path, url, tile_fmt, filename, check_modified=False):
        util.mkdir_if_doesnt_exist(path)
        util.mkdir_if_doesnt_exist(os.path.join(path, 'zip'))
        tile_path = os.path.join(path, filename)
        logger.info('... downloading %s' % url)

        if tile_fmt == '':
            ulmo.util.download_if_new(url, tile_path, check_modified=check_modified)
        else:
            zip_path = os.path.join(path, 'zip', filename)
            ulmo.util.download_if_new(url, zip_path, check_modified=check_modified)
            logger.info('... ... zipfile saved at %s' % zip_path)
            tile_path = ulmo.util.extract_from_zip(zip_path, tile_path, tile_fmt)

        return tile_path
