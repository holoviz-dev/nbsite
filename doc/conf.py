# -*- coding: utf-8 -*-


from nbsite.shared_conf import * # noqa

##############################################################
# start of things to edit

project = u'nbsite'
authors = u'nbsite GitHub contributors'
copyright = u'2017 ' + authors

# TODO: rename
ioam_module = 'nbsite'
description = 'something'

# TODO: gah, version
version = '0.0.1'
release = '0.0.1'

html_static_path = ['_static']

html_theme = 'sphinx_ioam_theme'
html_theme_options = {
#    'logo':'images/amazinglogo.png'
#    'favicon':'images/amazingfavicon.ico'
# ...
# ? css
# ? js
}


_NAV =  (
        ('Getting Started', 'getting_started/index'),
)

html_context = {
    'PROJECT': project,
    'DESCRIPTION': description,
    'AUTHOR': authors,
    # will work without this - for canonical (so can ignore when building locally or test deploying)    
    'WEBSITE_SERVER': 'https://ioam.github.io/nbsite',
    'VERSION': version,
    'NAV': _NAV,
    'LINKS': _NAV,
    'SOCIAL': (
        ('Github', '//github.com/ioam/holoviews'),
    ),
    'js_includes': ['custom.js', 'require.js'],
}

# If extensions (or modules to document with autodoc) are in another
# directory, add these directories to sys.path here.
paths = ['.', '..']

# end of things to edit
##############################################################


add_paths(paths)

from nbsite.shared_conf2 import hack
setup, intersphinx_mapping, texinfo_documents, man_pages, latex_documents, htmlhelp_basename, html_static_path, html_title, exclude_patterns = hack(project,ioam_module,authors,description,html_static_path)
