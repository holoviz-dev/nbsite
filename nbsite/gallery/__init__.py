import os

from .. import __version__ as nbs_version
from .gen import generate_gallery_rst, DEFAULT_GALLERY_CONF

def setup(app):
    """Setup sphinx-gallery sphinx extension"""
    app.add_config_value('nbsite_gallery_conf', DEFAULT_GALLERY_CONF, 'html')

    # Sphinx < 1.6 calls it `_extensions`, >= 1.6 is `extensions`.
    extensions_attr = '_extensions' if hasattr(app, '_extensions') else 'extensions'

    app.connect('builder-inited', generate_gallery_rst)
    metadata = {'parallel_read_safe': True,
                'version': nbs_version}
    return metadata
