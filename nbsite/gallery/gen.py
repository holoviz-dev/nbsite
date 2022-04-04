import os
import glob
import logging

import requests
import sphinx.util

try:
    import bs4
except:
    bs4 = None

from .thumbnailer import notebook_thumbnail, execute

logger = sphinx.util.logging.getLogger('nbsite-gallery')
logging.getLogger(requests.packages.urllib3.__package__).setLevel(logging.ERROR)

BUTTON_GROUP_TEMPLATE = """
.. raw:: html

    <script>
    function gallery_toggle(input) {{
        backends = {backends};
        for (i in backends) {{
            entries = $('.'+backends[i]+'_example');
            if (backends[i] == input) {{
                entries.show();
            }} else {{
                entries.hide()
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
        $(document).ready(function () {{
            backends = {backends};
            for (var i=0; i<backends.length; i++){{
                $('.'+backends[i]+'_example').hide();
            }}
        }});
    </script>
"""

CLEAR_DIV = """
.. raw:: html

    <div style='clear:both'></div>

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

THUMBNAIL_TEMPLATE = """
.. raw:: html

    <div class="sphx-glr-thumbcontainer {backend}example" tooltip="{label}">

.. figure:: /{thumbnail}

    :ref:`{label} <{prefix}gallery_{ref_name}>`

.. raw:: html

    </div>

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

INLINE_GALLERY_STYLE = """

.. raw:: html

   <style>
     .sphx-glr-section {
       display: inline-block;
       vertical-align: top;
       padding-right: 20px;
     }
   </style>

"""

