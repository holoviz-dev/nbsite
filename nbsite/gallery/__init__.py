from .. import __version__ as nbs_version
from .gen import (
    generate_gallery_rst,
    generate_gallery_inlined_rst,
    DEFAULT_GALLERY_CONF,
    DEFAULT_GALLERY_INLINED_CONF,
)

def setup(app):
    """Setup sphinx-gallery sphinx extension"""
    app.add_config_value('nbsite_gallery_conf', DEFAULT_GALLERY_CONF, 'html')
    app.add_config_value('nbsite_gallery_inlined_conf', DEFAULT_GALLERY_INLINED_CONF, 'html')

    app.connect('builder-inited', generate_gallery_rst)
    app.connect('builder-inited', generate_gallery_inlined_rst)
    metadata = {'parallel_read_safe': True,
                'version': nbs_version}
    return metadata
