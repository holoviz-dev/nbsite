# -*- coding: utf-8 -*-

import datetime
import os

import nbsite as _nbsite
import pathlib as _pathlib

from nbsite import nbbuild
from nbsite.util import base_version  # noqa

NBSITE_DIR = _pathlib.Path(_nbsite.__file__).parent


def holoviz_icon_white(cur_file):
    """Return the path as a string of the holoviz white icon SVG."""
    doc_root = _pathlib.Path(cur_file).parent
    shared_static_dir = _pathlib.Path(os.path.relpath(NBSITE_DIR / '_shared_static', start=doc_root))
    icon_path = shared_static_dir / 'holoviz-icon-white.svg'
    return str(icon_path)


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

templates_path = [
    os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            '_shared_templates'
        )
    )
]

html_context = {
    'js_includes': ['nbsite.js', 'require.js'],
    'css_includes': ['nbsite.css'] 
}

# A single line footer that includes the copyright and the last updated date.
html_theme_options = {
    "footer_items": [
        "copyright-last-updated",
    ],
}

# To be reused in a conf.py file to define the `copyright` string reused
# by sphinx to populate the footer content:
# copyright_years['start_year'] = '2000'
# copyright = copyright_fmt.format(**copyright_years)
copyright_years = {'current_year': str(datetime.date.today().year)}
copyright_fmt = "{start_year}-{current_year} Holoviz contributors"

# Format of the last updated date in the footer.
html_last_updated_fmt = '%Y-%m-%d'
