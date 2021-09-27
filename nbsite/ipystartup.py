import warnings
warnings.filterwarnings("ignore")

import matplotlib as mpl
mpl.use('agg')

try:
    import holoviews.plotting.bokeh
except:
    pass

try:
    import holoviews.plotting.mpl as hmpl
    hmpl.MPLPlot.fig_alpha = 0
except:
    pass
