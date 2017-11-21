# -*- coding: utf-8 -*-

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
