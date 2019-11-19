******
nbsite
******

**Build a tested, sphinx-based website from notebooks**

Nbsite lets you build a website from a set of notebooks plus a minimal
amount of config. Sites built with nbsite include
`pyviz.org <https://pyviz.org/>`_,
`datashader.org <http://datashader.org/>`_, and `hvplot.pyviz.org <https://hvplot.pyviz.org/>`_.

The idea behind nbsite is that notebooks can simultaneously be
documentation (things you want to tell people about), examples (a
starting point for people to run and use themselves), and test cases.

To get started using nbsite, please see `Getting Started
<getting_started.html>`_. However, please note that this is a pre-release
version of nbsite. If you use nbsite, you may subsequently have to
change your config on upgrading to a newer version of nbsite. You will
likely encounter limitations and
problems. However, please file issues or ask questions on `GitHub
<https://github.com/pyviz/nbsite/issues>`_.

Examples
========

Many of the websites in the pyviz ecosystem are built using nbsite.
These include:

  .. raw:: html

    <div id="iframe-container" style="height: 800px; width: 2000px;">
      <iframe src="https://holoviews.org" height="500px" width="900px"></iframe>
      <iframe src="https://pyviz.org" height="500px" width="900px"></iframe>
      <iframe src="https://holoviz.org" height="500px" width="900px"></iframe>
      <iframe src="https://datashader.org" height="500px" width="900px"></iframe>
      <iframe src="https://hvplot.pyviz.org" height="500px" width="900px"></iframe>
      <iframe src="https://panel.pyviz.org" height="500px" width="900px"></iframe>
      <iframe src="https://colorcet.pyviz.org" height="500px" width="900px"></iframe>
      <iframe src="https://examples.pyviz.org" height="500px" width="900px"></iframe>
    </div>

.. _when_to_use:

When to use nbsite
==================

Nbsite is recommended for users who want to generate a static site from
content in notebooks. It is especially useful if those notebooks contain
bokeh plots.

.. _when_not_to_use:

When not to use nbsite
======================

Nbsite is not recommended if you don't mind writing rst, don't have bokeh
plots or are primarily interested in live notebooks. There are other projects
to consider instead if that is your case:

  * static site generators with support for notebooks: nikola,
    pelican, jupytersite, hugo, (whatever
    `seaborn <https://seaborn.pydata.org/tutorial/color_palettes.html>`_ uses),
    (whatever scikit-learn uses), (wahtever scikit-image uses), ...

  * notebook hosting plus viewing: github+nbviewer
    (`example <https://nbviewer.jupyter.org/github/pyviz/pyviz/blob/master/notebooks/00-welcome.ipynb>`_),
    anaconda.org
    (`example <https://anaconda.org/cball/ioam-paramnb-index/notebook>`_);
    ...

  * live notebook hosting: mybinder
    (`example <https://mybinder.org/v2/gh/pyviz/pyviz/master?filepath=notebooks%2F12-parameters-and-widgets.ipynb>`_);
    ...?

.. _examples:

.. toctree::
    :hidden:
    :maxdepth: 2

    Introduction <self>
    Usage
    Gallery <gallery>
    Development
    FAQ
