#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob, pathlib
from setuptools import setup

import versioneer

_tmplate_files = [pathlib.Path(x) for x in glob.glob("nbsite/tmplate/*.*") + glob.glob("nbsite/tmplate/*/*.*")]

setup_args = dict(
    name='nbsite',
    version=versioneer.get_version(),
    author='pyviz contributors',
    description='Build a tested, sphinx-based website from notebooks.',
    license='BSD-3',
    url='https://ioam.github.io/nbsite/',
    packages=['nbsite'],
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
        'selenium',
        'phantomjs'
    ],
    package_data={'nbsite': [x.relative_to(x.parts[0]) for x in _tmplate_files]+\
                            ['_shared_static/*.*']
    },
    include_package_data=True,    
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

if __name__=="__main__":
    setup(**setup_args)
