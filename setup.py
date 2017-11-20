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
        'scripts/nbsite_fix_links.py',
        'scripts/nbsite_gallery.py',
        'scripts/nbsite_generate_modules.py',
        'scripts/nbsite_nbpagebuild.py'
    ]
)
