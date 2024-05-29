#!/usr/bin/env python
# -*- coding: utf-8 -*-

import glob

from setuptools import find_packages, setup

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
    import json
    import os

    filepath = os.path.abspath(os.path.dirname(root))
    version_file_path = os.path.join(filepath, reponame, '.version')
    try:
        from param import version
    except Exception:
        version = None
    if version is not None:
        return version.Version.setup_version(filepath, reponame, archive_commit="$Format:%h$")
    print(
        "WARNING: param>=1.6.0 unavailable. If you are installing a package, "
        "this warning can safely be ignored. If you are creating a package or "
        "otherwise operating in a git repository, you should install param>=1.6.0."
    )
    return json.load(open(version_file_path, 'r'))['version_string']

setup_args = dict(
    name=NAME,
    version=get_setup_version(__file__, NAME),
    description=DESCRIPTION,
    long_description=open("README.md").read(),
    long_description_content_type="text/markdown",
    author='HoloViz developers',
    author_email='developers@holoviz.org',
    maintainer='HoloViz developers',
    maintainer_email='developers@holoviz.org',
    url='https://nbsite.holoviz.org',
    project_urls={
        'Documentation': 'https://nbsite.holoviz.org/',
        'Source Code': 'https://github.com/holoviz-dev/nbsite',
        'Bug Tracker': 'https://github.com/holoviz-dev/nbsite/issues'
    },
    packages=find_packages(),
    python_requires='>=3.9',
    install_requires=[
        'param >=1.7.0',
        'pyviz_comms',
        'ipykernel',
        'nbformat',
        'nbconvert',
        'jupyter_client',
        'myst-nb >=1.1',
        'sphinx-design',
        'notebook',
        'sphinx >=7',
        'beautifulsoup4',
        'jinja2',
        'pillow',
        'pydata-sphinx-theme >=0.15,<0.16',
        'myst-parser >=3',
        'sphinx-copybutton',
        'sphinx-design',
        'sphinxext-rediraffe',
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
            'pre-commit',
        ],
        'build': [
            "setuptools",
            "param >=1.6.1",
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
    setup(**setup_args)
