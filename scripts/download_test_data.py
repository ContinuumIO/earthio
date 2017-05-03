#!/usr/bin/env python


"""
Setup:
    conda install -c defaults -c conda-forge python=3 requests pbzip2

Usage:
    ./download_test_data.py --files hdf4.tar.bz2 hdf5.tar.bz2 netcdf.tar.bz2 tif.tar.bz2
"""


import sys
import os
import tarfile
import subprocess
import shutil
import argparse

import requests
import magic
from six import print_


DEFAULT_S3_BUCKET = 'elm-test-data'
DEFAULT_S3_FILENAMES = ['hdf4.tar.bz2', 'hdf5.tar.bz2', 'netcdf.tar.bz2', 'tif.tar.bz2']
DEFAULT_TMPDIR = '/tmp'


class DownloadError(Exception):
    """Raised when file failed to successfully download from URL."""
    def __init__(self, url, status_code):
        self.message = 'Failed to download file from "{}". Status code: {}'.format(url, status_code)


class DecompressionError(Exception):
    """Raised when compressed file is not properly decompressed."""
    def __init__(self, compressed_fpath, fmt='bzip2'):
        self.message = 'Failed to decompress "{}". Please ensure it is in {} format.'.format(compressed_fpath, fmt)


class ExtractionError(Exception):
    """Raised when archive file is not properly extracted."""
    def __init__(self, archive_fpath, fmt='tar'):
        self.message = 'Failed to extract "{}". Please ensure it in {} format.'.format(archive_fpath, fmt)


def get_filetype(fpath):
    """Return a mime-style filetype string."""
    return magic.from_file(fpath, mime=True)


def decompress(compressed_fpath):
    """Return a filepath to decompressed version of compressed_fpath, after decompressing it.
    Raise DecompressionError if decompression fails.
    """
    # Assert that the file is bzip2-compressed
    if get_filetype(compressed_fpath) != 'application/x-bzip2':
        raise FileTypeError(compressed_fpath, target_fmt='bzip2')

    # Decompress the file
    try:
        print_('Decompressing...')
        subprocess.check_call('pbzip2 -d -k -f {}'.format(compressed_fpath), shell=True)

        # Check that file was decompressed properly
        fpath = os.path.splitext(compressed_fpath)[0]
        if not os.path.isfile(fpath):
            raise DecompressionError(compressed_fpath)
    except subprocess.CalledProcessError:
        raise DecompressionError(compressed_fpath)

    return fpath


def extract(archive_fpath):
    """Return a filepath to extracted version of archive_fpath, after decompressing it.
    Raise ExtractionError if decompression fails.
    """
    # Assert that the decompresed file is a tar archive
    assert get_filetype(archive_fpath) == 'application/x-tar'

    # Extract tar archive
    fpath = os.path.splitext(archive_fpath)[0]
    print_('Extracting "{}"...'.format(fpath))
    with tarfile.open(archive_fpath, "r:") as tfp:
        tfp.extractall()

    # Check that file was extracted properly
    if not os.path.exists(fpath):
        raise ExtractionError(compressed_fpath)

    return fpath


def download_file(url, to, tmpdir='/tmp'):
    """Download file from url to filepath "to".
    Raise DownloadError if download fails.
    """
    tmp_fpath = os.path.join(tmpdir, to+'.tmp')

    resp = requests.get(url, stream=True)
    if resp.status_code != 200:
        raise DownloadError(url, resp.status_code)

    with open(tmp_fpath, 'wb') as f:
        content_length = int(resp.headers.get('Content-Length'))
        for chunkct, chunk in enumerate(resp.iter_content(chunk_size=1024)):
            if chunk:
                f.write(chunk)
                f.flush()
            if chunkct % 10000 == 0:
                print_('Downloading "{}"... {:.2f}%'.format(url, ((chunkct+1)*1024*100) / content_length), flush=True, end='\r')
    print_('Downloading "{}"... {:.2f}%'.format(url, 100), flush=True)

    shutil.move(tmp_fpath, to)


def main(argv):
    parser = argparse.ArgumentParser()
    parser.add_argument('--bucket-name', default=DEFAULT_S3_BUCKET, help='Name of S3 bucket [default: {}]'.format(DEFAULT_S3_BUCKET))
    parser.add_argument('--tmpdir', default=DEFAULT_TMPDIR, help='Location to store downloaded files before they\'re finished downloading [default: {}]'.format(DEFAULT_TMPDIR))
    parser.add_argument('--files', nargs='*', default=DEFAULT_S3_FILENAMES, help='Names of files in S3 bucket [default: {}]'.format(DEFAULT_S3_FILENAMES))
    args = parser.parse_args()

    for fname in args.files:
        url = 'http://{}.s3.amazonaws.com/{}'.format(args.bucket_name, fname)
        try:
            if os.path.isfile(fname):
                print_('Skipping download for "{}"; file already present.'.format(fname))
            else:
                download_file(url, fname, tmpdir=args.tmpdir)
            archive_fpath = decompress(fname)
            data_path = extract(archive_fpath)
            os.remove(archive_fpath)
        except (DownloadError, DecompressionError, ExtractionError) as err:
            print_('{}: {}'.format(type(err).__name__, err.message))
            print_('Skipping...')

    return 0


if __name__ == '__main__':
    sys.exit(main(sys.argv))
