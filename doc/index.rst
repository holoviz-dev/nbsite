******
nbsite
******

.. raw:: html

   <div style="width: 65%; float:left">

	 
**Build a tested, sphinx-based website from notebooks**

Nbsite lets you build a website from a set of notebooks plus a minimal
amount of config. Sites built with nbsite include
`<http://pyviz.github.io/pyviz/>`_ and
`<https://bokeh.github.io/datashader-docs/>`_.

The idea behind nbsite is that notebooks can simultaneously be
documentation (things you want to tell people about), examples (a
starting point for people to run and use themselves), and test cases.

To get started using nbsite, please see the `user guide
<Usage.html>`_. However, please note that this is a pre-release
version of nbsite. If you use nbsite, you may subsequently have to
change your config on upgrading to a newer version of nbsite. You will
likely encounter limitations (not all of the above 'idea behind
nbsite' is easily available yet via this project) and
problems. However, please file issues or ask questions on `GitHub
<https://github.com/ioam/nbsite/issues>`_

At some point soon we will describe when you should or should not
consider using nbsite instead of various alternatives, including:

  * static site generators with support for notebooks: nikola,
    pelican, jupytersite, hugo, (whatever
    https://seaborn.pydata.org/tutorial/color_palettes.html uses),
    (whatever scikit-learn uses), (wahtever scikit-image uses), ...

  * notebook hosting plus viewing: github+nbviewer
    (e.g. `<http://nbviewer.jupyter.org/github/pyviz/pyviz/blob/master/notebooks/00-welcome.ipynb>`_),
    anaconda.org
    (e.g. `<https://anaconda.org/cball/ioam-paramnb-index/notebook>`_);
    ...

  * live notebook hosting: mybinder
    (e.g. `<https://mybinder.org/v2/gh/pyviz/pyviz/master?filepath=notebooks%2F12-parameters-and-widgets.ipynb>`_);
    ...?
    
Notes for nbsite developers: `Development <Development.html>`_

Work-in-progress sites built using nbsite (currently present to keep
keep track; will eventually remove):
  
  * `<https://ioam.github.io/parambokeh/>`_ (`parambokeh
    <https://github.com/ioam/parambokeh>`_)

  * `<https://ioam.github.io/geoviews/>`_ (`geoviews
    <https://github.com/ioam/geoviews>`_)
    
  * `<https://bokeh.github.io/datashader-docs/>`_ (`datashader
    <https://github.com/bokeh/datashader/>`_)
    
  * `<https://pyviz.github.io/pyviz/>`_ (`pyviz
    <https://github.com/pyviz/pyviz>`_)

  * `<https://ceball.github.io/>`_ (`tmp demo site
    <https://github.com/ContinuumIO/tmphvdocs/tree/tmphvdocs>`_; note:
    built from scratch, starting from nbsite template)

  * `<https://ioam.github.io/nbsite/>`_ (`nbsite
    <https://github.com/ioam/nbsite>`_; this site)

  * `<https://bokeh.github.io/colorcet/>`_ (`colorcet
    <https://github.com/bokeh/colorcet>`_)
    
  * `<https://ceball.github.io/xarray_filters/>`_ (`xarray_filters
    <https://github.com/ContinuumIO/xarray_filters>`_)

  * `<https://ioam.github.io/paramnb/>`_ (`paramnb
    <https://github.com/ioam/paramnb>`_)



.. raw:: html
  
   </div>

.. toctree::
    :hidden:
    :maxdepth: 2

    Introduction <self>
    Usage
    Development
    FAQ