DEFAULT_GALLERY_CONF = {
    'backends': None,
    'default_extensions': ['*.ipynb', '*.py'],
    'enable_download': True,
    'only_use_existing': False,
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
    'within_subsection_order': lambda key: key,
    'nblink': 'both',  # use this to control the position of the nblink
    'github_ref': 'master',  # branch or tag
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

def generate_file_rst(app, src_dir, dest_dir, page, section, backend,
                      img_extension, skip, deployment_urls):
    gallery_conf = app.config.nbsite_gallery_conf
    content = gallery_conf['galleries'][page]
    host = gallery_conf['host']
    download_as = gallery_conf['download_as']
    ref = gallery_conf['github_ref']
    nblink = gallery_conf['nblink']
    org = gallery_conf['github_org']
    proj = gallery_conf['github_project']
    examples_dir = gallery_conf['examples_dir']
    skip_execute = gallery_conf['skip_execute']
    endpoint = gallery_conf['deployment_url']
    iframe_spinner = gallery_conf['iframe_spinner']
    extensions = content.get('extensions', gallery_conf['default_extensions'])

    components = [examples_dir.split(os.path.sep)[-1], page]
    if section:
        components.append(section)
    if backend:
        components.append(backend)

    files = []
    for extension in extensions:
        files += glob.glob(os.path.join(src_dir, extension))

    # Try to fetch all deployed examples
    deployed_examples = []
    if bs4 and endpoint is not None:
        r = requests.get(endpoint, verify=False)
        if r.status_code == 200:
            soup = bs4.BeautifulSoup(r.content, features='lxml')
            try:
                deployed_examples = [l.text for l in soup.find('div', {"class": "list-group"}).find_all('h4')]
            except:
                deployed_examples = [l.get('id')[1:] for l in soup.find('ul', {"class": "cards-grid"}).find_all('a', {"class": "card-link"})]
            if not deployed_examples:
                deployed_examples = [l.text for l in soup.find('ul').find_all('a')]

    for f in files:
        if isinstance(skip, list) and os.path.basename(f) in skip:
            continue
        extension = f.split('.')[-1]
        basename = os.path.basename(f)
        rel_path = os.path.relpath(os.path.join(src_dir, basename), dest_dir)
        rst_path = os.path.join(dest_dir, basename[:-len(extension)].replace(' ', '_') + 'rst')
        name = basename[:-(len(extension)+1)]
        title = ' '.join([n[0].capitalize()+n[1:] for n in name.replace('_', ' ').split(' ')])
        deployed = name in deployed_examples
        ftype = 'notebook' if extension == 'ipynb' else 'script'

        if os.path.isfile(rst_path):
            with open(rst_path) as existing:
                if not 'Originally generated by nbsite' in existing.read():
                    continue

        with open(rst_path, 'w') as rst_file:
            prefix = '_'.join([p for p in (section, backend, 'gallery') if p])
            rst_file.write('.. _%s_%s:\n\n' % (prefix, name))
            rst_file.write(title+'\n')
            rst_file.write('_'*len(title)+'\n\n')

            deployed_file = get_deployed_url(deployment_urls, basename)
            if nblink in ['top', 'both']:
                add_nblink(rst_file, host, deployed_file, download_as,
                           org, proj, ref, components, basename, ftype, section)
                rst_file.write('\n\n-------\n\n')

            if ftype == 'notebook':
                rst_file.write(".. notebook:: %s %s" % (proj, rel_path))
                if deployed or (isinstance(skip, bool) and skip) or any(basename.strip().endswith(skipped) for skipped in skip_execute):
                    rst_file.write('\n    :skip_execute: True\n')
                if deployed:
                    rst_file.write(IFRAME_TEMPLATE.format(
                        background=iframe_spinner, url=endpoint+name))
            else:
                rst_file.write('.. literalinclude:: %s\n\n' % rel_path)
                url = os.path.join('thumbnails', '%s.%s' % (name, img_extension))
                rst_file.write('.. figure:: %s\n\n' % url)

            if nblink in ['bottom', 'both']:
                rst_file.write('\n\n-------\n\n')
                add_nblink(rst_file, host, deployed_file, download_as,
                           org, proj, ref, components, basename, ftype, section)

def add_nblink(rst_file, host, deployed_file, download_as,
               org, proj, ref, components, basename, ftype, section):
    if deployed_file:
        rst_file.write(f'`View a running version of this notebook. <{deployed_file}>`_ | ')
    if host == 'GitHub' and org and proj:
        rst_file.write('`Download this {ftype} from GitHub (right-click to download).'
                        ' <https://raw.githubusercontent.com/{org}/{proj}/{ref}/{path}/{basename}>`_'.format(
                            org=org, proj=proj, ref=ref, path='/'.join(components),
                            basename=basename, ftype=ftype))
    elif host == 'assets':
        if download_as == 'project':
            rst_file.write(f'`Download this project. </assets/{section}.zip>`_')
        else:
            rst_file.write('`Download this {ftype}. </assets/{path}/{basename}>`_'.format(
                                path='/'.join(components), basename=basename, ftype=ftype))


def _thumbnail_div(path_components, section, backend, fname, extension):
    """Generates RST to place a thumbnail in a gallery"""
    label = fname.replace('_', ' ').title()
    thumb = os.path.join(*path_components+['thumbnails', '%s.%s' % (fname, extension)])

    # Inside rst files forward slash defines paths
    thumb = thumb.replace(os.sep, "/")
    prefix = '_'.join([pre for pre in (section, backend) if pre])
    backend = backend+'_' if backend else ''
    if prefix:
        prefix += '_'

    return THUMBNAIL_TEMPLATE.format(
        backend=backend, prefix=prefix, thumbnail=thumb, ref_name=fname,
        label=label)


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
    thumbnail_url = gallery_conf['thumbnail_url']
    download = gallery_conf['enable_download']
    script_prefix = gallery_conf['script_prefix']
    only_use_existing = gallery_conf['only_use_existing']
    inline = gallery_conf['inline']

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

    if inline:
        gallery_rst += INLINE_GALLERY_STYLE

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

        if not heading:
            gallery_rst += '\n\n.. raw:: html\n\n    <div class="section sphx-glr-section" id="section"></div><br>\n\n'
        elif inline:
            gallery_rst += f'\n\n.. toctree::\n   :glob:\n   :hidden:\n   :maxdepth: 2\n\n   {section}/*'
        else:
            underline = '-'*len(heading)
            gallery_rst += f'\n\n{heading}\n{underline}\n\n'

        if section:
            gallery_rst += f'\n\n.. toctree::\n   :glob:\n   :hidden:\n\n   {heading}\n   {section}/*\n\n'
        else:
            gallery_rst += f'\n\n.. toctree::\n   :glob:\n   :hidden:\n\n   {heading}\n   *\n\n'

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

        thumb_extension = 'png'
        for backend in (section_backends or ('',)):
            path_components = [page]
            if section:
                path_components.append(section)
            if backend:
                path_components.append(backend)

            path = os.path.join(examples_dir, *path_components)
            dest_dir = os.path.join(doc_dir, *path_components)
            try:
                os.makedirs(dest_dir)
            except:
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

            for f in sorted(files, key=subsection_order):
                extension = f.split('.')[-1]
                basename = os.path.basename(f)[:-(len(extension)+1)]

                # Try to fetch thumbnail otherwise regenerate it
                url_components = [thumbnail_url, page]

                if section:
                    url_components.append(section)
                if backend:
                    url_components.append(backend)
                url_components.append('%s.png' % basename)

                # if there is a . in the path, just get rid of it
                thumb_url = '/'.join(url_components).replace('/./', '/')

                thumb_dir = os.path.join(dest_dir, 'thumbnails')
                if not os.path.isdir(thumb_dir):
                    os.makedirs(thumb_dir)
                thumb_path = os.path.join(thumb_dir, '%s.png' % basename)

                # Try existing file
                retcode = 1
                thumb_extension = 'png'

                if os.path.isfile(thumb_path):
                    verb = 'Used existing'
                    retcode = 0

                # Try download
                if download and retcode:
                    thumb_req = requests.get(thumb_url, verify=False)
                    verb = 'Successfully downloaded'
                    if thumb_req.status_code == 200:
                        verb = 'Successfully downloaded'
                        retcode = 0
                    else:
                        thumb_req = requests.get(thumb_url[:-4]+'.gif', verify=False)
                        if thumb_req.status_code == 200:
                            thumb_extension = 'gif'
                            thumb_path = thumb_path[:-4]+'.gif'
                            retcode = 0
                    if not retcode:
                        with open(thumb_path, 'wb') as thumb_f:
                            thumb_f.write(thumb_req.content)

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
                    backend_str = backend+'_' if backend else '' 
                    if thumb_prefix:
                        thumb_prefix += '_'
                    this_entry = THUMBNAIL_TEMPLATE.format(
                        backend=backend_str, prefix=thumb_prefix, thumbnail=logo_path,
                        ref_name=basename, label=basename.replace('_', ' ').title())
                else:
                    logger.info('%s %s thumbnail' % (verb, basename))
                    this_entry = _thumbnail_div(
                        path_components, section, backend, basename, thumb_extension
                    )

                gallery_rst += this_entry
            generate_file_rst(app, path, dest_dir, page, section,
                              backend, thumb_extension, skip, deployment_urls)
        # clear at the end of the section
        gallery_rst += CLEAR_DIV

    if backends or section_backends:
        gallery_rst += HIDE_JS.format(backends=repr(backends[1:]))
    with open(os.path.join(doc_dir, page, 'index.rst'), 'w') as f:
        f.write(gallery_rst)


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
