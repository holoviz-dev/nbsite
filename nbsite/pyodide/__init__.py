from pathlib import Path
from typing import Any, Dict, List

from docutils import nodes
from docutils.parsers.rst import directives, Directive, roles
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from sphinx.application import Sphinx


HERE = Path(__file__).parent

def get_env() -> Environment:
    ''' Get the correct Jinja2 Environment, also for frozen scripts.
    '''
    return Environment(loader=FileSystemLoader(HERE))

_env = get_env()
_env.trim_blocks = True
_env.lstrip_blocks = True

WEB_WORKER_TEMPLATE = _env.get_template('WebWorker.js')
WORKER_HANDLER_TEMPLATE = _env.get_template('WorkerHandler.js')
SERVICE_WORKER_TEMPLATE = _env.get_template('ServiceWorker.js')
SERVICE_HANDLER_TEMPLATE = _env.get_template('ServiceHandler.js')
WEB_MANIFEST_TEMPLATE = _env.get_template('site.webmanifest')

DEFAULT_PYODIDE_CONF = {
    'PYODIDE_URL': 'https://cdn.jsdelivr.net/pyodide/v0.21.2/full/pyodide.js',
    'autodetect_deps': True,
    'enable_pwa': True,
    'requirements': [
        'panel==0.14.0a11',
        'pandas',
        'matplotlib'
    ],
    'scripts': [
        'https://cdn.bokeh.org/bokeh/release/bokeh-2.4.3.min.js',
        'https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.4.3.min.js',
        'https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.4.3.min.js',
        'https://unpkg.com/@holoviz/panel@0.14.0-a.11/dist/panel.min.js'
    ],
    'cache_patterns': [
        'https://cdn.bokeh.org/bokeh/',
        'https://unpkg.com/@holoviz/',
        'https://cdn.jsdelivr.net/pyodide/',
        'https://files.pythonhosted.org/packages/',
        'https://pypi.org/pypi/'
    ],
    'setup_code': ""
}

class PyodideDirective(Directive):

    has_content = True

    def run(self):
        classes = 'pyodide'
        if 'class' in self.options:
            classes += f" {self.options['class']}"

        self.options['class'] = [classes]
        roles.set_classes(self.options)
        text = '\n'.join(self.content)
        doctree_node = nodes.literal_block(text, text, **self.options)
        doctree_node['language'] = 'python'
        return [doctree_node]

def write_worker(app: Sphinx, exc):
    if app.builder.format != 'html' or exc:
        return
    pyodide_conf = app.config.nbsite_pyodide_conf
    builddir = Path(app.builder.outdir)
    staticdir = builddir / '_static'

    # Render Web Worker
    web_worker = WEB_WORKER_TEMPLATE.render({
        'PYODIDE_URL': pyodide_conf['PYODIDE_URL'],
        'env_spec': ', '.join([repr(req) for req in pyodide_conf['requirements']]),
        'setup_code': pyodide_conf['setup_code'],
        'autodetect_deps': pyodide_conf['autodetect_deps']
    })
    with open(staticdir/ 'PyodideWebWorker.js', 'w') as f:
        f.write(web_worker)
    worker_setup = WORKER_HANDLER_TEMPLATE.render(
        scripts=pyodide_conf['scripts']
    )
    with open(staticdir/ 'WorkerHandler.js', 'w') as f:
        f.write(worker_setup)

    if not pyodide_conf['enable_pwa']:
        return

    # Render service worker
    service_worker = SERVICE_WORKER_TEMPLATE.render({
        'name': app.config.html_title,
        'pre_cache': ', '.join([repr(req) for req in pyodide_conf['scripts']]),
        'cache_patterns': ', '.join([repr(req) for req in pyodide_conf['cache_patterns']])
    })
    with open(builddir / 'PyodideServiceWorker.js', 'w') as f:
        f.write(service_worker)
    service_handler = SERVICE_HANDLER_TEMPLATE.render()
    with open(staticdir/ 'ServiceHandler.js', 'w') as f:
        f.write(service_handler)

    # Render manifest
    site_manifest = WEB_MANIFEST_TEMPLATE.render({
        'name': app.config.html_title,
    })
    with open(builddir / 'site.webmanifest', 'w') as f:
        f.write(site_manifest)

def init_conf(app: Sphinx) -> None:
    pyodide_conf = dict(DEFAULT_PYODIDE_CONF, **app.config.nbsite_pyodide_conf)
    app.config.nbsite_pyodide_conf = pyodide_conf
    app.config.html_static_path.append(
        str((HERE /'_static' ).absolute())
    )
    app.add_css_file('runbutton.css')
    app.add_js_file('run_cell.js')
    app.add_js_file('WorkerHandler.js')
    if pyodide_conf['enable_pwa']:
        app.add_js_file('ServiceHandler.js')

def html_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: Dict[str, Any],
    doctree: nodes.document,
) -> None:

    if doctree and app.config.nbsite_pyodide_conf['enable_pwa']:
        relpath = '/'.join(['..']*pagename.count('/'))
        if relpath:
            relpath += '/'
        context[
            "metatags"
        ] += f"""
            <link rel="manifest" href="{relpath}site.webmanifest"/>
            """

def setup(app):
    """Setup sphinx-gallery sphinx extension"""
    app.add_config_value('nbsite_pyodide_conf', DEFAULT_PYODIDE_CONF, 'html')

    app.connect('builder-inited', init_conf)
    app.connect('build-finished', write_worker)
    app.connect('html-page-context', html_page_context)

    app.add_directive('pyodide', PyodideDirective)


    return {
        'version': '0.5',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
