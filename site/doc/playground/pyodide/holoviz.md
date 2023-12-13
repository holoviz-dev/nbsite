# HoloViz outputs

## HoloViews

```{code-block} python
:pyodide: null

import holoviews as hv
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({'x': [0, 10, 20], 'y': [5, 1, 9]})

hv.Curve(df, kdims='x', vdims='y')
```

TODO: Matplotlib + Plotly

## hvPlot

```{code-block} python
:pyodide: null

import hvplot.pandas  # noqa

df.hvplot.scatter(x='x', y='y')
```

TODO: Matplotlib + Plotly


## Panel

```{code-block} python
:pyodide: null

import panel as pn

pn.widgets.IntInput()
```
