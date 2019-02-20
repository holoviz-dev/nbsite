import os
import glob
import logging

import requests
import sphinx.util

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

    <div class="sphx-glr-thumbcontainer {backend}_example" tooltip="{label}">

.. figure:: /{thumbnail}

    :ref:`{ref_name} <{backend}_gallery_{ref_name}>`

.. raw:: html

    </div>

"""

DEFAULT_GALLERY_CONF = {
    'backends': None,
    'default_extensions': ['*.ipynb', '*.py'],
    'enable_download': True,
    'examples_dir': os.path.join('..', 'examples'),
    'galleries': {
        'gallery': {
            'backends': [],
            'extensions': ['*.ipynb', '*.py'],
            'intro': 'Sample intro',
            'title': 'A sample gallery title',
            'sections': [],
        }
    },
    'github_org': None,
    'github_project': None,
    'script_prefix': PREFIX,
    'skip_execute': [],
    'thumbnail_url': THUMBNAIL_URL,
    'thumbnail_size': (400, 280),
    'within_subsection_order': lambda key: key,
}


def generate_file_rst(app, src_dir, dest_dir, page, section, backend, img_extension, skip):
    gallery_conf = app.config.nbsite_gallery_conf
    content = gallery_conf['galleries'][page]
    org = gallery_conf['github_org']
    proj = gallery_conf['github_project']
    examples_dir = gallery_conf['examples_dir']
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
                rst_file.write('.. literalinclude:: %s\n\n' % rel_path)
                url = os.path.join('thumbnails', '%s.%s' % (basename[:-(len(extension)+1)], img_extension))
                rst_file.write('.. figure:: %s\n\n' % url)
            rst_file.write('\n\n-------\n\n')
            if org and proj:
                rst_file.write('`Download this {ftype} from GitHub (right-click to download).'
                               ' <https://raw.githubusercontent.com/{org}/{proj}/master/{path}/{basename}>`_'.format(
                                   org=org, proj=proj, path='/'.join(components),
                                   basename=basename, ftype=ftype))


def _thumbnail_div(path_components, backend, fname, extension):
    """Generates RST to place a thumbnail in a gallery"""
    label = fname.replace('_', ' ').title()
    thumb = os.path.join(*path_components+['thumbnails', '%s.%s' % (fname, extension)])

    # Inside rst files forward slash defines paths
    thumb = thumb.replace(os.sep, "/")

    return THUMBNAIL_TEMPLATE.format(
        backend=backend, thumbnail=thumb, ref_name=fname, label=label)


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

    # Write gallery index
    title = content['title']
    gallery_rst = title + '\n' + '_'*len(title) + '\n'
    if 'intro' in content:
        gallery_rst += '\n' + content['intro']

    if backends:
        buttons = []
        for n, backend in enumerate(backends):
            buttons.append(BUTTON_TEMPLATE.format(N=n+1, checked='' if n else 'checked="checked"',
                                                  label=backend.capitalize()))
        gallery_rst += BUTTON_GROUP_TEMPLATE.format(buttons=''.join(buttons), backends=backends)

    for section in sections:
        if isinstance(section, dict):
            section_backends = section.get('backends', backends)
            skip = section.get('skip', content.get('skip', False))
            heading = section.get('title', section['path'])
            subsection_order = section.get('within_subsection_order', sort_fn)
            section = section['path']
        else:
            heading = section.title()
            skip = content.get('skip', False)
            section_backends = backends
            subsection_order = sort_fn

        if heading:
            gallery_rst += heading + '\n' + '='*len(heading) + '\n\n'
        else:
            gallery_rst += '\n\n.. raw:: html\n\n    <div class="section"></div><br>\n\n'

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

            if files:
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
                thumb_url = '/'.join(url_components)

                thumb_dir = os.path.join(dest_dir, 'thumbnails')
                if not os.path.isdir(thumb_dir):
                    os.makedirs(thumb_dir)
                thumb_path = os.path.join(thumb_dir, '%s.png' % basename)

                # Try existing file
                retcode = 1
                if os.path.isfile(thumb_path):
                    thumb_extension = 'png'
                    verb = 'Used existing'
                    retcode = 0

                # Try download
                if download and retcode:
                    thumb_req = requests.get(thumb_url)
                    verb = 'Successfully downloaded'
                    if thumb_req.status_code == 200:
                        thumb_extension = 'png'
                        verb = 'Successfully downloaded'
                        retcode = 0
                    else:
                        thumb_req = requests.get(thumb_url[:-4]+'.gif')
                        if thumb_req.status_code == 200:
                            thumb_extension = 'gif'
                            thumb_path = thumb_path[:-4]+'.gif'
                            retcode = 0
                    if not retcode:
                        with open(thumb_path, 'wb') as thumb_f:
                            thumb_f.write(thumb_req.content)

                # Generate thumbnail
                if not retcode:
                    pass
                elif extension == 'ipynb':
                    thumb_extension = 'png'
                    verb = 'Successfully generated'
                    code = notebook_thumbnail(f, os.path.join(*(['doc']+path_components)))
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
                        backend=backend, thumbnail='../_static/images/logo.png',
                        ref_name=basename, label=basename.replace('_', ' ').title())
                else:
                    logger.info('%s %s thumbnail' % (verb, basename))
                    this_entry = _thumbnail_div(path_components, backend,
                                                basename, thumb_extension)

                gallery_rst += this_entry
            generate_file_rst(app, path, dest_dir, page, section,
                              backend, thumb_extension, skip)
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
