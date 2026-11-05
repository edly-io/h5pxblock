"""
Minimal Django settings so h5pxblock.utils can be imported outside the LMS.
"""
import django
from django.conf import settings

if not settings.configured:
    settings.configure()
    django.setup()

import importlib
from types import SimpleNamespace

import pytest
from xblock.field_data import DictFieldData
from xblock.fields import ScopeIds
from xblock.test.toy_runtime import ToyRuntime

block_module = importlib.import_module("h5pxblock.h5pxblock")


class CloudStorage:
    """Non-filesystem storage double that only knows how to build URLs."""

    def url(self, name):
        return f"https://cdn.example.com/{name}"


class Runtime(ToyRuntime):
    """ToyRuntime with the user and i18n services the block asks for."""

    def __init__(self):
        super().__init__()
        self.published = []
        self.publish_errors = {}

    def service(self, block, service_name):
        if service_name == "user":
            user = SimpleNamespace(full_name="Jane Doe", emails=["jane@example.com"])
            return SimpleNamespace(get_current_user=lambda: user)
        if service_name == "i18n":
            return SimpleNamespace(ugettext=str, gettext=str, ngettext=lambda one, many, n: one if n == 1 else many)
        raise KeyError(service_name)

    def publish(self, block, event_type, event_data):
        error = self.publish_errors.get(event_type)
        if error:
            raise error(event_data)
        self.published.append((event_type, event_data))


@pytest.fixture(autouse=True)
def due(monkeypatch):
    """The LMS injects `due` into every block; plain XBlock has none."""
    monkeypatch.setattr(block_module.H5PPlayerXBlock, "due", None, raising=False)


@pytest.fixture
def storage(monkeypatch):
    cloud = CloudStorage()
    monkeypatch.setattr(block_module, "H5P_STORAGE", cloud)
    return cloud


@pytest.fixture
def block(storage):  # pylint: disable=redefined-outer-name,unused-argument
    runtime = Runtime()
    xblock = block_module.H5PPlayerXBlock(
        runtime,
        field_data=DictFieldData({}),
        scope_ids=ScopeIds("student", "h5pxblock", "def", "usage"),
    )
    xblock.location = SimpleNamespace(org="org", course="course", block_id="blk")
    return xblock
