export BUILD_DIR=`pwd -P`
if [ "$MAKE_MINICONDA" = "" ];then
    echo
else
    wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh
    bash miniconda.sh -b -p $HOME/miniconda
    export PATH="$HOME/miniconda/bin:$PATH"
fi
source deactivate
export env_=earth-env-test
conda env remove --name ${env_} &> /dev/null
conda config --set always_yes true
conda env update -n ${env_} -f environment.yml
source activate ${env_}
python setup.py develop
export ELM_EXAMPLE_DATA_PATH=$(pwd -P)/elm-data
conda install -c defaults -c conda-forge requests pbzip2 python-magic six # for download_test_data.py
mkdir -p $ELM_EXAMPLE_DATA_PATH && cd $ELM_EXAMPLE_DATA_PATH && python "${BUILD_DIR}/scripts/download_test_data.py"

# TODO remove this following line once data
# downloader for Tiffs is okay
rm -rf tif
python -c 'from earthio.s3_landsat_util import SceneDownloader;s = SceneDownloader();row = s.lowest_cloud_cover_image();s.download_all_bands(row.download_url.iloc[0])'
## End of section that needs to be removed soon
cd $BUILD_DIR
ls -lRth $ELM_EXAMPLE_DATA_PATH


