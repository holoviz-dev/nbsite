import glob
import json
import logging
import os
import pathlib
import re
import shutil

from concurrent.futures import ThreadPoolExecutor
from functools import partial
from urllib.parse import urlparse

import nbformat
import requests
import sphinx.util.logging

from PIL import Image

try:
    import bs4
except ImportError:
    bs4 = None

from .thumbnailer import execute, notebook_thumbnail

logger = sphinx.util.logging.getLogger('nbsite-gallery')
logging.getLogger(requests.packages.urllib3.__package__).setLevel(logging.ERROR)

BUTTON_GROUP_TEMPLATE = """
.. raw:: html

    <script>
    function gallery_toggle(input) {{
        var backends = {backends};
        for (var i = 0; i < backends.length; i++) {{
            var entries = document.getElementsByClassName(backends[i] + '-example');
            for (var j = 0; j < entries.length; j++) {{
                var parent = entries[j].parentNode;
                if (backends[i] == input) {{
                    parent.style.display = '';
                }} else {{
                    parent.style.setProperty('display', 'none', 'important');
                }}
            }}
        }}
    }}
    </script>

    <ul class="tab">
    {buttons}
    </ul>

"""

BUTTON_TEMPLATE = """
        <li>
            <input id="tab{N}" {checked} type="radio" name="tab" onclick="gallery_toggle('{label}'.toLowerCase())" />
            <label for="tab{N}">{label}</label>
        </li>
"""

HIDE_JS = """
.. raw:: html

    <script>
    document.addEventListener('DOMContentLoaded', function () {{
        var backends = {backends};
        for (var i = 0; i < backends.length; i++) {{
            var elements = document.getElementsByClassName(backends[i] + '-example');
            for (var j = 0; j < elements.length; j++) {{
                elements[j].parentNode.style.setProperty('display', 'none', 'important');
            }}
        }}
    }});
    </script>
"""

THUMBNAIL_URL = 'https://assets.holoviews.org/thumbnails'

PREFIX = """
# -*- coding: utf-8 -*-
import holoviews as hv
from pyviz_comms import Comm

try:
    import holoviews.plotting.mpl
    hv.Store.renderers['matplotlib'].comms['default'] = (Comm, '')
except:
    pass

try:
    import holoviews.plotting.bokeh
    hv.Store.renderers['bokeh'].comms['default'] = (Comm, '')
except:
    pass

try:
    import holoviews.plotting.widgets as hw
    hw.NdWidget.export_json=True
    hw.NdWidget.json_load_path = './'
    hw.NdWidget.json_save_path = './'
    del hw
except:
    pass

hv.plotting.mpl.MPLPlot.fig_alpha = 0
hv.plotting.bokeh.callbacks.Callback._comm_type = Comm
"""

REFERENCE_INTRO="""
The gallery presents the various components made available by
HoloViews from which you can build new visualizations. If you wish to
see a collection of more involved examples, see the `Gallery
<../gallery/index.html>`_. To get started with HoloViews, see our
`Getting Started <../getting_started/index.html>`_ guide and for more
detailed documentation our `User Guide <../user_guide/index.html>`_.
"""

GALLERY_INTRO="""
The gallery shows the breadth of what HoloViews is capable of with a
varied collection of examples.  If you are looking for a specific
component (or wish to view the available range of primitives), see our
`Reference Gallery <../reference/index.html>`_. To get started with
HoloViews, see our `Getting Started <../getting_started/index.html>`_
guide and for more detailed documentation our `User Guide
<../user_guide/index.html>`_.
"""

THUMBNAIL_TEMPLATE_LABEL_IN_TITLE = """
    .. grid-item-card:: {label}
        :link: {link}
        :link-type: doc
        :class-card: {backend_prefix}example
        :shadow: md

        .. image:: /{thumbnail}
            :alt: {label}
"""

THUMBNAIL_TEMPLATE_LABEL_IN_DESC = """
    .. grid-item-card::
        :link: {link}
        :link-type: doc
        :class-card: {backend_prefix}example
        :shadow: md

        .. image:: /{thumbnail}
            :alt: {label}

        {label}
"""

