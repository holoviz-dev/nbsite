#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob, pathlib
from setuptools import setup

import versioneer

_tmplate_files = [pathlib.Path(x) for x in glob.glob("nbsite/tmplate/*.*") + glob.glob("nbsite/tmplate/*/*.*")]
print([x.relative_to(x.parts[0]) for x in _tmplate_files])

setup(
    name='nbsite',
    version=versioneer.get_version(),
    author='nbsite contributors',
    license='BSD-3',
    url='https://github.com/ioam/nbsite',
    packages=['nbsite'],
    install_requires=[
        'jupyter_client',
        'ipykernel',
        'nbformat',
        'nbconvert',
        'notebook',
        'graphviz',
        'ipython',
        'sphinx',
        'beautifulsoup4',
        'graphviz'
    ],
    package_data={'nbsite': [x.relative_to(x.parts[0]) for x in _tmplate_files]+\
                            ['_shared_static/*.*']
    },
# TODO
#    install_requires=[],
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
    ],
    scripts = glob.glob("scripts/*.py"),
    zip_safe=False,
    cmdclass=versioneer.get_cmdclass()
)
