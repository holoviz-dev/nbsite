# -*- coding: utf-8 -*-

import sys
import os

def add_paths(paths):
    for path in paths:
        abs_path = os.path.abspath( path)
        sys.path.insert(0, abs_path)
        if "PYTHONPATH" not in os.environ:
            # PYTHONPATH needs to be set for runipy
            os.environ["PYTHONPATH"] = abs_path
        else:
            os.environ["PYTHONPATH"] += ':' + abs_path

extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.intersphinx',
    'sphinx.ext.coverage',
    'sphinx.ext.mathjax',
    'sphinx.ext.ifconfig',
    'sphinx.ext.viewcode',
    'sphinx.ext.inheritance_diagram'
]

inheritance_graph_attrs = dict(rankdir="LR", size='"12.0, 12.0"', fontsize=18)

default_edge_attrs = {
        'arrowsize': 1.0,
        'style': '"setlinewidth(0.5)"',
    }

source_suffix = '.rst'
master_doc = 'index'
pygments_style = 'sphinx'
#html_static_path = ['builder/_shared_static']
