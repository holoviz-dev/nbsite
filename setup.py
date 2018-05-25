#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
from setuptools import setup, find_packages

import version

setup_args = dict(
    name='nbsite',
    version=version.get_setup_version('nbsite'),
    author='pyviz contributors',
    description='Build a tested, sphinx-based website from notebooks.',
    license='BSD-3',
    url='https://pyviz.github.io/nbsite/',
    packages=find_packages(),
    python_requires='>=3',
    install_requires=[
        'jupyter_client',
        'ipykernel',
        'nbformat',
        'nbconvert',
        'notebook',
        'graphviz',
        'sphinx <1.7',
        'beautifulsoup4',
        'graphviz',
    ],
    extras_require= {'gallery':[
        'selenium',
        'phantomjs'        
        ],
                     'tests':[
        'flake8'                 
        ]},
    include_package_data=True,    
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
    ],
    scripts = glob.glob("scripts/*.py"),
)

if __name__=="__main__":
    setup(**setup_args)