IFRAME_TEMPLATE = """

.. raw:: html

    <style>
      .iframe-container {{
        overflow: hidden;
        padding-top: 56.25%;
        position: relative;
        background: url({background}) center center no-repeat;
      }}

      .iframe-container iframe {{
        border: 0;
        height: 100%;
        left: 0;
        position: absolute;
        top: 0;
        width: 100%;
      }}
    </style>

    <div class="iframe-container">
      <iframe src="{url}" width="100%" frameborder="0" onload="this.parentNode.style.background = 'none'"></iframe>
    </div>
"""


DEFAULT_GALLERY_CONF = {
    'backends': None,
    'default_extensions': ['*.ipynb', '*.py'],
    'enable_download': True,
    'only_use_existing': False,
    'as_pyodide': False,
    'skip_rst_notebook_directive': False,
    'examples_dir': os.path.join('..', 'examples'),
    'labels_dir': 'labels',
    'galleries': {
        'gallery': {
            'backends': [],
            'extensions': ['*.ipynb', '*.py'],
            'intro': 'Sample intro',
            'title': 'A sample gallery title',
            'sections': [],
        }
    },
    'host': 'GitHub',  # set this to assets to have download happen from assets
    'download_as': None,  # set this to 'project' to use project archives as download
    'github_org': None,
    'github_project': None,
    'deployment_url': None,
    'iframe_spinner': "https://assets.holoviews.org/static/spinner.gif",
    'inline': False,
    'script_prefix': PREFIX,
    'skip_execute': [],
    'thumbnail_url': THUMBNAIL_URL,
    'thumbnail_size': (400, 280),
    'within_subsection_order': None,
    'nblink': 'both',  # use this to control the position of the nblink
    'github_ref': 'main',  # branch or tag
    'jupyterlite_url': None,
    'titles_from_files': False,
    'grid_no_columns': (2, 2, 4, 5),
}

def get_deployed_url(deployment_urls, basename):
    for deployment_url in deployment_urls:
        # Test the deployment_url/basename, then deployment_url/notebooks/basename.ipynb
        candidates = [os.path.join(deployment_url,
                                   basename[:-6] if basename.endswith('.ipynb') else basename),
                      os.path.join(deployment_url, 'notebooks',
                                   basename if basename.endswith('ipynb')
                                   else '%s.ipynb' % basename )]
        for candidate in candidates:
            r = requests.get(candidate, verify=False)
            if r.status_code == 200:
                return candidate

    # Check deployment_urls directly
    for deployment_url in deployment_urls:
        r = requests.get(deployment_url, verify=False)
        if r.status_code == 200:
            return deployment_url
    return None

def get_nblink_md(
    host, deployed_file, jupyterlite_url, download_as,
    org, proj, ref, components, basename, ftype, section
):
    text = ''
    if deployed_file:
        text += f'[View a running version of this notebook]({deployed_file}) | '
    if jupyterlite_url:
        text += f'[Open this notebook in Jupyterlite]({jupyterlite_url}) | '
    path = '/'.join(components)
    if host == 'GitHub' and org and proj:
        text += (
            f'[Download this {ftype} from GitHub (right-click to download).]'
            f'(https://raw.githubusercontent.com/{org}/{proj}/{ref}/{path}/{basename})'
        )
    elif host == 'assets':
        if download_as == 'project':
            text += f'[Download this project.](</assets/{section}.zip>)'
        else:
            text += f'[Download this {ftype}](</assets/{path}/{basename})'
    return text

NO_IMAGE_THUMB = pathlib.Path(__file__).parent / "no_image.png"

def get_nblink_rst(
    host, deployed_file, jupyterlite_url, download_as,
    org, proj, ref, components, basename, ftype, section
):
    text = ''
    if deployed_file:
        text += f'`View a running version of this notebook <{deployed_file}>`_ | '
    if jupyterlite_url:
        text += f'`Open this notebook in Jupyterlite <{jupyterlite_url}>`_ | '
    path = '/'.join(components)
    if host == 'GitHub' and org and proj:
        text += (
            f'`Download this {ftype} from GitHub (right-click to download).'
            f' <https://raw.githubusercontent.com/{org}/{proj}/{ref}/{path}/{basename}>`_'
        )
    elif host == 'assets':
        if download_as == 'project':
            text += f'`Download this project. </assets/{section}.zip>`_'
        else:
            text += f'`Download this {ftype}. </assets/{path}/{basename}>`_'
    return text

