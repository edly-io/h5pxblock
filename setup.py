"""Setup for h5pxblock XBlock."""


import os

from pathlib import Path
from setuptools import setup

this_directory = Path(__file__).parent
long_description = (this_directory / "README.md").read_text()


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
    name='h5p-xblock',
    version='0.2.17',
    description='XBlock to play self hosted h5p content inside open edX',
    long_description=long_description,
    long_description_content_type='text/markdown',
    url='https://github.com/edly-io/h5pxblock',
    license='MIT',
    author='edly',
    author_email='hello@edly.io',
    keywords='python edx h5p xblock',
    packages=[
        'h5pxblock',
    ],
    install_requires=[
        'XBlock',
    ],
    classifiers=[
        'Development Status :: 4 - Beta',
        'Framework :: Django',
        'Framework :: Django :: 3.2',
        'Framework :: Django :: 4.0',
        'Intended Audience :: Developers',
        'License :: OSI Approved :: MIT License',
        'Natural Language :: English',
        'Programming Language :: Python :: 3',
        'Programming Language :: Python :: 3.8',
    ],
    entry_points={
        'xblock.v1': [
            'h5pxblock = h5pxblock:H5PPlayerXBlock',
        ]
    },
    package_data=package_data("h5pxblock", ["static", "public", "translations"]),
)
