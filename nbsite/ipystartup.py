import warnings
warnings.filterwarnings("ignore")

import matplotlib as mpl
mpl.use('agg')

try:
    import holoviews.plotting.widgets as hw
    hw.NdWidget.export_json=True
    hw.NdWidget.json_load_path = './'
    hw.NdWidget.json_save_path = './'
    del hw
except:
    from panel import config
    config.embed = True
    config.embed_json = True
    config.embed_json_prefix = 'json'
    config.embed_load_path = './'
    config.embed_save_path = './'
    del config

import holoviews.plotting.mpl as hmpl
hmpl.MPLPlot.fig_alpha = 0
del hmpl

