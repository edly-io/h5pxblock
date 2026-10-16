"""
Utility methods for xblock
"""
import concurrent.futures
import logging
import os
import shutil
from urllib.parse import unquote, urlparse
from zipfile import ZipFile, is_zipfile

from django.conf import settings
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage as django_default_storage
from django.utils.module_loading import import_string

log = logging.getLogger(__name__)


MAX_WORKERS = getattr(settings, "THREADPOOLEXECUTOR_MAX_WORKERS", 10)


def get_h5p_storage():
    """
    Returns storage for h5p content

    Priority:
      1) If Django STORAGES defines "h5pxblock_storage", return that instance.
      2) If legacy H5PXBLOCK_STORAGE is defined, import the class and instantiate
         with provided settings.
      3) Fallback to Django's default_storage singleton.
    """
    # Priority 1: Django 4.2+/5.x STORAGES registry
    storages_config = getattr(settings, 'STORAGES', {})
    if isinstance(storages_config, dict) and "h5pxblock_storage" in storages_config:
        # Prefer Django's storages registry if available (Django 4.2+/5.x)
        from django.core.files import storage as storage_module
        if hasattr(storage_module, 'storages'):
            return storage_module.storages["h5pxblock_storage"]
        # Manual instantiation path for environments without the handler
        cfg = storages_config.get("h5pxblock_storage", {})
        backend_path = cfg.get("BACKEND")
        options = cfg.get("OPTIONS", {})
        if backend_path:
            backend_cls = import_string(backend_path)
            return backend_cls(**options)

    # Priority 2: Legacy per-app config
    h5p_storage_settings = getattr(settings, "H5PXBLOCK_STORAGE", None)
    if not h5p_storage_settings:
        return django_default_storage

    storage_class_import_path = (
        h5p_storage_settings.get("storage_class")
        or h5p_storage_settings.get("STORAGE_CLASS")
    )
    storage_settings = (
        h5p_storage_settings.get("settings")
        or h5p_storage_settings.get("STORAGE_KWARGS")
        or {}
    )

    if storage_class_import_path:
        storage_class = import_string(storage_class_import_path)
        return storage_class(**storage_settings)

    # Priority 3: Fallback to default storage
    return django_default_storage


def cloud_key_from_url(url):
    """
    Return the "h5pxblockmedia/..." storage key inside an absolute content URL, or None.
    """
    if not url or not isinstance(url, str):
        return None
    parsed = urlparse(url.strip())
    if not parsed.scheme or not parsed.netloc:
        return None
    path = unquote(parsed.path)
    idx = path.find("/h5pxblockmedia/")
    if idx < 0:
        return None
    return path[idx + 1:].rstrip("/")


def str2bool(val):
    """ Converts string value to boolean"""
    return val in ['True', 'true', '1']


def delete_path(path):
    if os.path.exists(path):
        shutil.rmtree(path)


def future_result_handler(future):
    """
    Prints results of future in logs
    """
    try:
        log.info("Future task completed: Result:[%s]", future.result())
    except BaseException as exp:
        log.error("Future completed with error %s", exp)


def delete_existing_files_cloud(storage, path):
    """
    Recusively delete all files under given path on cloud storage
    """
    if storage.exists(path):
        log.info("%s path is being deleted on cloud", path)
        dir_names, file_names = storage.listdir(path)
        with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            for file_name in file_names:
                file_path = os.path.join(path, file_name)
                future = executor.submit(storage.delete, file_path)
                future.add_done_callback(future_result_handler)

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
            for zipfile_name in h5p_zip.namelist():
                real_path = os.path.join(path, zipfile_name)
                if not os.path.basename(real_path) in {"", ".", ".."}:  # skip invalid or dangerous paths
                    future = executor.submit(storage.save, real_path, ContentFile(h5p_zip.read(zipfile_name)))
                    future.add_done_callback(future_result_handler)
