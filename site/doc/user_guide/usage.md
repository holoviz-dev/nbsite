# Usage

## Prerequisites

1. You want a 'static', fairly self contained site (i.e. just an ordinary web server is required - you can build and serve locally, or copy the build directory to a remote server).

2. You have one or more sets of notebooks (e.g. `notebooks/`, or `examples/getting_started` + `examples/user_guide` + `examples/gallery`). Note: current expectation is for there to be no title in the notebook itself; instead, the title will be taken from filename. E.g. `1_The_Filename.ipynb` will result in a title of `1 The Filename`. If there is a title in the notebook, then the `offset` flag can be used to remove the first cell before rendering. Notebooks should use level 2 headings as their highest heading level (level 1 will used for the title). However, all of this may change - see [issue 18](https://github.com/holoviz-dev/nbsite/issues/18).

3. The packages used by the notebooks are already installed in the environment into which you will install nbsite.

4. (optional, for API docs) Any packages for which you want to generate API docs are also installed (which could be via e.g. `pip install -e /path/to/pkg`).

5. Currently, you need to have holoviews available in your environment. Other packages (bokeh, matplotlib, plotly) can be used for visualization in addition to holoviews, but if you don't have holoviews in the environment, you will at least need to override `nbbuild_ipython_startup` in `nbbuild.py`, setting it to e.g. `""`.

## Installation

`conda install -c pyviz nbsite` or `pip install nbsite` (note: certain operations may require extra dependencies; for now, see setup.py to learn what those are)

## One time setup

You can skip and/or modify various steps below depending on what you already have. If you do skip these steps you will need to at least create a doc dir with a conf.py in it. See nbsite/templates/basic for an example.

1. Create a set of basic pages: `nbsite init` (will not overwrite existing files). Use the `--theme` option to specify if you want the holoviz setup.

2. Edit conf.py as appropriate for your project.

3. Edit doc/index.rst toctree to match pages in conf.py

4. Commit any pages that you have edited : `git commit -m "something" doc/FAQ.rst doc.about.rst doc/conf.py doc/index.rst doc/latest_news.html ...` (etc)

## Building the site

0. `export ORG=yourorg`, `export PROJECT=yourproject` (or just replace as appropriate in commands below)

1. Generate rst containers for notebooks (assuming they are in `../examples`: `nbsite generate-rst --org ${ORG} --project ${PROJECT} --examples ../examples`)

2. *(optional, if you want gallery)* See [gallery docs](gallery)

3. Make site: `nbsite build`

4. View the result in a browser at localhost:8000: `cd builtdocs && python -m http.server`

## Re-building/updating the site

### rst pages

* Added, removed, or edited an rst page? Update any toc as necessary (e.g. removing an entry), then re-run step 5 above.

### Notebooks

* Removed a notebook? Delete the corresponding rst file.

* Edited a notebook? Re-run step 3 above. You need to manually remove the evaluated notebook from `doc` or use `--overwrite` to have the notebook re-run and turned into html.

* Added a new notebook? Re-run step 1 then proceed as for 'edited' above.

## Customizing Style

For most of the sites that have been generated so far, we used the `sphinx_holoviz_theme`. [PyViz](https://pyviz.org) is the exception and uses the Alabaster theme.


### HoloViz

```{note}
`sphinx_holoviz_theme` is no longer use in favor of the PyData Sphinx Theme.
TODO: Update this to explain how to configure the PyData Sphinx Theme.
```

```{note}
To use the holoviz theme: pip/conda install sphinx_holoviz_theme and set `html_theme` to `sphinx_holoviz_theme`. To control the look and feel, change `html_theme_options` in conf.py:

* `logo` and `favicon`: provide paths relative to `html_static_path` (`doc/_static` by default)
* `primary_color`, `primary_color_dark` and `secondary_color`: control the colors that the website uses for header, nav, links... These can be css named colors, or hex colors.
* `second_nav`: Boolean indicating whether to use a second nav bar.
* `custom_css`: path relative to `html_static_path` overriding styles. Styles come first from the theme's `main.css_t`, which is populated with the colors options, extended/overridden by nbsite's own css `nbsite/_shared_static/nbsite.css`, and then extended/overridden by your site's own css.

**NOTE:** Only use the custom_css to overwrite small pieces of the css not to make general improvements. If you have general improvements, please open a PR on the [theme repo](https://github.com/holoviz-dev/sphinx_holoviz_theme).
```

## Customizing running of IPython notebooks

In conf.py, you can set options to control notebook execution:

* `nbbuild_cell_timeout`: timeout per cell (seconds), e.g. `100`
* `nbbuild_ipython_startup`: code (as string) to execute before running the first cell of each notebook. Defaults to [nbsite's ipython startup code](https://github.com/holoviz-dev/nbsite/blob/main/nbsite/ipystartup.py). E.g. `"module.special_swith=False"`.
* `nbbuild_patterns_to_take_along`: list of glob patterns to match files that should be copied alongside a notebook. E.g. holoviews is configured to save data in external json files to improve page loading times, so this defaults to `["*.json"]`.
