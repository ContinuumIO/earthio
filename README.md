# Ensemble Learning Models - Data Readers

### Work in Progress

Currently this can be installed with

```
git clone https://github.com/ContinuumIO/earth-env
cd earth-env && conda env create --file environment_36.yml
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
