# -*- coding: utf-8 -*-

from nbsite.shared_conf import *

NAME = 'nbsite'
DESCRIPTION = 'Build a tested, sphinx-based website from notebooks.'

project = NAME
authors = u'PyViz Developers'
copyright = u'2018-2019 ' + authors
description = DESCRIPTION

import nbsite
version = release = nbsite.__version__

html_static_path += ['_static']
html_theme = 'sphinx_pyviz_theme'
html_theme_options = {
    'custom_css': 'nbsitesite.css',
    'logo': 'nbsite-logo.png',
    'favicon': 'favicon.ico'
}

_NAV = (
    ('Usage', 'usage'),
    ('Gallery', 'gallery'),
    ('About', 'about')
)

html_context.update({
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    'WEBSITE_SERVER': 'http://{}.pyviz.org'.format(NAME),
    'VERSION': version,
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Github', 'https://github.com/pyviz/{}'.format(NAME)),
        ('Gitter', 'https://gitter.im/pyviz/pyviz'),
    )
})
