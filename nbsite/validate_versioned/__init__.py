"""
validate_versioned extension to support versioned sites.

- Checks html_baseurl is set
- Creates a sitemap.xml file in a subdirectory of the docs source
- Creates a robots.txt file in a subdirectory of the docs source
"""
import itertools
import json
import shutil
import xml.etree.ElementTree as ET

from pathlib import Path
from urllib.parse import urljoin, urlparse

from packaging import version
from sphinx.util import logging

from .. import __version__ as nbs_version

logger = logging.getLogger(__name__)


OUTPUT_DIR = "_nbsite_versioned"


def domain_from_baseurl(html_baseurl: str) -> str:
    url = urlparse(html_baseurl)
    return url.scheme + "://" + url.netloc


def check_for_html_baseurl(app):
    """
    html_baseurl should be set for Sphinx to add to each page's head:
    <link rel="canonical" href="<html_baseurl>/<path/to/page.html>" />
    Useful for SEO purposes.
    """
    if not app.config.html_baseurl:
        logger.warning(
            "html_baseurl must be set when the site is versioned. For example: "
            "`html_baseurl = 'https://hvplot.holoviz.org/en/docs/latest/'`"
        )


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
    """
    Utility to pretty format an XML element.
    """
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


def get_switcher_data(app):
    switcher_path = Path(app.confdir, '_static', 'switcher.json')
    if not switcher_path.exists():
        raise FileNotFoundError(
            "switcher.json not found in _static directory, sitemap.xml "
            "cannot be built."
        )

    with open(switcher_path) as f:
        switcher_data = json.load(f)
    return switcher_data


def build_sitemap(app, our_dir):
    """
    Build a sitemap.xml file, inspired by readthedocs.

    Uses the data in switcher.json. Output file is saved next to
    conf.py.

    Does not include the dev version.
    """
    try:
        switcher_data = get_switcher_data(app)
    except FileNotFoundError as e:
        logger.warning(str(e))
        return

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
    out_path = Path(our_dir, "sitemap.xml")
    tree.write(out_path, encoding="utf-8", xml_declaration=True)
    logger.info(f"sitemap.txt written at {out_path}")


def build_robots(app, our_dir):
    """
    Build a robots.txt file, that disallows all paths except /en/docs/latest.
    """
    html_baseurl = app.config.html_baseurl
    if not html_baseurl:
        # check_for_html_baseurl already handles warning here.
        return
    sitemap_url = urljoin(domain_from_baseurl(html_baseurl), "sitemap.xml")

    out_path = Path(our_dir, "robots.txt")
    with open(out_path, "w", encoding="utf-8") as f:
        f.write("# Generated automatically by nbsite\n")
        f.write("User-agent: *\n")
        f.write("Disallow: /\n")
        f.write("Allow: /$\n")
        f.write("Allow: /en/docs/latest/\n")
        f.write(f"Sitemap: {sitemap_url}\n")
    logger.info(f"robots.txt written at {out_path}")


def build_404(out_dir):
    file_404 = Path(__file__).parent / "404.html"
    if not file_404.exists():
        logger.warning("Missing 404.html file")
        return
    out_path = out_dir / "404.html"
    shutil.copyfile(file_404, out_path)
    logger.info(f"404.html written at {out_path}")


def validate_versioned(app, exc):
    if not app.config.validate_versioned:
        return
    if exc:
        logger.debug("Exception, skipping validate_versioned")
        return
    theme_opts = app.config.html_theme_options
    # Detect whether versioning is enabled.
    if (
        isinstance(theme_opts, dict)
        and 'switcher' not in theme_opts
    ):
        return
    check_for_html_baseurl(app)
    out_dir = Path(app.outdir, OUTPUT_DIR)
    out_dir.mkdir(parents=True, exist_ok=True)
    build_sitemap(app, out_dir)
    build_robots(app, out_dir)
    build_404(out_dir)


def setup(app):
    app.add_config_value("validate_versioned", True, "html")
    app.connect('build-finished', validate_versioned)
    return {
        "version": nbs_version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
