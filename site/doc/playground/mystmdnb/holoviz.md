---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  name: python3
tags:
  - nb-interactivity-warning
---

# HoloViz outputs

Demonstrate that HoloViz specific outputs (HoloViews, Panel) are handled correctly.

## HoloViews

```{code-cell} ipython3
import holoviews as hv
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({'x': [0, 10, 20], 'y': [5, 1, 9]})

hv.Curve(df, kdims='x', vdims='y')
```

TODO: Matplotlib + Plotly

## hvPlot

```{code-cell} ipython3
import hvplot.pandas  # noqa

df.hvplot.scatter(x='x', y='y')
```

TODO: Matplotlib + Plotly


## Panel

```{code-cell} ipython3
import panel as pn

pn.widgets.IntInput()
```
