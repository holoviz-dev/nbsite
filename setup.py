#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
import os
from setuptools import setup, find_packages

# import pyct.build
import param

NAME = 'nbsite'
DESCRIPTION = 'Build a tested, sphinx-based website from notebooks.'

setup_args = dict(
    name=NAME,
    # version=pyct.build.get_setup_version(__file__, NAME),
    version=param.version.get_setup_version(__file__, NAME),
    author='PyViz',
    description=DESCRIPTION,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url='https://{}.pyviz.org/'.format(NAME),
    project_urls={
        'Documentation': 'https://{}.pyviz.org/'.format(NAME),
        'Source Code': 'https://github.com/pyviz/{}'.format(NAME),
        'Bug Tracker': 'https://github.com/pyviz/{}/issues'.format(NAME)
    },
    packages=find_packages(),
    python_requires='>=3',
    install_requires=[
        'pyviz_comms',
        'jupyter_client',
        'ipykernel',
        'nbformat',
        'nbconvert <5.4', # see https://github.com/pyviz/nbsite/issues/84
        'notebook',
        'sphinx',
        'beautifulsoup4',
    ],
    extras_require= {
        'refman':[
            'graphviz',
        ],
        'gallery':[
            'selenium',
            'phantomjs'
        ],
        'tests':[
            'flake8',
            'pytest >=3.9.1',
            'pyct[cmd] >=0.4.5'
        ],
        'examples':[
            'pyct[cmd] >=0.4.5',
            'sphinx_ioam_theme',
            'holoviews',
            'bokeh',
            'pillow',
            'matplotlib',
            'xarray',
            'pandas',
            'numpy',
            # 'plotly'  # gallery demo
        ],
        'build': [
            "setuptools",
            "param >=1.6.1",
            # "pyct[build] >0.5.0",
        ]
    },
    include_package_data=True,
    license='BSD-3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
    ],
    # TODO: will be transferring to nbsite command...
    scripts = glob.glob("scripts/*.py"),
    entry_points={
        'console_scripts': [
            'nbsite = nbsite.__main__:main'
        ]
    },
)

if __name__=="__main__":
    setup(**setup_args)

