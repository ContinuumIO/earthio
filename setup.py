import os
import glob
from setuptools import setup, find_packages

import versioneer

version = versioneer.get_version()
cmdclass = versioneer.get_cmdclass()
setup(name='earthio',
      version=version,
      cmdclass=cmdclass,
      description='Readers',
      include_package_data=True,
      install_requires=[],
      packages=['earthio', 'earthio.filters'],
      package_data={},
      entry_points={})