def replace_ipynb_links(line: str, filepath: str) -> str:
    """
    Replace relative .ipynb links in a Markdown line with .md links if the .ipynb file exists.

    Arguments
    ---------
    line: str
        A line of Markdown text.
    filepath: str
        The path to the Markdown file containing the line.

    Returns
    -------
    The modified line with .ipynb links replaced by .md links where applicable.
    """
    markdown_link_regex = re.compile(r'\[([^\]]+)\]\(([^)]+)\)')

    def replace_link(match):
        text = match.group(1)
        link = match.group(2)

        # Do not change absolute links and non-ipynb links
        parsed_url = urlparse(link)
        if parsed_url.scheme != '' or parsed_url.netloc != '' or not link.lower().endswith('.ipynb'):
            return match.group(0)

        md_dir = os.path.dirname(os.path.abspath(filepath))
        ipynb_path = os.path.normpath(os.path.join(md_dir, link))

        if os.path.exists(ipynb_path):
            new_link = re.sub(r'\.ipynb$', '', link, flags=re.IGNORECASE)
            return f'[{text}]({new_link})'
        else:
            # The .ipynb file does not exist; do not modify
            return match.group(0)

    new_line = markdown_link_regex.sub(replace_link, line)
    return new_line

def convert_notebook_to_md(filename, directive='{pyodide}'):
    with open(filename, encoding='utf-8') as nb:
        nb_json = json.loads(nb.read())

    md = ''
    for cell in nb_json['cells']:
        ctype = cell['cell_type']
        if ctype == 'raw':
            continue
        if md:
            md += '\n\n'
        source = cell['source']
        if ctype == 'code':
            nticks = 4 if any('```' in src for src in source) else 3
            backticks = '`'*nticks
            md += f'{backticks}{directive}\n'
        for src in source:
            if ctype == 'markdown':
                src = replace_ipynb_links(src, filename)
            md += src
        if ctype == 'code':
            md += f'\n{backticks}'
    return md

def generate_pyodide_markdown(
    app, page, section, backend, filename, src_dir, dest_dir,
    img_extension, deployed_file, deployed, skip
):
    """
    Generates a Markdown file that renders the notebook cells using
    the pyodide directive.
    """
    # Set up paths
    extension = filename.split('.')[-1]
    basename = os.path.basename(filename)
    md_path = os.path.join(dest_dir, basename[:-len(extension)].replace(' ', '_') + 'md')
    name = basename[:-(len(extension)+1)]
    title = ' '.join([n[0].capitalize()+n[1:] for n in name.replace('_', ' ').split(' ')])
    ftype = 'notebook' if extension == 'ipynb' else 'script'

    # Unpack config
    gallery_conf = app.config.nbsite_gallery_conf
    examples_dir = gallery_conf['examples_dir']
    content = gallery_conf['galleries'][page]

    # Download link options
    host = gallery_conf['host']
    download_as = gallery_conf['download_as']
    host = gallery_conf['host']
    nblink = gallery_conf['nblink']
    ref = gallery_conf['github_ref']
    org = gallery_conf['github_org']
    proj = gallery_conf['github_project']
    jupyterlite_url = gallery_conf['jupyterlite_url']

    # Deployed app options
    endpoint = content.get('deployment_url', gallery_conf['deployment_url'])
    iframe_spinner = gallery_conf['iframe_spinner']

    skip_execute = gallery_conf['skip_execute']
    directive = 'python' if skip_execute else '{pyodide}'

    if nblink:
        components = [examples_dir.split(os.path.sep)[-1], page]
        if section:
            components.append(section)
        if backend:
            components.append(backend)
        if jupyterlite_url:
            backend_slug = '/{backend}' if backend else ''
            lite_path = f'{jupyterlite_url}?path=/{page}/{section}{backend_slug}/{basename}'
        else:
            lite_path = None
        nblink_text = get_nblink_md(
            host, deployed_file, lite_path, download_as,
            org, proj, ref, components, basename, ftype, section
        )

    # Generate RST
    with open(md_path, 'w') as md_file:
        md_file.write(f'# {title}\n\n')

        if nblink in ['top', 'both']:
            md_file.write(f'{nblink_text}\n\n---\n')

        if ftype == 'notebook':
            nb_md = convert_notebook_to_md(filename, directive)
            md_file.write(nb_md)
        elif extension == 'md':
            with open(filename, encoding='utf-8') as md_src_file:
                md_file.write('\n'.join(md_src_file.readlines()[1:]))
        else:
            with open(filename, encoding='utf-8') as script:
                md_file.write(f'```{directive}\n{script.read()}```')
        if deployed:
            md_file.write(
                IFRAME_TEMPLATE.format(
                    background=iframe_spinner, url=endpoint+name
                )
            )

        if nblink in ['bottom', 'both']:
            md_file.write(f'\n\n---\n{nblink_text}')

