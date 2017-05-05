# EarthIO: Geographic, scientific, and image file readers and utilities for Python visualization and machine learning

### Work in Progress

Currently this can be installed with:

```
git clone https://github.com/ContinuumIO/earthio.git
conda env create -f environment.yml
source activate earth-env
python setup.py develop
python -c "from earthio import *"
```

### Testing

Tests are probably still broken due to package move refactor.

Download test data with:

```
conda install -c defaults -c conda-forge requests pbzip2 python-magic six
python ./scripts/download_test_data.py
```
