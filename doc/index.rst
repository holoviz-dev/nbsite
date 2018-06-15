******
nbsite
******

.. raw:: html

   <div style="width: 65%; float:left">

	 
**Build a tested, sphinx-based website from notebooks**

Nbsite lets you build a website from a set of notebooks plus a minimal
amount of config. Sites built with nbsite include
`<http://pyviz.org/>`_ and
`<https://datashader.org/>`_.

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
<https://github.com/pyviz/nbsite/issues>`_

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
  
  * `<https://ioam.github.io/parambokeh/>`_ (parambokeh)

  * `<http://geoviews.org/>`_ (geoviews)
    
  * `<http://datashader.org/`_ (datashader)
    
  * `<http://pyviz.org/>`_ (pyviz)

  * `<https://pyviz.github.io/nbsite/>`_ (nbsite; this project)

  * `<https://bokeh.github.io/colorcet/>`_ (colorcet)
    
  * `<https://ceball.github.io/xarray_filters/>`_ (`xarray_filters
    <https://github.com/ContinuumIO/xarray_filters>`_)

  * `<https://pyviz.github.io/holoplot/>`_ (holoplot)


.. raw:: html
  
   </div>

.. toctree::
    :hidden:
    :maxdepth: 2

    Introduction <self>
    Usage
    Development
    FAQ
