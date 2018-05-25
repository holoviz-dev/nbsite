# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

project = 'nbsite'

####
# could put in nbsite.util and all projects could use
from pkg_resources import get_distribution
_pkg = get_distribution(project)
_m = dict([ tuple(a.split(": ")[0:2]) for a in _pkg._get_metadata(_pkg.PKG_INFO) ])
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
