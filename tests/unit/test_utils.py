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
