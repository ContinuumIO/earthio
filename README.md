# Ensemble Learning Models - Data Readers

### Work in Progress

Currently this can be installed with

```
git clone https://github.com/ContinuumIO/earth-env
conda create -n earth-env -c ioam -c conda-forge -c scitools/label/dev -c gbrener earth-env
source activate earth-env
cd ../elm-readers && python setup.py develop
python -c "from elm.readers import *"
```

### Testing

Tests are probably still broken due to package move refactor.

Download test data with

```
conda install -c defaults -c conda-forge requests pbzip2 python-magic six
python ./scripts/download_test_data.py
```
