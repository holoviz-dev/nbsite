#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
from setuptools import setup, find_packages

import _pyctbuild

setup_args = dict(
    name='nbsite',
    version=_pyctbuild.get_setup_version2(),
    author='PyViz',
    description='Build a tested, sphinx-based website from notebooks.',
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    url='https://nbsite.pyviz.org/',
    project_urls={
        'Documentation': 'https://nbsite.pyviz.org/',
        'Source Code': 'https://github.com/pyviz/nbsite',
        'Bug Tracker': 'https://github.com/pyviz/nbsite/issues'        
    },
    packages=find_packages(),
    python_requires='>=3',
    install_requires=[
        'pyviz_comms',
        'jupyter_client',
        'ipykernel',
        'nbformat',
        'nbconvert',
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
            'pytest'
        ],
        'examples':[
            'pyct',
            'sphinx_ioam_theme',
            'holoviews',
            'bokeh',
            'pillow',
            'matplotlib',
            'xarray',
            'pandas',
            'numpy',
# gallery demo            
#            'plotly'            
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

    # TODO: hope to eliminate the examples handling from here too
    # (i.e. all lines except setup()), moving it to pyctbuild
    import os, sys, shutil
    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'nbsite','examples')
    if 'develop' not in sys.argv:
        import _pyctbuild
        _pyctbuild.examples(example_path, __file__, force=True)
    
    setup(**setup_args)

    if os.path.isdir(example_path):
        shutil.rmtree(example_path)
