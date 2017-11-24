# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = u'nbsite'
authors = u'nbsite GitHub contributors'
copyright = u'2017 ' + authors
description = 'something'

import nbsite
version = release = nbsite.__version__

html_static_path += ['_static']
html_theme = 'sphinx_ioam_theme'
html_theme_options = {}

_NAV = ()

html_context = {
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    'WEBSITE_SERVER': 'https://ioam.github.io/nbsite',
    'VERSION': version,
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Github', '//github.com/ioam/nbsite'),
    ),
    'js_includes': ['custom.js', 'require.js'],
}

