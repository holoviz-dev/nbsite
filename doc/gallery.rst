Gallery
_______

The nbsite gallery is a Sphinx extension to build a gallery from
directory of notebook examples containing HoloViews plots. The
extension creates thumbnails from Python scripts or Jupyter notebooks
examples, builds a gallery index page and individual pages for each of
the examples in the gallery. The ``nbsite.gallery`` can be activated
like any other sphinx extension:

.. _activating_gallery:

Activating the extension
========================

To enable the extension add it to the list of extensions in
``conf.py``::

    extensions += ['nbsite.gallery']

.. _configuring_gallery:

Configuring the extension
=========================

The nbsite.gallery is primarily configured via the conf.py file by
defining a ``nbsite_gallery_conf`` dictionary variable, offering the
following options:

- ``backends`` (:ref:`gallery_backends`)
- ``default_extensions`` (:ref:`default_extensions`)
- ``enable_download`` (:ref:`thumbnail_download`)
- ``examples_dir`` (:ref:`directory_structure`)
- ``galleries`` (:ref:`directory_structure`)
- ``github_org`` (:ref:`github_config`)
- ``github_project`` (:ref:`github_config`)
- ``skip_execute`` (:ref:`section_structure`)
- ``thumbnail_url`` (:ref:`thumbnail_download`)
- ``within_subsection_order`` (:ref:`section_structure`)

A sample configuration might look something like this::

    nbsite_gallery_conf = {
      'backends': ['bokeh', 'matplotlib'],
	  'default_extensions': ['*.ipynb', '*.py'],
	  'enable_download': True,
      'examples_dir': os.path.join('..', 'examples'),
      'galleries': {
        'gallery': {'title': 'Gallery'}
      },
      'github_org': 'pyviz',
      'github_project': 'geoviews',
	  'thumbnail_url': 'https://assets.holoviews.org/thumbnails',
      'within_subsection_order': lambda key: key
    }

.. _default_extensions:

File extension
**************

The ``nbsite.gallery`` can handle two different file types:

* ``*.py`` files containing a Python script
* ``*.ipynb`` files containing a Jupyter notebook

The ``default_extensions`` variable defaults to include both but may
be narrowed down to a single file type.

.. _directory_structure:

Directory structure
*******************

The most important variables when configuring the gallery are the
``examples_dir`` and ``galleries`` keys, which define the location and
structure of the galleries. The ``examples_dir`` variable should
define the location of the examples directory relative to the conf.py
file. By default it assumes that relative to the project root the doc
and examples directories are in ``./doc`` and ``./examples``
respectively.

The ``galleries`` config variable should be specified as a nested
dictionary defining one or more galleries to build. To illustrate this
let us look at a sample ``galleries`` configuration::

    'galleries': {
      'gallery': {
        'backends': [],
        'extensions': ['*.ipynb', '*.py'],
        'intro': 'Sample intro',
        'title': 'A sample gallery title',
        'sections': [],
       }
     }

Combined with ``examples_dir`` variable this declares that it should
look for the examples in ``./examples/gallery`` directory. Beyond that
a number of different nesting structures are possible depending on the
defined ``backends`` and ``sections``. Defining sections declares that
the examples are further nested into subdirectories, while declaring
``backends`` either at the top level or the in the ``galleries``
config declares that there are multiple plotting backends to toggle
between. Depending on what is declared the following directory
structure are therefore valid::

    ./examples_dir/gallery_name/section/backend/example.ipynb
    ./examples_dir/gallery_name/section/example.ipynb
    ./examples_dir/gallery_name/backend/example.ipynb
    ./examples_dir/gallery_name/example.ipynb

Note that if there are multiple ``backends`` they must be declared but
the ``sections`` will be discovered automatically if not defined.

.. _section_structure:

Section structure
#################

A section may either be declared as a string or a dictionary which
allows further customization on a per-section basis. If the section is
declared as a string it is assumed it matches sections path and will
be upgraded to title case to add a section header. The dictionary
structure should look like this::

    {'backends': ['bokeh'], 'path': 'section_a', 'skip': True,
	 'title': 'Section A', 'within_subsection_order': lambda key: key}

The most important parts of the declaration provide the ``path`` and
``title`` of the subsection. The ``skip`` key declares whether the
examples in the subsection should actually be executed, which is
sometimes not practical, e.g. for bokeh apps. Alternatively the
examples which should not be executed can also be explicitly declared
using the global ``skip_execute`` config variable.

The actual ordering of the examples in each subsection is defined by
the global or section specific ``within_subsection_order`` config
variable, which should define a key function which defines the sort
order.

.. _gallery_backends:

Gallery backends
****************

The ``backends`` feature in ``nbsite.gallery`` is built around the
capability of HoloViews to output plots using multiple plotting
backends. A gallery which declares multiple backends will have a set
of toggle buttons added at the top which will allow choosing between
the different backends.

.. _thumbnail_download:

Thumbnail downloads
*******************

In some cases it isn't practical to automatically generate a thumbnail
for a plot, particularly if it demonstrates some interactive
feature. For such cases ``nbsite.gallery`` offers the option to fetch
the thumbnail from a remote URL which should match the directory
structure of the ``examples_dir``, which may be defined under the
``thumbnail_url`` config variable, e.g. for the holoviews thumbnails
are stored under ``https://assets.holoviews.org/thumbnails``. To
toggle this behavior on and off you can set the ``enable_downloads``
config variable.

.. _github_config:

Github Configuration
********************

Each example links back to the location of the script or notebook it
was built from, in order to correctly determine these links the
``github_org`` and ``github_project`` must be defined, declaring the
GitHub organization and repository respectively.
