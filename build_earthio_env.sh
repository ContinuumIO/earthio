source deactivate;
export EARTHIO_BUILD_DIR=`pwd -P`
if [ "$EARTHIO_CHANNEL_STR" = "" ];then
    export EARTHIO_CHANNEL_STR=" -c ioam -c conda-forge -c scitools/label/dev ";
fi
if [ "$EARTHIO_TEST_ENV" = "" ];then
    export EARTHIO_TEST_ENV=earth-env-test;
fi
build_earthio_env(){
    if [ "$PYTHON_TEST_VERSION" = "" ];then
        echo Env variable PYTHON_TEST_VERSION is not defined. Set it to 2.7, 3.5 or 3.6 - FAIL ;
        return 1;
    fi
    if [ "$MAKE_MINICONDA" = "" ];then
        echo
    else
        wget https://repo.continuum.io/miniconda/Miniconda3-latest-Linux-x86_64.sh -O miniconda.sh || return 1;
        bash miniconda.sh -b -p $HOME/miniconda || return 1;
        export PATH="$HOME/miniconda/bin:$PATH";
    fi
    conda config --set always_yes true;

    conda install --name root conda conda-build;
    conda env remove --name ${EARTHIO_TEST_ENV} &> /dev/null;
    if [ "$EARTHIO_INSTALL_METHOD" = "" ];then
        export EARTHIO_INSTALL_METHOD="conda";
    fi
    if [ "$EARTHIO_INSTALL_METHOD" = "git" ];then
        conda env create -n ${EARTHIO_TEST_ENV} -f environment.yml  || return 1;
        source activate ${EARTHIO_TEST_ENV} || return 1;
        python setup.py develop || return 1;
    else
        conda build $EARTHIO_CHANNEL_STR --python $PYTHON_TEST_VERSION conda.recipe || return 1;
        conda create --use-local --name $EARTHIO_TEST_ENV $EARTHIO_CHANNEL_STR python=$PYTHON_TEST_VERSION earthio || return 1;
        source activate ${EARTHIO_TEST_ENV}  || return 1;
    fi
    if [ "$ELM_EXAMPLE_DATA_PATH" = "" ];then
        export ELM_EXAMPLE_DATA_PATH="${EARTHIO_BUILD_DIR}/../elm-data";
        conda install -c defaults -c conda-forge requests pbzip2 python-magic six  || return 1; # for download_test_data.py
        mkdir -p $ELM_EXAMPLE_DATA_PATH && cd $ELM_EXAMPLE_DATA_PATH && python "${EARTHIO_BUILD_DIR}/scripts/download_test_data.py" || return 1;
    fi
    cd $EARTHIO_BUILD_DIR || return 1;
}
build_earthio_env && source activate ${EARTHIO_TEST_ENV} && echo OK

