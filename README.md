<img src="https://github.com/holoviz-dev/nbsite/raw/main/site/doc/_static/nbsite-logo.png" height=150><br>

-----------------

# NBSite: Build a tested, sphinx-based website from notebooks

|    |    |
| --- | --- |
| Build Status | [![Build Status](https://github.com/holoviz-dev/nbsite/workflows/tests/badge.svg)](https://github.com/holoviz-dev/nbsite/actions?query=workflow%3Atests)
| Coverage | [![codecov](https://codecov.io/gh/holoviz-dev/nbsite/branch/main/graph/badge.svg)](https://codecov.io/gh/holoviz-dev/nbsite) |
| Latest dev release | [![Github tag](https://img.shields.io/github/tag/holoviz-dev/nbsite.svg?label=tag&colorB=11ccbb)](https://github.com/holoviz-dev/nbsite/tags) [![dev-site](https://img.shields.io/website-up-down-green-red/https/holoviz-dev.github.io/nbsite-dev.svg?label=dev%20website)](https://holoviz-dev.github.io/nbsite-dev/)|
| Latest release | [![Github release](https://img.shields.io/github/release/holoviz-dev/nbsite.svg?label=tag&colorB=11ccbb)](https://github.com/holoviz-dev/nbsite/releases) [![PyPI version](https://img.shields.io/pypi/v/nbsite.svg?colorB=cc77dd)](https://pypi.python.org/pypi/nbsite) [![nbsite version](https://img.shields.io/conda/v/pyviz/nbsite.svg?colorB=4488ff&style=flat)](https://anaconda.org/pyviz/nbsite) [![conda-forge version](https://img.shields.io/conda/v/conda-forge/nbsite.svg?label=conda%7Cconda-forge&colorB=4488ff)](https://anaconda.org/conda-forge/nbsite) [![defaults version](https://img.shields.io/conda/v/anaconda/nbsite.svg?label=conda%7Cdefaults&style=flat&colorB=4488ff)](https://anaconda.org/anaconda/nbsite) |
| Docs | [![gh-pages](https://img.shields.io/github/last-commit/pyviz/nbsite/gh-pages.svg)](https://github.com/pyviz/nbsite/tree/gh-pages) [![site](https://img.shields.io/website-up-down-green-red/https/nbsite.pyviz.org.svg)](https://nbsite.pyviz.org) |

---

**DISCLAIMER**

NBSite is a tool supporting the developers of the [HoloViz](https://holoviz/org) project. As such it is tailored to their use case, workflow, and **breaking changes may occur at any time**. We suggest that before using NBSite you investigate alternatives such as [MyST-NB](https://myst-nb.readthedocs.io) or [nbsphinx](https://nbsphinx.readthedocs.io/). If you select NBSite anyway, we recommend that you pin its version.

---

NBSite lets you build a website from a set of notebooks plus a minimal
amount of config. The idea behind NBSite is that notebooks can simultaneously be documentation (things you want to tell people about), examples (a starting point for people to run and use themselves), and test cases (see nbsmoke).

## Sites built with NBSite

Non exhaustive list of sites built with NBSite (as of November 2022):

- [Panel](https://panel.holoviz.org/)
- [hvPlot](https://hvplot.holoviz.org/)
- [HoloViews](https://holoviews.org/)
- [GeoViews](https://geoviews.org/)
- [Datashader](https://datashader.org/)
- [Lumen](https://lumen.holoviz.org/)
- [Colorcet](https://colorcet.holoviz.org/)
- [Param](https://param.holoviz.org/)
- [HoloViz.org](https://holoviz.org/)
- [examples.pyviz.org](https://examples.pyviz.org/)
- [PyViz.org](https://pyviz.org/)

## About HoloViz

NBSite is part of the HoloViz initiative for making Python-based visualization tools work well together.
See [holoviz.org](https://holoviz.org/) for related packages that you can use with NBSite and
[status.holoviz.org](https://status.holoviz.org/) for the current status of each HoloViz project.