def generate_item_rst(
    app, page, section, backend, filename, src_dir, dest_dir,
    img_extension, deployed_file, deployed, skip
):
    """
    Generates an RST file that includes a notebook directive to run
    the example.
    """
    # Set up paths
    extension = filename.split('.')[-1]
    basename = os.path.basename(filename)
    name = basename[:-(len(extension)+1)]
    rel_path = os.path.relpath(os.path.join(src_dir, basename), dest_dir)
    rst_path = os.path.join(dest_dir, basename[:-len(extension)].replace(' ', '_') + 'rst')
    title = ' '.join([n[0].capitalize()+n[1:] for n in name.replace('_', ' ').split(' ')])
    ftype = 'notebook' if extension == 'ipynb' else 'script'

    # Unpack config
    gallery_conf = app.config.nbsite_gallery_conf
    examples_dir = gallery_conf['examples_dir']
    content = gallery_conf['galleries'][page]
    skip_execute = gallery_conf['skip_execute']

    # Download link options
    download_as = gallery_conf['download_as']
    host = gallery_conf['host']
    nblink = gallery_conf['nblink']
    ref = gallery_conf['github_ref']
    org = gallery_conf['github_org']
    proj = gallery_conf['github_project']
    jupyterlite_url = gallery_conf['jupyterlite_url']

    # Deployed app options
    endpoint = content.get('deployment_url', gallery_conf['deployment_url'])
    iframe_spinner = gallery_conf['iframe_spinner']

    # Do not write existing (unless auto-generated)
    if os.path.isfile(rst_path):
        with open(rst_path) as existing:
            if 'Originally generated by nbsite' not in existing.read():
                return

    if nblink:
        components = [examples_dir.split(os.path.sep)[-1], page]
        if section:
            components.append(section)
        if backend:
            components.append(backend)
        nblink_text = get_nblink_rst(
            host, deployed_file, jupyterlite_url, download_as,
            org, proj, ref, components, basename, ftype, section
        )

    # Generate RST
    with open(rst_path, 'w') as rst_file:
        rst_file.write(title+'\n')
        rst_file.write('='*len(title)+'\n\n')

        if nblink in ['top', 'both']:
            rst_file.write(f'{nblink_text}\n\n-------\n\n')

        if ftype == 'notebook':
            rst_file.write(".. notebook:: %s %s" % (proj, rel_path))
            if deployed or (isinstance(skip, bool) and skip) or any(
                basename.strip().endswith(skipped) for skipped in skip_execute
            ):
                rst_file.write('\n    :skip_execute: True\n')
            if deployed:
                rst_file.write(IFRAME_TEMPLATE.format(
                    background=iframe_spinner, url=endpoint+name))
        else:
            rst_file.write(f'.. literalinclude:: {rel_path}\n\n')
            url = os.path.join('thumbnails', f'{name}.{img_extension}')
            rst_file.write(f'.. figure:: {url}\n\n')

        if nblink in ['bottom', 'both']:
            rst_file.write(f'\n\n-------\n\n{nblink_text}')

def get_deployed_examples(endpoint):
    # Try to fetch all deployed examples
    if not bs4 or endpoint is None:
        return []
    r = requests.get(endpoint, verify=False)
    if r.status_code != 200:
        return []

    soup = bs4.BeautifulSoup(r.content, features='lxml')
    try:
        deployed_examples = [
            l.text for l in soup.find('div', {"class": "list-group"}).find_all('h4')
        ]
    except Exception:
        deployed_examples = [
            l.get('id')[1:] for l in soup.find('ul', {"class": "cards-grid"}).find_all('a', {"class": "card-link"})
        ]
        if not deployed_examples:
            deployed_examples = [l.text for l in soup.find('ul').find_all('a')]
    return deployed_examples

