# Gallery

The NBSite gallery is a Sphinx extension to build a gallery from
directory of notebook examples containing HoloViews plots. The
extension creates thumbnails from Python scripts or Jupyter notebooks
examples, builds a gallery index page and individual pages for each of
the examples in the gallery. The `nbsite.gallery` can be activated
like any other sphinx extension:

(activating-gallery)=

## Activating the extension

To enable the extension add it to the list of extensions in
`conf.py`:

```
extensions += ['nbsite.gallery']
```

(configuring-gallery)=

## Configuring the extension

The `nbsite.gallery` is primarily configured via the conf.py file by
defining a `nbsite_gallery_conf` dictionary variable, offering the
following options:

- `backends`
- `default_extensions`
- `download_as`
- `enable_download`
- `examples_dir`
- `galleries`
- `github_org`
- `github_project`
- `host`
- `inline`
- `nblink`
- `only_use_existing`
- `skip_execute`
- `orphans`
- `thumbnail_url`
- `within_subsection_order`
- `skip_rst_notebook_directive`
- `titles_from_files`: Card titles are obtained from the notebook file heading (to be used with `skip_rst_notebook_directive=True`).
- `grid_no_columns`: Sphinx Design `columns` value. The number of columns (out of 12) a grid-item will take up. One or four integers (for “xs sm md lg”) between 1 and 12 (or auto to adapt to the content).
- `no_image_thumb`: Display nbsite's logo as a thumbnail is no thumbnail can be found or downloaded.
- `card_title_below`: Card title displayed below the thumbnail as a description.

A sample configuration might look something like this:

```
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
```

(default-extensions)=

### File extension

The `nbsite.gallery` can handle two different file types:

- `*.py` files containing a Python script
- `*.ipynb` files containing a Jupyter notebook

The `default_extensions` variable defaults to include both but may
be narrowed down to a single file type.

(directory-structure)=

### Directory structure

The most important variables when configuring the gallery are the
`examples_dir` and `galleries` keys, which define the location and
structure of the galleries. The `examples_dir` variable should
define the location of the examples directory relative to the conf.py
file. By default it assumes that relative to the project root the doc
and examples directories are in `./doc` and `./examples`
respectively.

The `galleries` config variable should be specified as a nested
dictionary defining one or more galleries to build. To illustrate this
let us look at a sample `galleries` configuration:

```
'galleries': {
  'gallery': {
    'backends': [],
    'extensions': ['*.ipynb', '*.py'],
    'intro': 'Sample intro',
    'title': 'A sample gallery title',
    'sections': [],
   }
 }
```

Combined with `examples_dir` variable this declares that it should
look for the examples in `./examples/gallery` directory. Beyond that
a number of different nesting structures are possible depending on the
defined `backends` and `sections`. Defining sections declares that
the examples are further nested into subdirectories, while declaring
`backends` either at the top level or the in the `galleries`
config declares that there are multiple plotting backends to toggle
between. Depending on what is declared the following directory
structure are therefore valid:

```
./examples_dir/gallery_name/section/backend/example.ipynb
./examples_dir/gallery_name/section/example.ipynb
./examples_dir/gallery_name/backend/example.ipynb
./examples_dir/gallery_name/example.ipynb
```

Note that if there are multiple `backends` they must be declared but
the `sections` will be discovered automatically if not defined.

(section-structure)=

#### Section structure

A section may either be declared as a string or a dictionary which
allows further customization on a per-section basis. If the section is
declared as a string it is assumed it matches sections path and will
be upgraded to title case to add a section header. The dictionary
structure should look like this:

```
{'backends': ['bokeh'], 'path': 'section_a', 'skip': True,
     'title': 'Section A', 'within_subsection_order': lambda key: key}
```

The most important parts of the declaration provide the `path` and
`title` of the subsection. The `skip` key declares whether the
examples in the subsection should actually be executed, which is
sometimes not practical, e.g. for bokeh apps. Alternatively the
examples which should not be executed can also be explicitly declared
using the global `skip_execute` config variable.

The `skip` key can also be used to pass a list of files that should
**not** show up at all on the gallery page. These examples will
not be thumbnailed or executed.

A slight variation on `skip`, the `orphans` key allows the user to
pass a list of files that will be rendered to html without being thumbnailed
and linked from the gallery page. The main usecase for this is when a section
has an index which provides an overview of the section and directs users through
the notebooks in a particular order.

The actual ordering of the examples in each subsection is defined by
the global or section specific `within_subsection_order` config
variable, which should define a key function which defines the sort
order.

(gallery-backends)=

### Gallery backends

The `backends` feature in `nbsite.gallery` is built around the
capability of HoloViews to output plots using multiple plotting
backends. A gallery which declares multiple backends will have a set
of toggle buttons added at the top which will allow choosing between
the different backends.

(gallery-page)=

### Gallery page

To control the look and feel of your gallery landing page, you can
use set the `inline` option to True. This will make the sections render
inline on the landing page increasing the density of content for projects
that have few notebooks per section (for instance: [examples.pyviz.org](https://examples.pyviz.org)).

(thumbnail-download)=

### Thumbnail downloads

In some cases it isn't practical to automatically generate a thumbnail
for a plot, particularly if it demonstrates some interactive
feature. For such cases `nbsite.gallery` offers the option to fetch
the thumbnail from a remote URL which should match the directory
structure of the `examples_dir`, which may be defined under the
`thumbnail_url` config variable, e.g. for the holoviews thumbnails
are stored under `https://assets.holoviews.org/thumbnails`. To
toggle this behavior on and off you can set the `enable_downloads`
config variable.

If you want to be sure never to generate thumbnails, for instance if
the environment won't have the right dependencies, then use the `only_use_existing`
to ensure that the script can only use thumbnails found in the directory
or at `thumbnail_url`.

(asset-download)=

### Asset Download

Each example links back to the location of the script or notebook it
was built from. These download links can be placed at the `top`, `bottom` or
`both` of the notebook using the `nblink` option. By default the download
usses `GitHub` as the `host`, in order to correctly determine these links the
`github_org` and `github_project` must be defined, declaring the
GitHub organization and repository respectively.

To enable direct downloads from the assets directory of the website set `host`
to `assets`. By default the links will point to a particular file. To instead point
the download link to a project archive, set `download_as` to `project`.
