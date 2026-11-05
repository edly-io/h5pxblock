"""
Tests for h5pxblock.utils.
"""
import pytest

from h5pxblock.utils import cloud_key_from_url

KEY = "h5pxblockmedia/ochin/CHWS101/7a6e7002a0814d01ad346510c64888e3"


@pytest.mark.parametrize("url, expected", [
    (f"https://edly-prod-multisites-koa-edx-storage.s3.amazonaws.com/{KEY}", KEY),
    (f"https://edly-prod-multisites-koa-edx-storage.s3.amazonaws.com/{KEY}/", KEY),
    (f"https://s3.amazonaws.com/edly-prod-multisites-koa-edx-storage/{KEY}", KEY),
    (f"https://bucket.s3.amazonaws.com/{KEY}?X-Amz-Signature=abc&X-Amz-Expires=3600", KEY),
    (f"  https://cdn.example.com/{KEY}  ", KEY),
    ("https://bucket.s3.amazonaws.com/h5pxblockmedia/org%20x/c/b", "h5pxblockmedia/org x/c/b"),
])
def test_extracts_key(url, expected):
    assert cloud_key_from_url(url) == expected


@pytest.mark.parametrize("url", [
    None,
    "",
    123,
    f"/{KEY}",
    KEY,
    "https://h5p.org/h5p/embed/123",
    "https://bucket.s3.amazonaws.com/other/h5pxblockmedia-ish/x",
])
def test_returns_none(url):
    assert cloud_key_from_url(url) is None


import io
import logging
import zipfile
from concurrent.futures import Future
from unittest import mock

from django.conf import settings
from django.core.files import storage as storage_module
from django.core.files.storage import FileSystemStorage, InMemoryStorage, default_storage
from django.test import override_settings

from h5pxblock import utils

BACKEND = "django.core.files.storage.InMemoryStorage"


def make_zip(entries):
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as archive:
        for name, data in entries.items():
            archive.writestr(name, data)
    buf.seek(0)
    buf.name = "package.h5p"
    return buf


def not_a_zip():
    buf = io.BytesIO(b"plain text")
    buf.name = "bad.h5p"
    return buf


class FakeCloud:
    """Dict-backed storage with the listdir/exists/delete/save subset the utils use."""

    def __init__(self, files=()):
        self.files = set(files)
        self.saved = {}
        self.deleted = []

    def exists(self, path):
        return any(f == path or f.startswith(path + "/") for f in self.files)

    def listdir(self, path):
        prefix = path + "/"
        names = [f[len(prefix):] for f in self.files if f.startswith(prefix)]
        return (
            sorted({n.split("/")[0] for n in names if "/" in n}),
            sorted(n for n in names if "/" not in n),
        )

    def delete(self, path):
        self.deleted.append(path)

    def save(self, path, content):
        self.saved[path] = content.read()


def test_storage_from_registry():
    registry = {"h5pxblock_storage": "registry-storage"}
    with override_settings(STORAGES={"h5pxblock_storage": {"BACKEND": BACKEND}}):
        with mock.patch.object(storage_module, "storages", registry):
            assert utils.get_h5p_storage() == "registry-storage"


def test_storage_from_manual_backend_without_registry(monkeypatch):
    monkeypatch.delattr(storage_module, "storages")
    monkeypatch.setattr(settings, "STORAGES", {"h5pxblock_storage": {"BACKEND": BACKEND, "OPTIONS": {}}})
    assert isinstance(utils.get_h5p_storage(), InMemoryStorage)


def test_storages_entry_without_backend_falls_through_to_default(monkeypatch):
    monkeypatch.delattr(storage_module, "storages")
    monkeypatch.setattr(settings, "STORAGES", {"h5pxblock_storage": {}})
    assert utils.get_h5p_storage() is default_storage


@pytest.mark.parametrize("config", [
    {"storage_class": "django.core.files.storage.FileSystemStorage", "settings": {"location": "/tmp/x"}},
    {"STORAGE_CLASS": "django.core.files.storage.FileSystemStorage", "STORAGE_KWARGS": {"location": "/tmp/x"}},
])
def test_storage_from_legacy_setting(config):
    with override_settings(H5PXBLOCK_STORAGE=config):
        result = utils.get_h5p_storage()
    assert isinstance(result, FileSystemStorage)
    assert result.location == "/tmp/x"


@pytest.mark.parametrize("config", [None, {}, {"settings": {}}])
def test_storage_defaults(config):
    with override_settings(H5PXBLOCK_STORAGE=config):
        assert utils.get_h5p_storage() is default_storage


@pytest.mark.parametrize("value, expected", [
    ("True", True), ("true", True), ("1", True), ("false", False), ("", False), (None, False),
])
def test_str2bool(value, expected):
    assert utils.str2bool(value) is expected


def test_delete_path(tmp_path):
    target = tmp_path / "gone"
    (target / "sub").mkdir(parents=True)
    utils.delete_path(str(target))
    assert not target.exists()
    utils.delete_path(str(target))


def test_future_result_handler_logs_result_and_error(caplog):
    ok, bad = Future(), Future()
    ok.set_result("saved")
    bad.set_exception(RuntimeError("boom"))
    with caplog.at_level(logging.INFO):
        utils.future_result_handler(ok)
        utils.future_result_handler(bad)
    assert "Result:[saved]" in caplog.text
    assert "Future completed with error boom" in caplog.text


def test_delete_existing_files_cloud_is_recursive():
    cloud = FakeCloud(["root/a.txt", "root/sub/b.txt", "root/sub/deep/c.txt"])
    utils.delete_existing_files_cloud(cloud, "root")
    assert sorted(cloud.deleted) == ["root/a.txt", "root/sub/b.txt", "root/sub/deep/c.txt"]


def test_delete_existing_files_cloud_missing_path():
    cloud = FakeCloud()
    utils.delete_existing_files_cloud(cloud, "root")
    assert not cloud.deleted


def test_unpack_local_extracts_and_replaces_old_content(tmp_path):
    target = tmp_path / "pkg"
    target.mkdir()
    (target / "stale.txt").write_text("old")
    utils.unpack_package_local_path(make_zip({"h5p.json": "{}", "content/c.json": "[]"}), str(target))
    assert sorted(p.relative_to(target).as_posix() for p in target.rglob("*") if p.is_file()) == [
        "content/c.json", "h5p.json",
    ]


def test_unpack_local_rejects_non_zip(tmp_path, caplog):
    target = tmp_path / "pkg"
    utils.unpack_package_local_path(not_a_zip(), str(target))
    assert target.is_dir() and not any(target.iterdir())
    assert "bad.h5p is not a valid zip" in caplog.text


def test_unpack_cloud_uploads_files_and_skips_dir_entries():
    cloud = FakeCloud(["base/old.txt"])
    package = make_zip({"h5p.json": "{}", "content/": "", "content/c.json": "[]", "x/..": "evil"})
    utils.unpack_and_upload_on_cloud(package, cloud, "base")
    assert cloud.saved == {"base/h5p.json": b"{}", "base/content/c.json": b"[]"}
    assert cloud.deleted == ["base/old.txt"]


def test_unpack_cloud_rejects_non_zip(caplog):
    cloud = FakeCloud(["base/old.txt"])
    utils.unpack_and_upload_on_cloud(not_a_zip(), cloud, "base")
    assert not cloud.saved and not cloud.deleted
    assert "bad.h5p is not a valid zip" in caplog.text
