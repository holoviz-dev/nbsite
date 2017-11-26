import holoviews # noqa (API import)
import numpy     # noqa (API import)
import warnings

import matplotlib as mpl
mpl.use('agg')

import holoviews.plotting.mpl

warnings.filterwarnings("ignore")

ip = get_ipython()  # pyflakes:ignore (IPython namespace)
ip.extension_manager.load_extension('holoviews.ipython')

from holoviews.plotting.widgets import NdWidget
from holoviews.plotting.comms import Comm

try:
    import holoviews.plotting.mpl
    holoviews.Store.renderers['matplotlib'].comms['default'] = (Comm, '')
except:
    pass

try:
    import holoviews.plotting.bokeh
    holoviews.Store.renderers['bokeh'].comms['default'] = (Comm, '')
except:
    pass

NdWidget.export_json=True
NdWidget.json_load_path = '/json'
NdWidget.json_save_path = './'

holoviews.plotting.mpl.MPLPlot.fig_alpha = 0

