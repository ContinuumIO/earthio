export EARTHIO_TEST_ENV=earth-env-test
build_earthio_env(){
    export BUILD_DIR=`pwd -P`
    if [ "$MAKE_MINICONDA" = "" ];then
        echo
    else
        wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh || return 1;
        bash miniconda.sh -b -p $HOME/miniconda || return 1;
        export PATH="$HOME/miniconda/bin:$PATH" || return 1;
    fi
    source deactivate  || return 1;
    conda install --name root conda conda-build;
    conda env remove --name ${EARTHIO_TEST_ENV} &> /dev/null;
    conda config --set always_yes true  || return 1;
    conda env create -n ${EARTHIO_TEST_ENV} -f environment.yml  || return 1;
    source activate ${EARTHIO_TEST_ENV}  || return 1;
    if [ "$EARTHIO_INSTALL_METHOD" = "" ];then
        export EARTHIO_INSTALL_METHOD="conda";
    fi
    if [ "$EARTHIO_INSTALL_METHOD" = "git" ];then
        python setup.py develop || return 1;
    else
        conda build -c conda-forge --python $EARTH_VERS conda.recipe || return 1;
    fi
    export ELM_EXAMPLE_DATA_PATH=$(pwd -P)/elm-data
    conda install -c defaults -c conda-forge requests pbzip2 python-magic six  || return 1;# for download_test_data.py
    mkdir -p $ELM_EXAMPLE_DATA_PATH && cd $ELM_EXAMPLE_DATA_PATH && python "${BUILD_DIR}/scripts/download_test_data.py"  || return 1;
    cd $BUILD_DIR
}
build_earthio_env && source activate ${EARTHIO_TEST_ENV} && echo OK

