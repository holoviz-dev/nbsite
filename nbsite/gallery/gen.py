import sys
import os
import glob
import shutil
import requests

from distutils.version import LooseVersion

import sphinx

from .thumbnailer import notebook_thumbnail, execute

# Try Python 3 first, otherwise load from Python 2
try:
    from html import escape
except ImportError:
    from functools import partial
    from xml.sax.saxutils import escape
    escape = partial(escape, entities={'"': '&quot;'})

if LooseVersion(sphinx.__version__) >= '1.6':
    getLogger = sphinx.util.logging.getLogger
    status_iterator = sphinx.util.status_iterator
else:
    getLogger = _app_get_logger
    status_iterator = _app_status_iterator

logger = getLogger('nbsite-gallery')

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

THUMBNAIL_URL = 'http://assets.holoviews.org/thumbnails'

PREFIX = """
# -*- coding: utf-8 -*-
import holoviews as hv
from holoviews.plotting.widgets import NdWidget
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

NdWidget.export_json=True
NdWidget.json_load_path = '/json'
NdWidget.json_save_path = './'

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

    <div class="sphx-glr-thumbcontainer {backend}_example" tooltip="{snippet}">

.. figure:: /{thumbnail}

    :ref:`{ref_name} <_{backend}_gallery_{ref_name}>`

.. raw:: html

    </div>

"""

DEFAULT_GALLERY_CONF = {
    'galleries': {
        'gallery': {
            'backends': [],
            'extensions': ['*.ipynb', '*.py'],
            'intro': 'Sample intro',
            'title': 'A sample gallery title',
            'sections': [],
        }
    },
    'skip_execute': [],
    'examples_dir': os.path.join('..', 'examples'),
    'thumbnail_url': THUMBNAIL_URL,
    'within_subsection_order': lambda key: key,
    'script_prefix': PREFIX,
    'thumbnail_size': (400, 280),
    'default_extensions': ['*.ipynb', '*.py'],
    'enable_download': True,
    'github_org': None,
    'github_project': None
}


def generate_file_rst(app, src_dir, dest_dir, page, section, backend, skip):
    gallery_conf = app.config.nbsite_gallery_conf
    content = gallery_conf['galleries'][page]
    org = gallery_conf['github_org']
    proj = gallery_conf['github_project']
    examples_dir = gallery_conf['examples_dir']
    thumbnail_url = gallery_conf['thumbnail_url']
    skip_execute = gallery_conf['skip_execute']
    extensions = content.get('extensions', gallery_conf['default_extensions'])

    components = [examples_dir.split(os.path.sep)[-1], page]
    if section:
        components.append(section)
    if backend:
        components.append(backend)

    files = []
    for extension in extensions:
        files += glob.glob(os.path.join(src_dir, extension))

    for f in files:
        extension = f.split('.')[-1]
        basename = os.path.basename(f)
        rel_path = os.path.relpath(os.path.join(src_dir, basename), dest_dir)
        rst_path = os.path.join(dest_dir, basename[:-len(extension)].replace(' ', '_') + 'rst')
        title = basename[:-(len(extension)+1)].replace('_', ' ').capitalize()
        if os.path.isfile(rst_path):
            continue

        with open(rst_path, 'w') as rst_file:
            rst_file.write('.. _%s_%s:\n\n' % ('_'.join([backend, 'gallery']),
                                               basename[:-(len(extension)+1)]))
            rst_file.write(title+'\n')
            rst_file.write('_'*len(title)+'\n\n')
            if extension == 'ipynb':
                ftype = 'notebook'
                rst_file.write(".. notebook:: %s %s" % (proj, rel_path))
                if skip or any(basename.strip().endswith(skipped) for skipped in skip_execute):
                    rst_file.write('\n    :skip_execute: True\n')
            else:
                ftype = 'script'
                rst_file.write('.. literalinclude:: %s\n\n' % basename)
                url = '%s/gifs/%s/%s.gif' % (thumbnail_url, src_dir[2:], basename[:-3])
                rst_file.write('.. figure:: %s\n\n' % url)
            rst_file.write('\n\n-------\n\n')
            if org and proj:
                rst_file.write('`Download this %s from GitHub (right-click to download).'
                               ' <https://raw.githubusercontent.com/{org}/{proj}/master/{path}/{basename}>`_'.format(
                                   org=org, proj=proj, path='/'.join(components), basename=basename))


