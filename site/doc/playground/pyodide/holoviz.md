# HoloViz outputs

## HoloViews

```{pyodide}
import holoviews as hv
import pandas as pd

hv.extension('bokeh')

df = pd.DataFrame({'x': [0, 10, 20], 'y': [5, 1, 9]})

hv.Curve(df, kdims='x', vdims='y')
```

TODO: Matplotlib + Plotly

## hvPlot

```{pyodide}
import hvplot.pandas  # noqa

df.hvplot.scatter(x='x', y='y')
```

TODO: Matplotlib + Plotly


## Panel

```{pyodide}
import panel as pn

pn.widgets.IntInput()
```
