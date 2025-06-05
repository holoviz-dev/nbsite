"""
validate_versioned extension validates the configuration of versioned sites.
"""
import itertools
import json
import xml.etree.ElementTree as ET

from pathlib import Path
from urllib.parse import urljoin, urlparse

import requests

from packaging import version
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


def check_for_robots(app):
    theme_opts = app.config.html_theme_options
    if (
        isinstance(theme_opts, dict)
        and 'switcher' not in theme_opts
    ):
        return
    html_baseurl = app.config.html_baseurl
    if not html_baseurl:
        # check_for_switcher_key already handles warning here.
        return
    url = urlparse(html_baseurl)
    robots = urljoin(url.scheme + "://" + url.netloc, "robots.txt")
    resp = requests.head(robots)
    if not resp.ok:
        logger.warning(f"robots.txt file not found at {robots}, please add one.")


def priorities_generator():
    """
    Generator returning ``priority`` needed by sitemap.xml.

    It generates values from 1 to 0.1 by decreasing in 0.1 on each
    iteration. After 0.1 is reached, it will keep returning 0.1.

    Copied from readthedocs
    """
    priorities = [1, 0.9, 0.8, 0.7, 0.6, 0.5, 0.4, 0.3, 0.2]
    yield from itertools.chain(priorities, itertools.repeat(0.1))


def changefreqs_generator():
    """
    Generator returning ``changefreq`` needed by sitemap.xml.

    It returns ``weekly`` on first iteration, ~~then ``daily`` and~~, then it
    will return always ``monthly``.

    Note: readthedocs uses `daily` for /latest which corresponds to the
    dev version. We prefer not to reference the dev version at all.

    We are using ``monthly`` as last value because ``never`` is too
    aggressive. If the tag is removed and a branch is created with the same
    name, we will want bots to revisit this.

    Copied and adapted from readthedocs
    """
    # changefreqs = ["weekly", "daily"]
    changefreqs = ["weekly"]
    yield from itertools.chain(changefreqs, itertools.repeat("monthly"))


def indent_xml(elem, level=0):
    i = "\n" + level * "  "
    if len(elem):
        if not elem.text or not elem.text.strip():
            elem.text = i + "  "
        for child in elem:
            indent_xml(child, level + 1)
        if not elem[-1].tail or not elem[-1].tail.strip():
            elem[-1].tail = i
        if not elem.tail or not elem.tail.strip():
            elem.tail = i
    else:
        if not elem.tail or not elem.tail.strip():
            elem.tail = i


def build_sitemap(app):
    """
    Build a sitemap.xml file, inspired by readthedocs.

    Uses the data in switcher.json. Output file is saved next to
    conf.py.

    Does not include the dev version.
    """
    theme_opts = app.config.html_theme_options
    if (
        isinstance(theme_opts, dict)
        and 'switcher' not in theme_opts
    ):
        return
    confdir = Path(app.confdir)
    switcher_path = confdir / '_static' / 'switcher.json'
    if not switcher_path.exists():
        logger.warning(
            "switcher.json not found in _static directory, sitemap.xml "
            "cannot be built."
        )
        return

    with open(switcher_path) as f:
        switcher_data = json.load(f)

    switcher_data =  [data for data in switcher_data if data.get('version') != 'dev']
    switcher_data = sorted(
        switcher_data,
        key=lambda el: version.parse(el['version']),
        reverse=True,
    )

    versions = []
    for data, priority, changefreq in zip(switcher_data, priorities_generator(), changefreqs_generator()):
        element = {
            'loc': data['url'],
            # 'lastmod': '?',
            'changefreq': changefreq,
            'priority': priority,
        }
        versions.append(element)

    urlset = ET.Element("urlset", xmlns="http://www.sitemaps.org/schemas/sitemap/0.9")

    for entry in versions:
        url = ET.SubElement(urlset, "url")
        ET.SubElement(url, "loc").text = entry["loc"]
        # ET.SubElement(url, "lastmod").text = "?"
        ET.SubElement(url, "changefreq").text = entry["changefreq"]
        ET.SubElement(url, "priority").text = str(entry["priority"])

    indent_xml(urlset)
    tree = ET.ElementTree(urlset)
    tree.write(confdir / "sitemap.xml", encoding="utf-8", xml_declaration=True)


def setup(app):
    app.connect('builder-inited', check_for_switcher_key)
    app.connect('builder-inited', check_for_robots)
    app.connect('builder-inited', build_sitemap)
    return {
        "version": nbs_version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
