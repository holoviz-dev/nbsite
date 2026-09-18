#!/usr/bin/env python
"""
Cleans up relative cross-notebook links by replacing them with .html
extension.
"""
import os
import posixpath
import re
import warnings

from concurrent.futures import ProcessPoolExecutor
from functools import partial
from pathlib import Path

import lxml.html

# TODO: holoviews specific links e.g. to reference manual...doc & generalize

#BOKEH_REPLACEMENTS = {'cell.output_area.append_execute_result': '//cell.output_area.append_execute_result',
#                      '}(window));\n</div>': '}(window));\n</script></div>',
#                      '\n(function(root) {': '<script>\n(function(root) {'}

# Fix gallery links (e.g to the element gallery)
#LINK_REPLACEMENTS = {'../../examples/elements/':'../gallery/elements/',
#                     '../../examples/demos/':'../gallery/demos/',
#                     '../../examples/streams/':'../gallery/streams/'}


def filter_available(names, name_type):
    available = []
    for name in names:
        reference_dir = os.path.abspath(os.path.join(__file__, '..','..', '..',
                                                     'examples', 'reference'))
#        if not os.path.isdir(reference_dir):
#            raise Exception('Cannot find examples/reference in %r' % reference_dir)

        for backend in ['bokeh', 'matplotlib', 'plotly']:
            candidate = os.path.join(reference_dir, name_type, backend, name+'.ipynb')
            if os.path.isfile(candidate):
                replacement_tpl = """<a href='../reference/{clstype}/{backend}/{clsname}.html'>
                <code>{clsname}</code></a>"""
                replacement = replacement_tpl.format(clstype=name_type,
                                                     clsname=name,
                                                     backend=backend)
                available.append((name, replacement))
                break
    return available


# TODO: allow to register stuff
def find_autolinkable():

    try:
        import holoviews as hv
        import param
    except ImportError:
        print('no holoviews and/or param: skipping autolinks')
        return {}

    # Class names for auto-linking
    excluded_names = { 'UniformNdMapping', 'NdMapping', 'MultiDimensionalMapping',
                       'Empty', 'CompositeOverlay', 'Collator', 'AdjointLayout'}
    dimensioned = set(param.concrete_descendents(hv.core.Dimensioned).keys())

    all_elements = set(param.concrete_descendents(hv.Element).keys())
    all_streams = set(param.concrete_descendents(hv.streams.Stream).keys())
    all_containers = set((dimensioned - all_elements) - excluded_names)
    return {'elements':   filter_available(all_elements, 'elements'),
            'streams':    filter_available(all_streams, 'streams'),
            'containers': filter_available(all_containers, 'containers')}


_HTML_TAG_RE = re.compile(r"<html[\s>]", re.IGNORECASE)


def _uses_component_links(path):
    return ('user_guide' in path) or ('getting_started' in path)


def component_links(text, path, autolinkable=None):
    if _uses_component_links(path):
        if autolinkable is None:
            autolinkable = find_autolinkable()
        for clstype, listing in autolinkable.items():
            for (clsname, replacement) in list(listing):
                try:
                    text, count = re.subn(r'<code>\s*{clsname}\s*</code>*'.format(clsname=clsname),replacement, text)
                except Exception as e:
                    print(str(e))
    return text


def cleanup_links(path, inspect_links=False, autolinkable=None):
    """
    Use inspect_links to get a list of all the external links in the site

    Returns the warning messages instead of warning, as warnings raised in
    the worker processes of fix_links do not reach the main process.
    """
    with open(path, encoding='utf-8') as f:
        text = f.read()
    # Not a page, e.g. a Jinja template a theme copies to _static, which
    # parsing as a document would wrap in <html> and URL-encode
    if _HTML_TAG_RE.search(text) is None:
        return []

#    if 'BokehJS does not appear to have successfully loaded' in text:
#        for k, v in BOKEH_REPLACEMENTS.items():
#            text = text.replace(k, v)

    text = component_links(text, path, autolinkable)
    # huge_tree as embedded outputs can exceed libxml2's limit for a text node
    parser = lxml.html.HTMLParser(huge_tree=True)
    tree = lxml.html.document_fromstring(text, parser=parser)
    messages = []
    # libxml2 percent-escapes whitespace in URI attributes when serializing,
    # and whitespace in base64 is ignored anyway
    for element in tree.xpath('//*[starts-with(@src, "data:") or starts-with(@href, "data:")]'):
        for attribute in ('src', 'href'):
            value = element.get(attribute, '')
            if value.startswith('data:') and ';base64,' in value:
                element.set(attribute, ''.join(value.split()))

    for a in tree.iter('a'):
        href = a.get('href', '')
        if '.ipynb' in href and 'http' not in href:
 #           for k, v in LINK_REPLACEMENTS.items():
 #               href = href.replace(k, v)
            href = href.replace('.ipynb', '.html')
            a.set('href', href)

            # check to make sure that path exists, if not, try un-numbered version
            link, sep, fragment = href.partition('#')
            try_path = os.path.join(os.path.dirname(path), link)
            if not os.path.exists(try_path):
                num_name = os.path.basename(try_path)
                name = re.split(r"^#?\d+( |-|_)", num_name)[-1]
                new_path = try_path.replace(num_name, name)
                if os.path.exists(new_path):
                    # A URL, so always with forward slashes, also on Windows
                    href = os.path.relpath(new_path, os.path.dirname(path)).replace(os.sep, '/')
                    a.set('href', href + sep + fragment)
                else:
                    also_tried = 'Also tried: {}'.format(name) if name != num_name else ''
                    messages.append('Found missing link {} in: {}. {}'.format(href, path, also_tried))

        elif href.endswith('/') and 'http' not in href:
            a.set('href', href + 'index.html')

        if inspect_links and 'http' in a.get('href', ''):
            print(a.get('href'))

    for img in tree.iter('img'):
        src = img.get('src', '')
        if 'http' not in src and 'assets' in src:
            try_path = os.path.join(os.path.dirname(path), src)
            if not os.path.exists(try_path):
                also_tried = posixpath.join('..', src)
                if os.path.exists(os.path.join(os.path.dirname(path), also_tried)):
                    img.set('src', also_tried)
                else:
                    messages.append(f'Found reference to missing image {src} in: {path}. Also tried: {also_tried}')

    doctype = tree.getroottree().docinfo.doctype or None
    with open(path, 'w', encoding='utf-8') as f:
        f.write(lxml.html.tostring(tree, doctype=doctype, encoding='unicode'))
    return messages

def fix_links(build_dir, inspect_links=False):
    files = [os.fspath(path) for path in Path(build_dir).rglob("*.html")]
    autolinkable = find_autolinkable() if any(map(_uses_component_links, files)) else {}
    func = partial(cleanup_links, inspect_links=inspect_links, autolinkable=autolinkable)
    # Processes instead of threads, as editing the parsed pages holds the GIL
    with ProcessPoolExecutor() as executor:
        for messages in executor.map(func, files, chunksize=8):
            for msg in messages:
                warnings.warn(msg)
