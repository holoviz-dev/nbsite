from pathlib import Path

from docutils import nodes
from docutils.parsers.rst import directives, Directive
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader

HERE = Path(__file__).parent


def get_env():
    ''' Get the correct Jinja2 Environment, also for frozen scripts.
    '''
    return Environment(loader=FileSystemLoader(HERE))

_env = get_env()
_env.trim_blocks = True
_env.lstrip_blocks = True

WEB_WORKER_TEMPLATE = _env.get_template('pyodideWorker.js')
WORKER_SETUP_TEMPLATE = _env.get_template('workerSetup.js')

DEFAULT_PYODIDE_CONF = {
    'PYODIDE_URL': 'https://cdn.jsdelivr.net/pyodide/v0.21.2/full/pyodide.js',
    'requirements': [
        'panel==0.14.0a11',
        'pandas',
        'matplotlib'
    ],
    'scripts': [
        'https://cdn.bokeh.org/bokeh/release/bokeh-2.4.3.min.js',
        'https://cdn.bokeh.org/bokeh/release/bokeh-widgets-2.4.3.min.js',
        'https://cdn.bokeh.org/bokeh/release/bokeh-tables-2.4.3.min.js',
        'https://unpkg.com/@holoviz/panel@0.14.0-a.4/dist/panel.min.js'
    ]
}

def write_worker(app, exc):
    if app.builder.format != 'html' or exc:
        return
    pyodide_conf = app.config.nbsite_pyodide_conf
    web_worker = WEB_WORKER_TEMPLATE.render({
        'PYODIDE_URL': pyodide_conf['PYODIDE_URL'],
        'env_spec': ', '.join([repr(req) for req in pyodide_conf['requirements']])
    })
    staticdir = Path(app.builder.outdir) / '_static'
    with open(staticdir/ 'webWorker.js', 'w') as f:
        f.write(web_worker)
    worker_setup = WORKER_SETUP_TEMPLATE.render(
        scripts=pyodide_conf['scripts']
    )
    with open(staticdir/ 'workerSetup.js', 'w') as f:
        f.write(worker_setup)
    return

def init_conf(app):
    pyodide_conf = dict(DEFAULT_PYODIDE_CONF, **app.config.nbsite_pyodide_conf)
    app.config.nbsite_pyodide_conf = pyodide_conf
    app.config.html_static_path.append(
        str((HERE /'_static' ).absolute())
    )

def setup(app):
    """Setup sphinx-gallery sphinx extension"""
    app.add_config_value('nbsite_pyodide_conf', DEFAULT_PYODIDE_CONF, 'html')

    app.connect('builder-inited', init_conf)
    app.connect('build-finished', write_worker)

    app.add_js_file('workerSetup.js')
    app.add_css_file("runbutton.css")
    app.add_js_file("run_cell.js")

    return {
        'version': '0.5',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