def generate_file_rst(
    app, src_dir, dest_dir, page, section, backend, img_extension, skip, deployment_urls
):
    gallery_conf = app.config.nbsite_gallery_conf
    content = gallery_conf['galleries'][page]
    endpoint = content.get('deployment_url', gallery_conf.get('deployment_url', None))
    extensions = content.get('extensions', gallery_conf['default_extensions'])
    as_pyodide = content.get('as_pyodide', gallery_conf.get('as_pyodide', False))
    skip_rst_notebook_directive = content.get(
        'skip_rst_notebook_directive',
        gallery_conf.get('skip_rst_notebook_directive', False)
    )

    deployed_examples = get_deployed_examples(endpoint)

    files = []
    for extension in extensions:
        files += glob.glob(os.path.join(src_dir, extension))

    for filename in files:
        if isinstance(skip, list) and os.path.basename(filename) in skip:
            continue
        extension = filename.split('.')[-1]
        basename = os.path.basename(filename)
        name = basename[:-(len(extension)+1)]
        deployed = name in deployed_examples
        try:
            deployed_file = get_deployed_url(deployment_urls, basename)
        except Exception:
            deployed_file = None

        # Generate document
        if as_pyodide:
            gen = generate_pyodide_markdown
        elif not skip_rst_notebook_directive:
            gen = generate_item_rst
        else:
            gen = None
        if gen:
            gen(app, page, section, backend, filename, src_dir, dest_dir,
                img_extension, deployed_file, deployed, skip)


REDIRECT = """.. raw:: html

    <head>
        <meta http-equiv='refresh' content='0; URL={rel}/index.html#{section}'>
    </head>
"""

def generate_section_index(section, items, dest_dir, rel='..', title=None):
    """
    Builds index pages for each section which redirect to the main
    gallery index.
    """
    # Reference to section header
    section_ref = section.lower().replace(' ', '-').replace('_', '-')
    index_page = REDIRECT.format(rel=rel, section=section_ref)
    title = title or section.replace('_', ' ')
    index_page += '\n' + title + '\n' + '_'*len(title) + '\n'
    index_page += '\n\n.. toctree::\n   :glob:\n   :hidden:\n\n   '
    index_page += '\n   '.join(items)
    with open(os.path.join(dest_dir, 'index.rst'), 'w', encoding='utf-8') as f:
        f.write(index_page)

def _normalize_label(string):
    return ' '.join([s[0].upper()+s[1:] for s in string.split('_')])

def _thumbnail_div(thumb_path, section, backend, fname, normalize=True, title=None, card_title_below=False):
    """Generates RST to place a thumbnail in a gallery"""
    if title is not None:
        label = title
    elif normalize:
        label = _normalize_label(fname)
    else:
        label = fname

    # Inside rst files forward slash defines paths
    thumb_path = thumb_path.replace(os.sep, "/")

    if section and backend:
        section_path = f'{section}/{backend}'
    elif section and not backend:
        section_path = section
    elif not section and backend:
        section_path = backend
    else:
        section_path = ''

    link = f'{section_path}/{fname}'

    if card_title_below:
        tpl = THUMBNAIL_TEMPLATE_LABEL_IN_DESC
    else:
        tpl = THUMBNAIL_TEMPLATE_LABEL_IN_TITLE

    return tpl.format(
        backend_prefix=backend+'-', thumbnail=thumb_path,
        label=label, link=link,
    )


def resize_pad(im_pth, desired_size=500):
    im = Image.open(im_pth)
    old_size = im.size  # old_size[0] is in (width, height) format

    ratio = float(desired_size)/max(old_size)
    new_size = tuple([int(x*ratio) for x in old_size])
    w = (desired_size-new_size[0])//2
    h = (desired_size-new_size[1])//2

    # LANCZOS replaced ANTIALIAS in PIL 10
    im_filter = getattr(Image, "LANCZOS", None) or getattr(Image, "ANTIALIAS", None)
    im = im.resize(new_size, im_filter)
    new_im = Image.new("RGBA", (desired_size, desired_size), color=(0, 0, 0, 0))
    new_im.paste(im, (w, h))
    new_im.save(im_pth)


