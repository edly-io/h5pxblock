"""
Utility methods for xblock
"""
import logging
import os
import shutil

from zipfile import is_zipfile, ZipFile
from django.conf import settings

log = logging.getLogger(__name__)


MAX_WORKERS = getattr(settings, "THREADPOOLEXECUTOR_MAX_WORKERS", 10)


def str2bool(val):
    """ Converts string value to boolean"""
    return val in ['True', 'true', '1']


def delete_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def unpack_package(package, path):
    """
    Unpacks a zip file in local path
    """
    delete_path(path)
    os.makedirs(path)

    if not is_zipfile(package):
        log.error('%s is not a valid zip', package.name)
        return

    with ZipFile(package, 'r') as zip:
        log.info('Extracting all the files now from %s', package.name)
        zip.extractall(path)
