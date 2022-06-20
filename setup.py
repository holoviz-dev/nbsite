#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob
from setuptools import setup, find_packages

import pyct.build

NAME = 'nbsite'
DESCRIPTION = 'Build a tested, sphinx-based website from notebooks.'

# duplicated from pyct.build.get_setup_version until pyct[build] >0.4.6 lands
def get_setup_version(root, reponame):
    """
    Helper to get the current version from either git describe or the
    .version file (if available) - allows for param to not be available.
    Normally used in setup.py as follows:
    >>> from pyct.build import get_setup_version
    >>> version = get_setup_version(__file__, reponame)  # noqa
    """
    import os
    import json

    filepath = os.path.abspath(os.path.dirname(root))
    version_file_path = os.path.join(filepath, reponame, '.version')
    try:
        from param import version
    except:
        version = None
    if version is not None:
        return version.Version.setup_version(filepath, reponame, archive_commit="$Format:%h$")
    else:
        print("WARNING: param>=1.6.0 unavailable. If you are installing a package, this warning can safely be ignored. If you are creating a package or otherwise operating in a git repository, you should install param>=1.6.0.")
        return json.load(open(version_file_path, 'r'))['version_string']

setup_args = dict(
    name=NAME,
    # version=pyct.build.get_setup_version(__file__, NAME),
    version=get_setup_version(__file__, NAME),
    description=DESCRIPTION,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author='PyViz developers',
    author_email='developers@pyviz.org',
    maintainer='PyViz developers',
    maintainer_email='developers@pyviz.org',
    url='https://{}.pyviz.org/'.format(NAME),
    project_urls={
        'Documentation': 'https://{}.pyviz.org/'.format(NAME),
        'Source Code': 'https://github.com/pyviz/{}'.format(NAME),
        'Bug Tracker': 'https://github.com/pyviz/{}/issues'.format(NAME)
    },
    packages=find_packages(),
    python_requires='>=3',
    install_requires=[
        'param >=1.7.0',
        'pyct >=0.4.4',
        'pyviz_comms',
        'ipykernel',
        'nbformat',
        'nbconvert <6.0',
        'jupyter_client <6.2',
        'myst-nb',
        'notebook',
        'sphinx',
        'beautifulsoup4',
        'jinja2 <3.1',
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
            'pyct[cmd]',
        ],
        'examples':[
            'pyct[cmd] >=0.4.5',
            'sphinx_holoviz_theme',
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
            "pyct >=0.4.4",
        ]
    },
    include_package_data=True,
    license='BSD-3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
        'Intended Audience :: Developers',
        'Natural Language :: English',
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
    # (i.e. all lines except setup()), moving it to pyct.build.setup

    import os, sys, shutil

    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                NAME,'examples')
    if 'develop' not in sys.argv:
        pyct.build.examples(example_path, __file__, force=True)

    setup(**setup_args)

    if os.path.isdir(example_path):
        shutil.rmtree(example_path)