def generate_gallery(app, page):
    """
    Generates a gallery for all example directories specified in
    the gallery_conf. Generates rst files for all found notebooks
    and copies the notebooks to doc/gallery/ relative to the supplied
    basepath. Also generates thumbnails and an overall index.
    """
    # Get config
    gallery_conf = app.config.nbsite_gallery_conf
    content = gallery_conf['galleries'][page]
    backends = content.get('backends', gallery_conf.get('backends', []))
    titles = content.get('titles', {})
    titles_from_files = content.get('titles_from_files', gallery_conf['titles_from_files'])
    normalize = content.get('normalize_titles', True)
    grid_no_columns = content.get('grid_no_columns', gallery_conf['grid_no_columns'])

    # Get directories
    doc_dir = app.builder.srcdir
    examples_dir = os.path.join(doc_dir, gallery_conf['examples_dir'])
    gallery_dir = os.path.join(examples_dir, page)
    static_dir = app.config.html_static_path[-1]
    static_path = os.path.join(
        os.path.split(gallery_conf['examples_dir'])[-2], static_dir)
    labels_dir = gallery_conf['labels_dir']
    labels_path = os.path.join(static_path, labels_dir)
    logo = app.config.html_theme_options.get('logo', 'images/logo.png')
    if isinstance(logo, dict):
        logo = logo['image_light']
    logo_path = os.path.join(static_path, logo)

    if 'sections' in content:
        sections = content['sections']
    else:
        sections = [s for s in glob.glob(os.path.join(gallery_dir, '*'))
                    if os.path.isdir(os.path.join(gallery_dir, s)) and
                    not any(s.endswith(b) for b in backends)]
        if not sections:
            sections = ['']

    extensions = content.get('extensions', gallery_conf['default_extensions'])
    sort_fn = gallery_conf['within_subsection_order']
    thumbnail_url = content.get('thumbnail_url', gallery_conf['thumbnail_url'])
    download = gallery_conf['enable_download']
    script_prefix = gallery_conf['script_prefix']
    only_use_existing = gallery_conf['only_use_existing']
    inline = gallery_conf['inline']
    card_title_below = content.get('card_title_below', False)
    no_image_thumb = content.get('no_image_thumb', False)

    if sort_fn is None:
        sort_fn = lambda key: titles.get(key, key)

    # Write gallery index
    title = content['title']
    gallery_rst = title + '\n' + '_'*len(title) + '\n'
    if 'intro' in content:
        gallery_rst += '\n' + content['intro'] + '\n'

    if backends:
        buttons = []
        for n, backend in enumerate(backends):
            buttons.append(BUTTON_TEMPLATE.format(N=n+1, checked='' if n else 'checked="checked"',
                                                  label=backend.capitalize()))
        gallery_rst += BUTTON_GROUP_TEMPLATE.format(buttons=''.join(buttons), backends=backends)

    toc = '\n\n.. toctree::\n   :glob:\n   :hidden:\n\n'
    section_backends = None
    for section in sections:
        if isinstance(section, dict):
            section_backends = section.get('backends', backends)
            skip = section.get('skip', content.get('skip', False))
            orphans = section.get('orphans', content.get('orphans', []))
            heading = section.get('title', section['path'])
            description = section.get('description', None)
            labels = section.get('labels', [])
            subsection_order = section.get('within_subsection_order', sort_fn)
            deployment_urls = section.get('deployment_urls', [])
            section = section['path']
        else:
            heading = section.title()
            skip = content.get('skip', False)
            orphans = content.get('orphans', [])
            section_backends = backends
            subsection_order = sort_fn
            description = None
            labels = []
            deployment_urls = []

        # Add section toctree
        if section:
            toc += f'   {section}/index\n'
        else:
            gallery_rst += f'.. toctree::\n   :glob:\n   :hidden:\n\n   {heading}\n   *\n\n'

        if heading:
            underline = '-'*len(heading)
            gallery_rst += f'\n\n{heading}\n{underline}\n\n'

        if labels:
            gallery_rst += '\n\n.. raw:: html\n\n'
            for label in sorted(labels):
                label_svg = os.path.join(labels_path, f'{label}.svg')
                if not os.path.exists(os.path.join(doc_dir, label_svg)):
                    logger.info(
                        f'Control the look of the {label} label by adding '
                        f'under _static/labels/{label}.svg (created using '
                        f'https://img.shields.io/badge/-{label}-<color>)')
                    label_svg = f'https://img.shields.io/badge/-{label}-aaaaaa'
                gallery_rst += f'    <img src="{label_svg}" title={label}>'

            gallery_rst += '\n\n'

        if description:
            gallery_rst += description + '\n\n'

        if isinstance(grid_no_columns, (tuple, list)):
            grid_no_columns = " ".join(str(s) for s in grid_no_columns)
        gallery_rst += f'.. grid:: {grid_no_columns}\n    :gutter: 3\n    :margin: 0\n'

        thumb_extension = 'png'

        path_components = [page]
        if section:
            path_components.append(section)
        dest_path = os.path.join(doc_dir, *path_components)
        section_path = os.path.join(examples_dir, *path_components)

        try:
            os.makedirs(dest_path)
        except Exception:
            pass
        if section and section_backends:
            backend_items = [f'{item}/index' for item in section_backends]
            generate_section_index(heading, backend_items, dest_path)
        for backend in (section_backends or ('',)):
            path = section_path
            dest_dir = dest_path
            if backend:
                path = os.path.join(path, backend)
                dest_dir = os.path.join(dest_path, backend)

            try:
                os.makedirs(dest_dir)
            except Exception:
                pass

            # Collect examples
            files = []
            for extension in extensions:
                files += glob.glob(os.path.join(path, extension))

            if isinstance(skip, list):
                files = [f for f in files if os.path.basename(f) not in skip]
            if orphans:
                files = [f for f in files if os.path.basename(f) not in orphans]
            if files:
                if inline:
                    gallery_rst = gallery_rst.replace(f'id="{section}-section"',
                        f'id="{section}-section" style="width: {180 * len(files)}px"')
                if backend:
                    backend_str = ' for %s backend' % backend
                else:
                    backend_str = ''
                logger.info("\n\nGenerating %d %s %s examples%s\n"
                            "__________________________________________________"
                            % (len(files), heading, title, backend_str))
                if section:
                    section_items = [
                        os.path.basename(f).split('.')[0] for f in sorted(files)
                    ]
                    generate_section_index(
                        heading, section_items, dest_dir,
                        rel='../..' if backend else '..',
                        title=backend.title() if backend else None
                    )
                if titles_from_files:
                    for file in files:
                        basename = pathlib.Path(file).stem
                        with open(file, "r") as f:
                            notebook = nbformat.read(f, as_version=4)
                        first_cell = notebook.cells[0]
                        if first_cell and first_cell["cell_type"] == "markdown":
                            try:
                                title = first_cell['source'].split('\n')[0].split("#")[1].strip()
                                titles[basename] = title
                            except Exception as e:
                                logger.error(
                                    f'Failed at getting the title from the notebook heading with: {e}\n\n'
                                    f'From notebook: {file}\n'
                                    f'From content: {first_cell["source"]}'
                                )

            sorted_files = sorted(files, key=subsection_order)
            with ThreadPoolExecutor() as ex:
                func = partial(_download_image, page, thumbnail_url, download, backend, section, dest_dir, no_image_thumb)
                futures = ex.map(func, sorted_files)

            for f, (thumb_extension, extension, basename, retcode, verb) in zip(sorted_files, futures):
                # Generate thumbnail
                if not retcode or only_use_existing:
                    pass
                elif extension == 'ipynb':
                    verb = 'Successfully generated'
                    print('getting thumbnail code for %s' % os.path.abspath(f))
                    print('Path exists %s' % os.path.exists(os.path.abspath(f)))
                    code = notebook_thumbnail(os.path.abspath(f), dest_dir)
                    code = script_prefix + code
                    my_env = os.environ.copy()
                    retcode = execute(code.encode('utf8'), env=my_env, cwd=os.path.split(f)[0])
                else:
                    retcode = 1

                if retcode:
                    logger.info('%s thumbnail export failed' % basename)
                    if extension == 'py':
                        continue
                    thumb_prefix = '_'.join([pre for pre in (section, backend) if pre])
                    if thumb_prefix:
                        thumb_prefix += '_'
                    if basename in titles:
                        label = titles[basename]
                    elif normalize:
                        label = _normalize_label(basename)
                    else:
                        label = basename

                    if section and backend:
                        section_path = f'{section}/{backend}'
                    elif section and not backend:
                        section_path = section
                    elif not section and backend:
                        section_path = backend
                    else:
                        section_path = ''

                    if section_path:
                        link = f'{section_path}/{basename}'
                    else:
                        link = basename
                    this_entry = THUMBNAIL_TEMPLATE_LABEL_IN_TITLE.format(
                        backend_prefix=backend+'-', thumbnail=logo_path,
                        label=label, link=link,
                    )
                else:
                    logger.info('%s %s thumbnail' % (verb, basename))
                    thumb_path = os.path.join(
                        dest_dir, 'thumbnails', f'{basename}.{thumb_extension}'
                    )
                    if thumb_extension not in ('svg', 'gif'):
                        resize_pad(os.path.join(doc_dir, thumb_path))
                    this_entry = _thumbnail_div(
                        thumb_path, section, backend, basename,
                        normalize, titles.get(basename),
                        card_title_below=card_title_below,
                    )

                gallery_rst += this_entry
            generate_file_rst(app, path, dest_dir, page, section,
                              backend, thumb_extension, skip, deployment_urls)
    gallery_rst += toc

    if backends or section_backends:
        gallery_rst += HIDE_JS.format(backends=repr(backends[1:]))
    with open(os.path.join(doc_dir, page, 'index.rst'), 'w', encoding='utf-8') as f:
        f.write(gallery_rst)


