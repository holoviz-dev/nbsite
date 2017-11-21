***
FAQ
***

Questions we have been asked by users, plus potential pitfalls we hope
to help users avoid:


Can I use HoloViews without IPython/Jupyter?
============================================

Yes! The IPython/Jupyter notebook support makes a lot of tasks easier,
and helps keep your data objects separate from the customization
options, but everything available in IPython can also be done directly
from Python.  For instance, since HoloViews 1.3.0 you can render an
object directly to disk, with custom options, like this:

.. code:: python

  import holoviews as hv
  renderer = hv.renderer('matplotlib').instance(fig='svg', holomap='gif')
  renderer.save(my_object, 'example_I', style=dict(Image={'cmap':'jet'}))

This process is described in detail in the `Customizing Plots
<user_guide/Customizing_Plots.html>`_ user guide.  Of course,
notebook-specific functionality like capturing the data in notebook
cells or saving cleared notebooks is only for IPython/Jupyter.

How should I use HoloViews as a short qualified import?
=======================================================

We recommend importing HoloViews using ``import holoviews as hv``.

Why does my output look different from what is shown on the website?
====================================================================

HoloViews is organized as data structures that have corresponding
plotting code implemented in different plotting-library backends, and
each library will have differences in behavior.  Moreover, the same
library can give different results depending on its own internal
options and versions.  For instance, Matplotlib supports a variety of
internal plotting backends, and these can have inconsistent
output. HoloViews will not switch Matplotlib backends for you, but
when using Matplotlib we strongly recommend selecting the 'agg'
backend for consistency:

.. code:: python

  from matplotlib import pyplot
  pyplot.switch_backend('agg')

You can generally set options explicitly to make the output more
consistent across HoloViews backends, but in general HoloViews tries
to use each backend's defaults where possible.

How do I index into my object?
==============================

In any Python session, you can look at ``print(obj)``. For an
explanation of how this information helps you index into your object,
see our `Composing Elements <user_guides/Composing_Elements.html>`_
user guide.


How do I find out the options for customizing the appearance of my object?
==========================================================================

If you are in the IPython/Jupyter Notebook you can use the cell magic
``%%output info=True`` at the top of your code cell. This will present
the available style and plotting options for that object.

The same information is also available in any Python session using
``hv.help(obj)``. For more information on customizing the display of
an object, see our `Customizing Plots
<user_guides/Customizing_Plots.html>`_ user guide.
