export BUILD_DIR=`pwd -P`
if [ "$MAKE_MINICONDA" = "" ];then
    echo
else
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"
fi
export env_=earth-env-test
conda env remove --name ${env_} &> /dev/null
conda config --set always_yes true
conda env update -n ${env_} -f environment.yml
source activate ${env_}
python setup.py develop
export ELM_EXAMPLE_DATA_PATH=$(pwd -P)/elm-data
conda install -c defaults -c conda-forge requests pbzip2 python-magic six # for download_test_data.py
mkdir -p $ELM_EXAMPLE_DATA_PATH && cd $ELM_EXAMPLE_DATA_PATH && python "${BUILD_DIR}/scripts/download_test_data.py"
cd $BUILD_DIR
ls -lRth $ELM_EXAMPLE_DATA_PATH
