"""
validate_versioned extension validates the configuration of versioned sites.
"""


from sphinx.util import logging

from .. import __version__ as nbs_version

logger = logging.getLogger(__name__)

def check_for_switcher_key(app):
    theme_opts = app.config.html_theme_options
    if (
        isinstance(theme_opts, dict)
        and 'switcher' in theme_opts
        and not app.config.html_baseurl
    ):
        logger.warning(
            "html_baseurl must be set when the site is versioned. For example: "
            "`html_baseurl = 'https://hvplot.holoviz.org/en/docs/latest/'`"
        )

def setup(app):
    app.connect('builder-inited', check_for_switcher_key)
    return {
        "version": nbs_version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