def _download_image(page, thumbnail_url, download, backend, section, dest_dir, no_image_thumb, f):
    extension = f.split('.')[-1]
    basename = os.path.basename(f)[:-(len(extension)+1)]

    # Try to fetch thumbnail otherwise regenerate it
    url_components = [thumbnail_url, page]

    if section:
        url_components.append(section)
    if backend:
        url_components.append(backend)
    url_components.append(f'{basename}.png')

    # if there is a . in the path, just get rid of it
    thumb_url = '/'.join(url_components).replace('/./', '/')

    thumb_dir = os.path.join(dest_dir, 'thumbnails')
    os.makedirs(thumb_dir, exist_ok=True)
    thumb_path = os.path.join(thumb_dir, f'{basename}.png')

    # Try existing file
    retcode = 1
    thumb_extension = 'png'

    if os.path.isfile(thumb_path):
        verb = 'Used existing'
        retcode = 0

    if os.path.isfile(thumb_path[:-4]+'.gif'):
        verb = 'Used existing'
        retcode = 0
        thumb_path = thumb_path[:-4] +'.gif'
        thumb_extension = 'gif'

    # Try download
    if download and retcode:
        try:
            thumb_req = requests.get(thumb_url)
        except Exception:
            thumb_req = requests.get(thumb_url, verify=False)

        verb = 'Successfully downloaded'
        if thumb_req.ok:
            verb = 'Successfully downloaded'
            retcode = 0
        else:
            try:
                thumb_req = requests.get(thumb_url[:-4]+'.gif')
            except Exception:
                thumb_req = requests.get(thumb_url[:-4]+'.gif', verify=False)
            if thumb_req.ok:
                thumb_extension = 'gif'
                thumb_path = thumb_path[:-4]+'.gif'
                retcode = 0
        if not retcode:
            with open(thumb_path, 'wb') as thumb_f:
                thumb_f.write(thumb_req.content)

    if retcode and no_image_thumb:
        shutil.copy2(NO_IMAGE_THUMB, thumb_path)
        retcode = 0
    return thumb_extension, extension, basename, retcode, verb


def generate_gallery_rst(app):
    """Generate the Main examples gallery reStructuredText
    Start the sphinx-gallery configuration and recursively scan the examples
    directories in order to populate the examples gallery
    """
    logger.info('generating gallery...', color='white')
    gallery_conf = dict(DEFAULT_GALLERY_CONF, **app.config.nbsite_gallery_conf)

    # this assures I can call the config in other places
    app.config.nbsite_gallery_conf = gallery_conf

    for gallery in sorted(gallery_conf['galleries']):
        generate_gallery(app, gallery)
