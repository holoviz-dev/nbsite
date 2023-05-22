from .. import __version__ as nbs_version
from .gen import DEFAULT_GALLERY_CONF, generate_gallery_rst


def setup(app):
    """Setup sphinx-gallery sphinx extension"""
    app.add_config_value('nbsite_gallery_conf', DEFAULT_GALLERY_CONF, 'html')

    app.connect('builder-inited', generate_gallery_rst)
    metadata = {'parallel_read_safe': True,
                'version': nbs_version}
    return metadata
