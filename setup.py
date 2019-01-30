#!/usr/bin/env python
# -*- coding: utf-8 -*-

import os
import sys
import shutil
import glob
from collections import defaultdict
from setuptools import setup, find_packages


########## autover ##########

def embed_version(basepath, ref='v0.2.2'):
    """
    Autover is purely a build time dependency in all cases (conda and
    pip) except for when you use pip's remote git support [git+url] as
    1) you need a dynamically changing version and 2) the environment
    starts off clean with zero dependencies installed.
    This function acts as a fallback to make Version available until
    PEP518 is commonly supported by pip to express build dependencies.
    """
    import io, zipfile, importlib
    try:    from urllib.request import urlopen
    except: from urllib import urlopen
    try:
        url = 'https://github.com/ioam/autover/archive/{ref}.zip'
        response = urlopen(url.format(ref=ref))
        zf = zipfile.ZipFile(io.BytesIO(response.read()))
        ref = ref[1:] if ref.startswith('v') else ref
        embed_version = zf.read('autover-{ref}/autover/version.py'.format(ref=ref))
        with open(os.path.join(basepath, 'version.py'), 'wb') as f:
            f.write(embed_version)
        return importlib.import_module("version")
    except:
        return None

def get_setup_version(reponame):
    """
    Helper to get the current version from either git describe or the
    .version file (if available).
    """
    import json
    basepath = os.path.split(__file__)[0]
    version_file_path = os.path.join(basepath, reponame, '.version')
    try:
        from param import version
    except:
        version = embed_version(basepath)
    if version is not None:
        return version.Version.setup_version(basepath, reponame, archive_commit="$Format:%h$")
    else:
        print("WARNING: param>=1.6.0 unavailable. If you are installing a package, this warning can safely be ignored. If you are creating a package or otherwise operating in a git repository, you should install param>=1.6.0.")
        return json.load(open(version_file_path, 'r'))['version_string']

########## examples ##########

def check_pseudo_package(path):
    """
    Verifies that a fake subpackage path for assets (notebooks, svgs,
    pngs etc) both exists and is populated with files.
    """
    if not os.path.isdir(path):
        raise Exception("Please make sure pseudo-package %s exists." % path)
    else:
        assets = os.listdir(path)
        if len(assets) == 0:
            raise Exception("Please make sure pseudo-package %s is populated." % path)


excludes = ['DS_Store', '.log', 'ipynb_checkpoints']
packages = []
extensions = defaultdict(list)

def walker(top, names):
    """
    Walks a directory and records all packages and file extensions.
    """
    global packages, extensions
    if any(exc in top for exc in excludes):
        return
    package = top[top.rfind('nbsite'):].replace(os.path.sep, '.')
    packages.append(package)
    for name in names:
        ext = '.'.join(name.split('.')[1:])
        ext_str = '*.%s' % ext
        if ext and ext not in excludes and ext_str not in extensions[package]:
            extensions[package].append(ext_str)


def examples(path='nbsite-examples', verbose=False, force=False, root=__file__):
    """
    Copies the notebooks to the supplied path.
    """
    filepath = os.path.abspath(os.path.dirname(root))
    example_dir = os.path.join(filepath, './examples')
    if not os.path.exists(example_dir):
        example_dir = os.path.join(filepath, '../examples')
    if os.path.exists(path):
        if not force:
            print('%s directory already exists, either delete it or set the force flag' % path)
            return
        shutil.rmtree(path)
    ignore = shutil.ignore_patterns('.ipynb_checkpoints', '*.pyc', '*~')
    tree_root = os.path.abspath(example_dir)
    if os.path.isdir(tree_root):
        shutil.copytree(tree_root, path, ignore=ignore, symlinks=True)
    else:
        print('Cannot find %s' % tree_root)



def package_assets(example_path):
    """
    Generates pseudo-packages for the examples directory.
    """
    examples(example_path, force=True, root=__file__)
    for root, dirs, files in os.walk(example_path):
        walker(root, dirs+files)
    setup_args['packages'] += packages
    for p, exts in extensions.items():
        if exts:
            setup_args['package_data'][p] = exts

########## dependencies ##########
install_requires=[
    'pyviz_comms',
    'jupyter_client',
    'ipykernel',
    'nbformat',
    'nbconvert <5.4', # see https://github.com/pyviz/nbsite/issues/84
    'notebook',
    'sphinx',
    'beautifulsoup4',
]
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
    ],
    # until pyproject.toml/equivalent is widely supported (setup_requires
    # doesn't work well with pip)
    'build': [
        'param >=1.6.1',
        'setuptools' # should make this pip now
    ]
}

setup_args = dict(
    name='nbsite',
    version=get_setup_version("nbsite"),
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
    packages=find_packages()+packages,
    package_data={'nbsite': ['.version']},
    include_package_data=True,
    license='BSD-3',
    classifiers=[
        'Development Status :: 3 - Alpha',
        'Programming Language :: Python :: 3',
        'Operating System :: OS Independent',
        'License :: OSI Approved :: BSD License',
    ],
    python_requires='>=3',
    install_requires=install_requires,
    extras_require=extras_require,
    tests_require=extras_require['tests'],
    # TODO: will be transferring to nbsite command...
    scripts = glob.glob("scripts/*.py"),
    entry_points={
        'console_scripts': [
            'nbsite = nbsite.__main__:main'
        ]
    },
)

if __name__=="__main__":
    import os, sys, shutil
    example_path = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                                'nbsite','examples')
    if 'develop' not in sys.argv:
        package_assets(example_path)

    setup(**setup_args)

    if os.path.isdir(example_path):
        shutil.rmtree(example_path)