def _thumbnail_div(full_dir, fname, snippet, backend, extension):
    """Generates RST to place a thumbnail in a gallery"""
    thumb = os.path.join(full_dir, 'thumbnails',
                         '%s.%s' % (fname, extension))

    # Inside rst files forward slash defines paths
    thumb = thumb.replace(os.sep, "/")
    template = THUMBNAIL_TEMPLATE
    return template.format(snippet=escape(snippet), backend=backend,
                           thumbnail=thumb[2:], ref_name=fname)


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
    
    # Get directories
    doc_dir = app.builder.srcdir
    examples_dir = os.path.join(doc_dir, gallery_conf['examples_dir'])
    gallery_dir = os.path.join(examples_dir, page)

    if 'sections' in content:
        sections = content['sections']
    else:
        sections = [s for s in glob.glob(os.path.join(gallery_dir, '*'))
                    if os.path.isdir(os.path.join(gallery_dir, s))]
        if not sections:
            sections = ['']

    backends = content.get('backends', None)
    extensions = content.get('extensions', gallery_conf['default_extensions'])
    sort_fn = gallery_conf['within_subsection_order']
    thumbnail_url = gallery_conf['thumbnail_url']
    download = gallery_conf['enable_download']
    script_prefix = gallery_conf['script_prefix']

    # Write gallery index
    title = content['title']
    gallery_rst = title + '\n' + '_'*len(title)
    if 'intro' in content:
        gallery_rst += '\n' + content['intro']

    if backends:
        buttons = []
        for n, backend in enumerate(backends):
            buttons.append(BUTTON_TEMPLATE.format(N=n+1, checked='' if n else 'checked="checked"',
                                                  label=backend.capitalize()))
        gallery_rst += BUTTON_GROUP_TEMPLATE.format(buttons=''.join(buttons), backends=backends)

    for section in sections:
        heading = section.title()
        if isinstance(section, dict):
            skip = section.get('skip', False)
            heading = section.get('title', heading)
            section = section['path']
        else:
            skip = False

        #asset_dir = os.path.join(basepath, examples, page, folder, 'assets')
        #asset_dest = os.path.join('.', page, folder, 'assets')
        #if os.path.isdir(asset_dir) and not os.path.isdir(asset_dest):
        #    shutil.copytree(asset_dir, asset_dest)

        if heading:
            gallery_rst += heading + '\n' + '='*len(heading) + '\n\n'

        for backend in (backends or ('',)):
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

            if files:
                if backend:
                    backend_str = ' for %s backend' % backend
                else:
                    backend_str = ''
                logger.info("\n\nGenerating %d %s %s examples%s\n"
                            "__________________________________________________"
                            % (len(files), heading, title, backend_str))

            for f in sorted(files, key=sort_fn):
                extension = f.split('.')[-1]
                basename = os.path.basename(f)[:-(len(extension)+1)]
                ftitle = basename.replace('_', ' ').capitalize()
                dest = os.path.join(dest_dir, os.path.basename(f))

                # Try to fetch thumbnail otherwise regenerate it
                url_components = [thumbnail_url, page]
                if section:
                    url_components.append(section)
                if backend:
                    url_components.append(backend)
                url_components.append('%s.png' % basename)
                thumb_url = '/'.join(url_components)

                if download:
                    thumb_req_png = requests.get(thumb_url)
                    if thumb_req_png.status_code == 200:
                        thumb_req_gif = requests.get(thumb_url[:-4]+'.gif')
                    else:
                        thumb_req_gif = None
                else:
                    thumb_req_png = None
                    thumb_req_gif = None

                thumb_dir = os.path.join(dest_dir, 'thumbnails')
                if not os.path.isdir(thumb_dir):
                    os.makedirs(thumb_dir)
                thumb_path = os.path.join(thumb_dir, '%s.png' % basename)

                if os.path.isfile(thumb_path):
                    thumb_extension = 'png'
                    verb = 'Used existing'
                    retcode = 0
                elif thumb_req_png and thumb_req_png.status_code == 200:
                    thumb_extension = 'png'
                    verb = 'Successfully downloaded'
                    with open(thumb_path, 'wb') as thumb_f:
                        thumb_f.write(thumb_req.content)
                    retcode = 0
                elif thumb_req_gif and thumb_req_gif.status_code == 200:
                    thumb_extension = 'gif'
                    verb = 'Successfully downloaded'
                    with open(thumb_path[:-4]+'.gif', 'wb') as thumb_f:
                        thumb_f.write(thumb_req_gif.content)
                    retcode = 0
                elif extension == 'ipynb':
                    thumb_extension = 'png'
                    verb = 'Successfully generated'
                    code = notebook_thumbnail(f, os.path.join(*path_components))
                    code = script_prefix + code
                    my_env = os.environ.copy()
                    retcode = execute(code.encode('utf8'), env=my_env, cwd=os.path.split(f)[0])
                else:
                    retcode = 1

                if retcode:
                    logger.info('%s thumbnail export failed' % basename)
                    if extension == 'py':
                        continue
                    this_entry = THUMBNAIL_TEMPLATE.format(
                        snippet=escape(ftitle), backend=backend,
                        thumbnail='../_static/images/logo.png',
                        ref_name=basename)
                else:
                    logger.info('%s %s thumbnail' % (verb, basename))
                    this_entry = _thumbnail_div(dest_dir, basename, ftitle,
                                                backend, thumb_extension)
                gallery_rst += this_entry
            generate_file_rst(app, path, dest_dir, page, section, backend, skip)
        # clear at the end of the section
        gallery_rst += CLEAR_DIV
    if backends:
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
