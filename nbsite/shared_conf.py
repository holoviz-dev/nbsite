# -*- coding: utf-8 -*-

import os

from nbsite import nbbuild

def setup(app):
    try:
        from nbsite.paramdoc import param_formatter, param_skip
        app.connect('autodoc-process-docstring', param_formatter)
        app.connect('autodoc-skip-member', param_skip)
    except ImportError:
        print('no param_formatter (no param?)')

    nbbuild.setup(app)
    app.connect("builder-inited", remove_mystnb_static)

def remove_mystnb_static(app):
    # Ensure our myst_nb.css is loaded by removing myst_nb static_path
    # from config
    app.config.html_static_path = [
        p for p in app.config.html_static_path if 'myst_nb' not in p
    ]

extensions = [
    'myst_nb',
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.inheritance_diagram',
]

inheritance_graph_attrs = dict(
    rankdir="LR",
    size='"12.0, 12.0"',
    fontsize=18
)

default_edge_attrs = {
    'arrowsize': 1.0,
    'style': '"setlinewidth(0.5)"',
}

source_suffix = '.rst'

master_doc = 'index'

pygments_style = 'sphinx'

exclude_patterns = ['_build']

html_static_path = [
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '_shared_static'
        )
    )
]

html_context = {
    'js_includes': ['nbsite.js', 'require.js'],
    'css_includes': ['nbsite.css'] 
}
