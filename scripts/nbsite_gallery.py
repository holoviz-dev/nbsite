#!/usr/bin/env python

import sys
import os
import glob
import shutil
import requests
from nbsite.thumbnailer import notebook_thumbnail, execute

# Try Python 3 first, otherwise load from Python 2
try:
    from html import escape
except ImportError:
    from functools import partial
    from xml.sax.saxutils import escape
    escape = partial(escape, entities={'"': '&quot;'})

THUMBNAIL_URL = 'http://assets.holoviews.org'

# CONFIGURATION
gallery_conf = {
    'Gallery':   {'Apps': 'apps', 'Notebooks': 'notebooks'},
#    'Reference': {'Apps': 'apps', 'Containers': 'containers',
#                  'Elements': 'elements',
#                  'Streams': {'path': 'streams', 'skip': True}}
}
backends = ['bokeh', 'matplotlib', 'plotly']

PREFIX = """
# -*- coding: utf-8 -*-
import holoviews
from holoviews.plotting.widgets import NdWidget
from holoviews.plotting.comms import Comm

try:
    import holoviews.plotting.mpl
    holoviews.Store.renderers['matplotlib'].comms['default'] = (Comm, '')
except:
    pass

try:
    import holoviews.plotting.bokeh
    holoviews.Store.renderers['bokeh'].comms['default'] = (Comm, '')
except:
    pass

NdWidget.export_json=True
NdWidget.json_load_path = '/json'
NdWidget.json_save_path = './'

holoviews.plotting.mpl.MPLPlot.fig_alpha = 0
holoviews.plotting.bokeh.callbacks.Callback._comm_type = Comm
"""

THUMBNAIL_TEMPLATE = """
.. raw:: html

    <div class="sphx-glr-thumbcontainer {backend}_example" tooltip="{snippet}">

.. figure:: /{thumbnail}

    :ref:`{ref_name} <{backend}_gallery_{ref_name}>`

.. raw:: html

    </div>

"""

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

skip_execute_nbs = ['DynamicMap.ipynb']

def generate_file_rst(src_dir, backend, skip):
    files = (glob.glob(os.path.join(src_dir, '*.ipynb'))+
             glob.glob(os.path.join(src_dir, '*.py')))
    for f in files:
        extension = f.split('.')[-1]
        basename = os.path.basename(f)
        rst_path = f[:-len(extension)].replace(' ', '_') + 'rst'
        title = basename[:-(len(extension)+1)].replace('_', ' ').capitalize()
        if os.path.isfile(rst_path):
            continue
        with open(rst_path, 'w') as rst_file:
            rst_file.write('.. _%s_gallery_%s:\n\n' % (backend, basename[:-(len(extension)+1)]))
            rst_file.write(title+'\n')
            rst_file.write('_'*len(title)+'\n\n')
            if extension == 'ipynb':
                ftype = 'notebook'
                rst_file.write(".. notebook:: %s %s" % ('holoviews', basename))
                if skip or any(basename.strip().endswith(skipped) for skipped in skip_execute_nbs):
                    rst_file.write('\n    :skip_execute: True\n')
            else:
                ftype = 'script'
                rst_file.write('.. literalinclude:: %s\n\n' % basename)
                url = 'http://assets.holoviews.org/gifs/%s/%s.gif' % (src_dir[2:], basename[:-3])
                rst_file.write('.. figure:: %s\n\n' % url)
            rst_file.write('\n\n-------\n\n')
            rst_file.write('`Download this %s from GitHub (right-click to download).'
                           ' <https://raw.githubusercontent.com/ioam/holoviews/master/examples/%s/%s>`_'
                           % (ftype, src_dir[2:], basename))


def _thumbnail_div(full_dir, fname, snippet, backend, extension):
    """Generates RST to place a thumbnail in a gallery"""
    thumb = os.path.join(full_dir, 'thumbnails',
                         '%s.%s' % (fname, extension))

    # Inside rst files forward slash defines paths
    thumb = thumb.replace(os.sep, "/")
    template = THUMBNAIL_TEMPLATE
    return template.format(snippet=escape(snippet), backend=backend,
                           thumbnail=thumb[2:], ref_name=fname)


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

INTRO_PARAGRAPH = {'Reference': REFERENCE_INTRO, 'Gallery': GALLERY_INTRO}

