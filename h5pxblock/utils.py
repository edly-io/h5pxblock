"""
Utility methods for xblock
"""
import concurrent.futures
import logging
import os
import shutil

from zipfile import is_zipfile, ZipFile
from django.conf import settings
from django.core.files.base import ContentFile

log = logging.getLogger(__name__)


MAX_WORKERS = getattr(settings, "THREADPOOLEXECUTOR_MAX_WORKERS", 10)


def str2bool(val):
    """ Converts string value to boolean"""
    return val in ['True', 'true', '1']


def delete_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def delete_existing_files_cloud(storage, path):
    """
    Recusively delete all files under given path on cloud storage
    """
    log.info("%s path is being deleted on cloud", path)
    dir_names, file_names = storage.listdir(path)
    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        tracker_futures = []
        for file_name in file_names:
            file_path = os.path.join(path, file_name)
            tracker_futures.append(
                executor.submit(storage.delete, file_path)
            )
            log.info("%s file deleted on cloud", file_path)

    for dir_name in dir_names:
        dir_path = os.path.join(path, dir_name)
        delete_existing_files_cloud(storage, dir_path)


def unpack_package_local_path(package, path):
    """
    Unpacks a zip file in local path
    """
    delete_path(path)
    os.makedirs(path)

    if not is_zipfile(package):
        log.error('%s is not a valid zip', package.name)
        return

    with ZipFile(package, 'r') as h5p_zip:
        log.info('Extracting all the files now from %s', package.name)
        h5p_zip.extractall(path)


def unpack_and_upload_on_cloud(package, storage, path):
    """
    Unpacks a zip file and upload it on cloud storage
    """
    if not is_zipfile(package):
        log.error('%s is not a valid zip', package.name)
        return

    delete_existing_files_cloud(storage, path)

    with ZipFile(package, 'r') as h5p_zip:
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            tracker_futures = []
            for zipfile_name in h5p_zip.namelist():
                real_path = os.path.join(path, zipfile_name)
                log.info('Uploading file %s to cloud storage ', zipfile_name)
                tracker_futures.append(
                    executor.submit(storage.save, real_path, ContentFile(h5p_zip.read(zipfile_name)))
                )
