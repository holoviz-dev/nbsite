# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = 'nbsite'

####
# could put in nbsite.util and all projects could use...and...surely there's a simpler way?
from pkg_resources import get_distribution
from email import message_from_string
_pkg = get_distribution(project)
_m = {m[0]:m[1] for m in message_from_string(_pkg.get_metadata(_pkg.PKG_INFO)).items()}
####

authors = _m["Author"]
copyright = authors
description = _m['Summary']

import nbsite
version = release = nbsite.__version__

html_static_path += ['_static']
html_theme = 'sphinx_ioam_theme'
html_theme_options = {
    'custom_css': 'nbsitesite.css',
    'logo': 'nbsite-logo.png',
    'favicon': 'favicon.ico'
}

_NAV = ()

html_context.update({
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    'WEBSITE_SERVER': _m['Home-page'],
    'VERSION': version,
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Github', '//github.com/pyviz/nbsite'),
    )
})
