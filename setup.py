#!/usr/bin/env python
# -*- coding: utf-8 -*-

from setuptools import setup

import versioneer

setup(
    name='nbsite',
    version=versioneer.get_version(),
    author='nbsite contributors',
    license='BSD-3',
    url='https://github.com/ioam/nbsite',
    description='abc123',
    long_description=read('README.rst'),
    py_modules=['nbsite'],
# TODO
#    install_requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
    ],
    scripts = [
        'scripts/fix_links.py',
        'scripts/gallery.py',
        'scripts/generate_modules.py',
        'scripts/nbpagebuild.py'
    ]
)
