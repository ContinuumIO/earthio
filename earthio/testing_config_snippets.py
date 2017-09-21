def old_style_converter(fname):
    new = fname.replace('.yml', '-converted.yml')
    new_services = []
    with open(fname) as f:
        obj = yaml.load(f.read())
        for k, v in obj['services'].items():
            v['service_id'] = k
            new_services.append(v)
        obj['services'] = new_services
    with open(new, 'w') as f:
        f.write(yaml.safe_dump(obj))
    with open(new.replace('yml', 'json'), 'w') as f:
        f.write(json.dumps(obj, indent=2))

def tester(old_fnames):
    for f in old_fnames:
        old_style_converter(f)

from param.io import *
import glob
import param.io
fnames = glob.glob('../../quest/examples/*conver*yml')
c = from_file(ConfigSpec(), fnames[0])
#d = to_params_dict(c)
u = param.io.unwinder(c)