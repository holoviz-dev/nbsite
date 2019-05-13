# -*- coding: utf-8 -*-
# flake8: noqa (hacky way of sharing config, etc...)

from nbsite.shared_conf import *

###################################################
# edit things below as appropriate for your project

project = u'Project'
authors = u'Authors for html meta author'
copyright = u'2019 ' + authors
description = u'Short description for html meta description.'
site = u'website where this will be served'
version = release = '0.0.1'

html_static_path += ['_static']
# html_theme =   # choose a theme
html_theme_options = {}  # fill out theme options as desired

_NAV =  (
    ('Getting Started', 'getting_started/index'),
    ('User Guide', 'user_guide/index'),
    ('Gallery', 'gallery/index'),
    ('API', 'Reference_Manual/index'),
    ('FAQ', 'FAQ'),
    ('About', 'about')
)

html_context.update({
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    # will work without this - for canonical (so can ignore when building locally or test deploying)
    'WEBSITE_SERVER': site,
    'VERSION': version,
    'NAV': _NAV,
    # by default, footer links are same as those in header
    'LINKS': _NAV,
    'SOCIAL': (
        ('Gitter', 'https://gitter.im/'),
        ('Twitter', 'https://twitter.com/'),
        ('Github', 'https://github.com/'),
    )
})
