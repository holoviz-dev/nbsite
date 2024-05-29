"""
Analytics extension supporting GoatCounter only.
Should be upstreamed to pydata-sphinx-theme.
"""

from .. import __version__ as nbs_version


def add_analytics(app):
    nbsite_analytics = app.config.nbsite_analytics
    if nbsite_analytics:

        # Process GoatCounter

        # goatcounter_holoviz is specific to HoloViz, remove when moving to PyData Sphinx Theme
        goatcounter_holoviz = nbsite_analytics.get('goatcounter_holoviz', False)
        if goatcounter_holoviz:
            hv_default = dict(
                goatcounter_url='https://holoviz.goatcounter.com/count',
                goatcounter_domain='auto',
            )
            nbsite_analytics = dict(nbsite_analytics, **hv_default)
        goatcounter_url = nbsite_analytics.get('goatcounter_url')
        if goatcounter_url:
            goatcounter_domain = nbsite_analytics.get('goatcounter_domain')
            if goatcounter_domain:
                domain = "location.host" if goatcounter_domain == "auto" else f"{goatcounter_domain!r}"
                # See https://www.goatcounter.com/help/domains
                body = (
                    "\n    window.goatcounter = {\n"
                    "        path: function(p) { return " + domain + " + p }\n"
                    "    }\n"
                )
                app.add_js_file(None, body=body)
        app.add_js_file(
            "js/goatcounter.js",
            **{"loading_method": "async", "data-goatcounter": goatcounter_url}
        )

def setup(app):
    """Setup analytics (goatcounter only!) sphinx extension"""
    # In the Pydata Sphinx Theme the config is going to be in the theme
    app.add_config_value('nbsite_analytics', {}, 'html')
    app.connect('builder-inited', add_analytics)
    return  {'parallel_read_safe': True, 'version': nbs_version}
