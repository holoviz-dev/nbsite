import warnings

warnings.filterwarnings("ignore")

try:
    import matplotlib as mpl
    mpl.use('agg')
except ModuleNotFoundError:
    pass

try:
    import holoviews.plotting.bokeh  # noqa
except Exception:
    pass

try:
    import holoviews.plotting.mpl as hmpl
    hmpl.MPLPlot.fig_alpha = 0
except Exception:
    pass
