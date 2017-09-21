
import json

import param
import yaml


class ServiceMetadata(param.Parameterized):
    display_name = param.String()
    description = param.String()
    geographical_area = param.String()
    bounding_boxes = param.String()
    service_type = param.String()
    geom_type = param.String()
    datatype = param.String()
    file_format = param.String()
    parameters = param.List()
    unmapped_parameters_available = param.Boolean()


class Features(param.Parameterized):
    file = param.String()
    format = param.List()


class Datasets(param.Parameterized):
    mapping = param.String()
    save_folder = param.String()


class Service(param.Parameterized):
    service_folder = param.List()
    service_id = param.String()
    metadata = param.ObjectSelector(default=ServiceMetadata())
    features = param.ObjectSelector(default=Features())
    datasets = param.ObjectSelector(default=Datasets())


class Organization(param.Parameterized):
    abbr = param.String()
    name = param.String()


class ProjectMetadata(param.Parameterized):
    display_name = param.String()
    description = param.String(allow_None=True)


class ConfigSpec(param.Parameterized):
    metadata = ProjectMetadata()
    env = param.Dict()
    cmd_args = param.Dict()
    services = param.List(class_=Service, instantiate=True)


import glob
import param.io
fnames = glob.glob('../../quest/examples/*conver*yml')
c = param.io.from_yaml(ConfigSpec(), fnames[0])
param.io.to_yaml(c, 'output_check.yml')
