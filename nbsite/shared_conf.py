# -*- coding: utf-8 -*-

import datetime
import importlib
import inspect
import os
import pathlib as _pathlib
import subprocess
import sys

import nbsite as _nbsite

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
    'sphinx_design',
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.linkcode',
    'sphinx.ext.inheritance_diagram',
    'sphinx_copybutton',
    'sphinxext.rediraffe',
]

# Default theme is the PyData Sphinx Theme
html_theme = "pydata_sphinx_theme"

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

html_context = {}

html_css_files = [
    'nbsite.css',
    'notebook.css',
    'gallery.css',
    'alert.css',
    'dataframe.css',
    'scroller.css'
]

# A single line footer that includes the copyright and the last updated date.
html_theme_options = {
    "footer_start": [
        "copyright-last-updated",
    ],
    # To avoid warning as this is the new default
    # See https://github.com/pydata/pydata-sphinx-theme/issues/1492
    "navigation_with_keys": False,
}

# Default is "**": ["sidebar-nav-bs", "sidebar-ethical-ads"]
# Overriding the index sidebar to include the toctree on the landing page.
# The layout.html template in pydata-sphinx-theme removes the default
# sidebar-nav-bs.html template.
html_sidebars = {
    "index": ["sidebar-nav-bs-alt"],
    "**": ["sidebar-nav-bs-alt"],
}

# To be reused in a conf.py file to define the `copyright` string reused
# by sphinx to populate the footer content:
# copyright_years['start_year'] = '2000'
# copyright = copyright_fmt.format(**copyright_years)
copyright_years = {'current_year': str(datetime.date.today().year)}
copyright_fmt = "{start_year}-{current_year} Holoviz contributors"

# Format of the last updated date in the footer.
html_last_updated_fmt = '%Y-%m-%d'

rediraffe_redirects = {}

suppress_warnings = [
    # Ignore: (WARNING/2) Document headings start at H2, not H1
    "myst.header",
    # Ignores: skipping unknown output mime type: application/vnd.holoviews_exec.v0+json
    "mystnb.unknown_mime_type"
]

GIT_ROOT_CMD = "git rev-parse --show-toplevel"
GITHUB_BASE_URL = "https://github.com/holoviz/"

def get_module_object(modname, fullname):
    """Retrieve the Python object based on its module and fullname."""
    submod = sys.modules.get(modname)
    if submod is None:
        return None
    obj = submod
    for part in fullname.split("."):
        obj = getattr(obj, part, None)
        if obj is None:
            return None
    return obj

def get_source_info(obj):
    """Get the source file and line numbers for a Python object."""
    try:
        fn = inspect.getsourcefile(inspect.unwrap(obj))
        source, lineno = inspect.getsourcelines(obj)
    except (TypeError, OSError):
        return None, None, None
    return fn, source, lineno

def get_repo_dir():
    """Get the root directory of the current Git repository."""
    try:
        output = subprocess.check_output(GIT_ROOT_CMD.split(" ")).strip().decode('utf-8')
        return _pathlib.Path(output).name
    except subprocess.CalledProcessError:
        raise RuntimeError("Unable to determine the repository directory")

def linkcode_resolve(domain, info):
    """Resolve the link to the source code for a given Python object in documentation."""
    if domain != "py":
        return None

    modname = info["module"]
    fullname = info["fullname"]

    obj = get_module_object(modname, fullname)
    if obj is None:
        return None

    fn, source, lineno = get_source_info(obj)
    if not fn:
        return None

    linespec = f"#L{lineno}-L{lineno + len(source) - 1}" if lineno else ""

    package = get_repo_dir()

    ppath = importlib.__import__(package).__file__
    pver = importlib.__import__(package).__version__

    fn = os.path.relpath(fn, start=os.path.dirname(ppath))

    if "+" in pver:
        return f"{GITHUB_BASE_URL}{package}/blob/main/{package}/{fn}{linespec}"
    else:
        return f"{GITHUB_BASE_URL}{package}/blob/v{pver}/{package}/{fn}{linespec}"
