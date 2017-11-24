# -*- coding: utf-8 -*-

from nbsite.shared_conf import extensions, inheritance_graph_attrs,\
    default_edge_attrs, source_suffix, master_doc, pygments_style,\
    exclude_patterns, html_static_path, setup

project = u'Project'
authors = u'Project GitHub contributors'
copyright = u'2017 ' + authors

description = 'Stop plotting your data - annotate your data and let it visualize itself.'

# TODO: gah, version
version = '0.0.1'
release = '0.0.1'

html_static_path += ['_static']
html_theme = 'sphinx_ioam_theme'
# logo file etc should be in html_static_path, e.g. _static
html_theme_options = {
#    'logo':'amazinglogo.png'
#    'favicon':'amazingfavicon.ico'
# ...
# ? css
# ? js
}

_NAV =  (
    ('Getting Started', 'getting_started/index'),
    ('User Guide', 'user_guide/index'),
    ('Gallery', 'gallery/index'),
    ('API', 'Reference_Manual/index'),
    ('FAQ', 'FAQ'),
    ('About', 'about')
)

html_context = {
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    # will work without this - for canonical (so can ignore when building locally or test deploying)    
    'WEBSITE_SERVER': 'https://ceball.github.io',
    'VERSION': version,
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Gitter', '//gitter.im/ioam/holoviews'),
        ('Twitter', '//twitter.com/holoviews'),
        ('Github', '//github.com/ioam/holoviews'),
    ),
    'js_includes': ['custom.js', 'require.js'],
}

