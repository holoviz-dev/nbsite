---
jupytext:
  text_representation:
    extension: .md
    format_name: myst
    format_version: 0.13
    jupytext_version: 1.16.0
kernelspec:
  display_name: Python 3 (ipykernel)
  language: python
  name: python3
---

# Jupytext

This Markdown file can be opened as a Notebook in JupyterLab with Jupytext installed. New code cells are created with the `code-cell` directive.

## HoloViews

```{code-cell} ipython3
print('code-cells are turned into code-blocks')
```

```{code-cell} ipython3
:pyodide: null

print('pyodide code-cell are turned into code-blocks and parsed with the PyodideCodeBlock directive')
```

```{code-cell} ipython3
:pyodide: null

import holoviews as hv
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({'x': [0, 10, 20], 'y': [5, 1, 20]})

hv.Curve(df, kdims='x', vdims='y')
```

TODO: Matplotlib + Plotly

## hvPlot

```{code-cell} ipython3
:pyodide: null

import hvplot.pandas  # noqa

df.hvplot.scatter(x='x', y='y')
```

TODO: Matplotlib + Plotly


## Panel

```{code-cell} ipython3
:pyodide: null

import panel as pn

pn.widgets.IntInput()
```
