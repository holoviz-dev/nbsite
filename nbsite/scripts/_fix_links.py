#!/usr/bin/env python
"""
Cleans up relative cross-notebook links by replacing them with .html
extension.
"""
import os
import re
import warnings

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from pathlib import Path

from bs4 import BeautifulSoup

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



def component_links(text, path):
    autolinkable = find_autolinkable()

    if ('user_guide' in path) or ('getting_started' in path):
        for clstype, listing in autolinkable.items():
            for (clsname, replacement) in list(listing):
                try:
                    text, count = re.subn(r'<code>\s*{clsname}\s*</code>*'.format(clsname=clsname),replacement, text)
                except Exception as e:
                    print(str(e))
    return text


def cleanup_links(path, inspect_links=False):
    """
    Use inspect_links to get a list of all the external links in the site
    """
    with open(path) as f:
        text = f.read()

#    if 'BokehJS does not appear to have successfully loaded' in text:
#        for k, v in BOKEH_REPLACEMENTS.items():
#            text = text.replace(k, v)

    text = component_links(text, path)
    soup = BeautifulSoup(text, features="html.parser")
    for a in soup.find_all('a'):
        href = a.get('href', '')
        if '.ipynb' in href and 'http' not in href:
 #           for k, v in LINK_REPLACEMENTS.items():
 #               href = href.replace(k, v)
            a['href'] = href.replace('.ipynb', '.html')

            # check to make sure that path exists, if not, try un-numbered version
            try_path = os.path.join(os.path.dirname(path), a['href'])
            if not os.path.exists(try_path):
                num_name = os.path.basename(try_path)
                name = re.split(r"^#?\d+( |-|_)", num_name)[-1]
                new_path = try_path.replace(num_name, name)
                if os.path.exists(new_path):
                    a['href'] = os.path.relpath(new_path, os.path.dirname(path))
                else:
                    also_tried = 'Also tried: {}'.format(name) if name != num_name else ''
                    msg = 'Found missing link {} in: {}. {}'.format(a['href'], path, also_tried)
                    warnings.warn(msg)

        if inspect_links and 'http' in a['href']:
            print(a['href'])

    for img in soup.find_all('img'):
        src = img.get('src', '')
        if 'http' not in src and 'assets' in src:
            try_path = os.path.join(os.path.dirname(path), src)
            if not os.path.exists(try_path):
                also_tried = os.path.join('..', src)
                if os.path.exists(os.path.join(os.path.dirname(path), also_tried)):
                    img['src'] = also_tried
                else:
                    msg = f'Found reference to missing image {src} in: {path}. Also tried: {also_tried}'
                    warnings.warn(msg)
    with open(path, 'w', encoding='utf-8') as f:
        f.write(str(soup))

def fix_links(build_dir, inspect_links=False):
    files = map(os.fspath, Path(build_dir).rglob("*.html"))
    with ThreadPoolExecutor() as executor:
        func = partial(cleanup_links, inspect_links=inspect_links)
        # list to force execution and raise potential exception
        list(executor.map(func, files))
