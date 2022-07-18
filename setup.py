"""Setup for h5pxblock XBlock."""


import os

from setuptools import setup


def package_data(pkg, roots):
    """Generic function to find package_data.

    All of the files under each of the `roots` will be declared as package
    data for package `pkg`.

    """
    data = []
    for root in roots:
        for dirname, _, files in os.walk(os.path.join(pkg, root)):
            for fname in files:
                data.append(os.path.relpath(os.path.join(dirname, fname), pkg))

    return {pkg: data}


setup(
    name='h5pxblock-xblock',
    version='0.1',
    description='XBlock to play self hosted h5p content inside open edX',
    license='MIT',
    packages=[
        'h5pxblock',
    ],
    install_requires=[
        'XBlock',
    ],
    entry_points={
        'xblock.v1': [
            'h5pxblock = h5pxblock:H5PPlayerXBlock',
        ]
    },
    package_data=package_data("h5pxblock", ["static", "public"]),
)