def generate_gallery(basepath, title, folders):
    """
    Generates a gallery for all example directories specified in
    the gallery_conf. Generates rst files for all found notebooks
    and copies the notebooks to doc/gallery/ relative to the supplied
    basepath. Also generates thumbnails and an overall index.
    """
    #title = 'Reference Guide' if title=='Reference' else title
    gallery_rst = title + '\n' + '_'*len(title)
    gallery_rst += '\n' + INTRO_PARAGRAPH[title]

    buttons = []
    for n, backend in enumerate(backends):
        buttons.append(BUTTON_TEMPLATE.format(N=n+1, checked='' if n else 'checked="checked"',
                                              label=backend.capitalize()))

    gallery_rst += BUTTON_GROUP_TEMPLATE.format(buttons=''.join(buttons), backends=backends)

    page = title.lower()
    for heading, folder in sorted(folders.items()):
        if isinstance(folder, dict):
            skip = folder.get('skip', False)
            folder = folder['path']
        else:
            skip = False
        gallery_rst += heading + '\n' + '='*len(heading) + '\n\n'
        asset_dir = os.path.join(basepath, 'examples', page, folder, 'assets')
        asset_dest = os.path.join('.', page, folder, 'assets')
        if os.path.isdir(asset_dir) and not os.path.isdir(asset_dest):
            shutil.copytree(asset_dir, asset_dest)
        for backend in backends:
            path = os.path.join(basepath, 'examples', page, folder, backend)
            dest_dir = os.path.join('.', page, folder, backend)
            try:
                os.makedirs(dest_dir)
            except:
                pass
            notebooks = glob.glob(path+'/*.ipynb') + glob.glob(path+'/*.py')
            if notebooks:
                print("\n\nGenerating %d %s %s examples for %s backend\n"
                      "__________________________________________________"
                      % (len(notebooks), heading, title, backend))
            for f in notebooks:
                # Get ipynb file and copy it to doc
                extension = f.split('.')[-1]
                basename = os.path.basename(f)[:-(len(extension)+1)]
                ftitle = basename.replace('_', ' ').capitalize()
                dest = os.path.join(dest_dir, os.path.basename(f))

                shutil.copyfile(f, dest)
                # Try to fetch thumbnail otherwise regenerate it
                thumb_url = '/'.join([THUMBNAIL_URL, 'thumbnails', page, folder,
                                      backend, '%s.png' % basename])
                thumb = os.path.join(dest_dir, 'thumbnails',
                                     '%s.png' % basename)
                thumb_req = requests.get(thumb_url)
                thumb_req2 = requests.get(thumb_url[:-4]+'.gif')
                if os.path.isfile(thumb):
                    thumb_extension = 'png'
                    verb = 'Used existing'
                    retcode = 0
                elif False and thumb_req.status_code == 200:
                    thumb_extension = 'png'
                    verb = 'Successfully downloaded'
                    thumb_dir = os.path.dirname(thumb)
                    if not os.path.isdir(thumb_dir):
                        os.makedirs(thumb_dir)
                    with open(thumb, 'wb') as thumb_f:
                        thumb_f.write(thumb_req.content)
                    retcode = 0
                elif False and thumb_req2.status_code == 200:
                    thumb_extension = 'gif'
                    verb = 'Successfully downloaded'
                    thumb_dir = os.path.dirname(thumb)
                    if not os.path.isdir(thumb_dir):
                        os.makedirs(thumb_dir)
                    with open(thumb[:-4]+'.gif', 'wb') as thumb_f:
                        thumb_f.write(thumb_req2.content)
                    retcode = 0
                elif extension == 'ipynb':
                    thumb_extension = 'png'
                    verb = 'Successfully generated'
                    code = notebook_thumbnail(f, os.path.join(page, folder, backend))
                    code = PREFIX + code
                    my_env = os.environ.copy()
                    retcode = execute(code.encode('utf8'), env=my_env, cwd=os.path.split(f)[0])
                else:
                    retcode = 1
                if retcode:
                    print('%s thumbnail export failed' % basename)
                    if extension == 'py':
                        continue
                    this_entry = THUMBNAIL_TEMPLATE.format(
                        snippet=escape(ftitle), backend=backend,
                        thumbnail='../_static/images/logo.png',
                        ref_name=basename)
                else:
                    print('%s %s thumbnail' % (verb, basename))
                    this_entry = _thumbnail_div(dest_dir, basename, ftitle,
                                                backend, thumb_extension)
                gallery_rst += this_entry
            generate_file_rst(dest_dir, backend, skip)
        # clear at the end of the section
        gallery_rst += """.. raw:: html\n\n
        <div style='clear:both'></div>\n\n"""
    gallery_rst += HIDE_JS.format(backends=repr(backends[1:]))
    with open(os.path.join(basepath, 'doc', page, 'index.rst'), 'w') as f:
        f.write(gallery_rst)


if __name__ == '__main__':
    basepath = os.path.abspath(sys.argv[1])
    for title, folders in sorted(gallery_conf.items()):
        generate_gallery(basepath, title, folders)
