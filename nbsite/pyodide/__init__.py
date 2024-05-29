import io
import json
import sys
import warnings

from collections import defaultdict
from html import escape
from multiprocessing import Pipe, Process
from pathlib import Path
from typing import (
    Any, Dict, List, Tuple,
)

import param

from bokeh.document import Document
from bokeh.embed.bundle import _bundle_extensions
from bokeh.embed.util import standalone_docs_json_and_render_items
from bokeh.model import Model
from docutils import nodes
from docutils.parsers.rst import Directive, roles
from jinja2.environment import Environment
from jinja2.loaders import FileSystemLoader
from packaging.version import Version
from panel.config import config, panel_extension as extension
from panel.io.convert import BOKEH_VERSION
from panel.io.mime_render import exec_with_return, format_mime
from panel.io.resources import CDN_DIST, Resources, set_resource_mode
from panel.pane import HoloViews, Interactive, panel as as_panel
from panel.reactive import ReactiveHTML
from panel.viewable import Viewable, Viewer
from sphinx.application import Sphinx

HERE = Path(__file__).parent

CONVERT_PANE_TYPES = (HoloViews, Interactive)

try:
    from panel.param import ReactiveExpr
    CONVERT_PANE_TYPES += (ReactiveExpr,)
except Exception:
    pass

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

JS_MODULE_TAG = """
<script type="module" src="{file}"></script>"""
JS_MODULE_EXPORT = """
<script type="module">
  import {name} from "{file}";
  window.{name} = {name}
</script>
"""

bokeh_version = Version(BOKEH_VERSION)
if bokeh_version.is_devrelease or bokeh_version.is_prerelease:
    bk_prefix = 'dev'
else:
    bk_prefix = 'release'

DEFAULT_PYODIDE_CONF = {
    'PYODIDE_URL': 'https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js',
    'autodetect_deps': True,
    'enable_pwa': True,
    'requirements': ['panel', 'pandas'],
    'precache': [],
    'scripts': [
        f'https://cdn.bokeh.org/bokeh/{bk_prefix}/bokeh-{BOKEH_VERSION}.min.js',
        f'https://cdn.bokeh.org/bokeh/{bk_prefix}/bokeh-widgets-{BOKEH_VERSION}.min.js',
        f'https://cdn.bokeh.org/bokeh/{bk_prefix}/bokeh-tables-{BOKEH_VERSION}.min.js',
        f'{CDN_DIST}panel.min.js'
    ],
    'extra_css': [],
    'cache_patterns': [
        CDN_DIST,
        'https://cdn.bokeh.org/bokeh/',
        'https://cdn.jsdelivr.net/pyodide/',
        'https://files.pythonhosted.org/packages/',
        'https://pypi.org/pypi/'
    ],
    'setup_code': "",
    'warn_message': "Executing this cell will download Python runtime (typically 40+ MB).",
    'requires': {}
}

EXTRA_RESOURCES = defaultdict(lambda: {'js': [], 'css': [], 'js_modules': {}, 'js_exports': {}})

def extract_extensions(code: str) -> List[str]:
    """
    Extracts JS and CSS dependencies of Panel extensions from code snippets
    containing pn.extension calls.
    """
    js, js_exports, js_modules, css = [], {}, {}, []
    with set_resource_mode('cdn'):
        for name, model in Model.model_class_reverse_map.items():
            if hasattr(model, '__javascript__'):
                js += model.__javascript__
            if hasattr(model, '__css__'):
                css += model.__css__
            if hasattr(model, '__javascript_modules__'):
                js_modules.update({
                    jsm.split("/")[-1][:-3]: jsm for jsm in model.__javascript_modules__
                    if jsm.endswith('.js')
                })
            if hasattr(model, '__javascript_module_exports__'):
                js_exports.update(
                    dict(zip(model.__javascript_module_exports__,
                             model.__javascript_modules__))
                )
        for model in param.concrete_descendents(ReactiveHTML).values():
            if not model._loaded():
                continue
            js += getattr(model, '__javascript__', []) or []
            css += getattr(model, '__css__', []) or []
    if config.design and hasattr(config.design, 'resolve_resources'):
        design_resources = config.design().resolve_resources(
            cdn=True, include_theme=True
        )
        js += list(design_resources['js'].values())
        css += list(design_resources['css'].values())
        js_modules.update(design_resources['js_modules'])
    resources = Resources(mode='cdn')
    extensions = _bundle_extensions(None, resources)
    js += [cdn_url for bundle in extensions if bundle.cdn_url and
           '@holoviz/panel@' not in (cdn_url:= str(bundle.cdn_url))]
    global_exports = [
        extension._globals[ext][0] for ext, imp in extension._imports.items()
        if imp in sys.modules and ext in extension._globals
    ]
    return js, js_exports, js_modules, css, global_exports

def _model_json(model: Model, target: str) -> Tuple[Document, str]:
    """
    Renders a Bokeh Model to JSON representation given a particular
    DOM target and returns the Document and the serialized JSON string.

    Arguments
    ---------
    model: bokeh.model.Model
        The bokeh model to render.
    target: str
        The id of the DOM node to render to.

    Returns
    -------
    document: Document
        The bokeh Document containing the rendered Bokeh Model.
    model_json: str
        The serialized JSON representation of the Bokeh Model.
    """
    doc = Document()
    model.server_doc(doc=doc)
    model = doc.roots[0]
    docs_json, _ = standalone_docs_json_and_render_items(
        [model], suppress_callback_warning=True
    )
    doc_json = list(docs_json.values())[0]

    return doc, json.dumps(dict(
        target_id = target,
        root_id   = model.ref['id'],
        doc       = doc_json,
        version   = BOKEH_VERSION,
    ))


def _option_boolean(arg):
    if not arg or not arg.strip():
        # no argument given, assume used as a flag
        return True
    elif arg.strip().lower() in ("no", "0", "false"):
        return False
    elif arg.strip().lower() in ("yes", "1", "true"):
        return True
    else:
        raise ValueError('"%s" unknown boolean' % arg)

class PyodideDirective(Directive):

    has_content = True

    option_spec = {
        'skip-embed': _option_boolean
    }

    _current_source = None
    _current_context = {}
    _current_count = 0
    _current_process = None
    _conn = None

    @classmethod
    def _execution_process(cls, pipe):
        """
        Process execution loop to run in separate process that is used
        to evaluate code.
        """
        while True:
            msg = pipe.recv()
            if msg['type'] == 'close':
                break
            elif msg['type'] != 'execute':
                continue
            stdout = io.StringIO()
            stderr = io.StringIO()
            code = msg['code']
            with set_resource_mode('cdn'):
                try:
                    out = exec_with_return(code, stdout=stdout, stderr=stderr)
                except Exception:
                    out = None
                if (isinstance(out, (Model, Viewable, Viewer)) or
                    any(pane.applies(out) for pane in CONVERT_PANE_TYPES)):
                    _, content = _model_json(as_panel(out), msg['target'])
                    mime_type = 'application/bokeh'
                elif out is not None:
                    try:
                        content, mime_type = format_mime(out)
                    except Exception:
                        warnings.warn(f'Could not render {out!r} generated from executed code directive: {code}')
                else:
                    content, mime_type = None, None
            js, js_exports, js_modules, css, global_exports = extract_extensions(code)
            pipe.send((content, mime_type, stdout.getvalue(), stderr.getvalue(), js, js_exports, js_modules, css, global_exports))
        pipe.close()

    @classmethod
    def terminate(cls, *args):
        """
        Terminates a running process.
        """
        if not cls._current_process:
            return
        try:
            cls._conn.send({'type': 'close'})
            cls._current_process.join()
        except Exception:
            cls._current_process.terminate()
        finally:
            cls._current_process = None

    @classmethod
    def _launch_process(cls, timeout=5):
        """
        Launches a process to execute code in.
        """
        cls.terminate()
        cls._conn, child_conn = Pipe()
        cls._current_process = Process(target=cls._execution_process, args=(child_conn,))
        cls._current_process.start()

    @classmethod
    def _kill(cls):
        cls._current_process.terminate()
        cls._current_process = None

    def run(self):
        current_source = self.state_machine.get_source()
        if self._current_source != current_source or self._current_process is None:
            PyodideDirective._current_count = 0
            PyodideDirective._current_source = current_source
            self._launch_process()

        classes = 'pyodide'
        if 'class' in self.options:
            classes += f" {self.options['class']}"
        self.options['class'] = [classes]
        self.options['id'] = cellid = f'codecell{self._current_count}-py'
        roles.set_classes(self.options)
        code = '\n'.join(self.content)
        doctree_node = nodes.literal_block(code, code, **self.options)
        doctree_node['language'] = 'python'

        PyodideDirective._current_count += 1
        if self.options.get('skip-embed'):
            return [doctree_node]

        # Send execution request to client and wait for result
        self._conn.send({'type': 'execute', 'target': f'output-{cellid}', 'code': code})
        if self._conn.poll(60):
            try:
                output, mime_type, stdout, stderr, js, js_exports, js_modules, css, global_exports = (
                    self._conn.recv()
                )
            except Exception:
                self._kill()
                return [doctree_node]
        else:
            self._kill()
            return [doctree_node]
        EXTRA_RESOURCES[current_source]['js'] += js
        EXTRA_RESOURCES[current_source]['js_exports'].update(js_exports)
        EXTRA_RESOURCES[current_source]['js_modules'].update(js_modules)
        EXTRA_RESOURCES[current_source]['css'] += css

        stdout_style = 'style="display: block;"' if stdout else ''
        stdout_html = f'<pre id="stdout-{cellid}" class="pyodide-stdout" {stdout_style}>{escape(stdout)}</pre>'
        stdout_node = nodes.raw(stdout, stdout_html, format='html')

        stderr_style = 'style="display: block;"' if stderr else ''
        stderr_html = f'<pre id="stderr-{cellid}" class="pyodide-stderr" {stderr_style}>{escape(stderr)}</pre>'
        stderr_node = nodes.raw(stderr, stderr_html, format='html')

        rendered_nodes = [doctree_node, stdout_node, stderr_node]
        if output is None:
            return rendered_nodes

        # Ensure we wait for all JS module exports to be initialized
        exports = ' && '.join(f'window.{export}' for export in global_exports)
        if exports:
            exports = f' && {exports}'

        script = ""
        if mime_type == 'text/plain':
            output = f'<pre>{output}</pre>'
        elif mime_type == 'application/bokeh':
            script = f"""
            <script>
              async function embed_bokeh_{self._current_count} () {{
                if (window.Bokeh && window.Bokeh.Panel{exports}) {{
                  await Bokeh.embed.embed_item({output})
                }} else {{
                   setTimeout(embed_bokeh_{self._current_count}, 200)
                }}
              }};
              embed_bokeh_{self._current_count}()
            </script>
            """
            output = ""
        else:
            output = f'<div class="pyodide-output-wrapper">{output}</div>'
        output_html = f'<div id="output-{cellid}" class="pyodide-output embedded">{output}</div>\n{script}'
        output_node = nodes.raw(output, output_html, format='html')
        return rendered_nodes+[output_node]

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
        'autodetect_deps': pyodide_conf['autodetect_deps'],
        'requires': json.dumps(pyodide_conf['requires'])
    })
    with open(staticdir/ 'PyodideWebWorker.js', 'w', encoding='utf-8') as f:
        f.write(web_worker)
    worker_setup = WORKER_HANDLER_TEMPLATE.render(
        scripts=pyodide_conf['scripts']
    )
    with open(staticdir/ 'WorkerHandler.js', 'w', encoding='utf-8') as f:
        f.write(worker_setup)

    if not pyodide_conf['enable_pwa']:
        return

    # Render service worker
    service_worker = SERVICE_WORKER_TEMPLATE.render({
        'project': app.config.project,
        'version': app.config.version,
        'pre_cache': ', '.join([repr(req) for req in pyodide_conf['precache']]),
        'cache_patterns': ', '.join([repr(req) for req in pyodide_conf['cache_patterns']])
    })
    with open(builddir / 'PyodideServiceWorker.js', 'w', encoding='utf-8') as f:
        f.write(service_worker)
    service_handler = SERVICE_HANDLER_TEMPLATE.render()
    with open(staticdir/ 'ServiceHandler.js', 'w', encoding='utf-8') as f:
        f.write(service_handler)

    # Render manifest
    site_manifest = WEB_MANIFEST_TEMPLATE.render({
        'name': app.config.html_title,
    })
    with open(builddir / 'site.webmanifest', 'w', encoding='utf-8') as f:
        f.write(site_manifest)


def init_conf(app: Sphinx) -> None:
    pyodide_conf = dict(DEFAULT_PYODIDE_CONF, **app.config.nbsite_pyodide_conf)
    app.config.nbsite_pyodide_conf = pyodide_conf
    app.config.html_static_path.append(
        str((HERE /'_static' ).absolute())
    )
    if pyodide_conf['enable_pwa']:
        app.add_js_file('ServiceHandler.js')
    for script in pyodide_conf['scripts']:
        app.add_js_file(script)

def html_page_context(
    app: Sphinx,
    pagename: str,
    templatename: str,
    context: Dict[str, Any],
    doctree: nodes.document,
) -> None:
    if not doctree:
        return

    if app.config.nbsite_pyodide_conf['enable_pwa']:
        relpath = '/'.join(['..']*pagename.count('/'))
        if relpath:
            relpath += '/'
        context[
            "metatags"
        ] += f"""
            <link rel="manifest" href="{relpath}site.webmanifest"/>
            """

    # Add additional resources extracted from pn.extension calls
    sourcename = context['sourcename'].replace('.txt', '')
    extra_resources = [
        (r['js'], r['js_exports'], r['js_modules'], r['css']) for filename, r in EXTRA_RESOURCES.items()
        if filename.endswith(sourcename)
    ]
    if extra_resources:
        extra_js, js_exports, js_modules, extra_css = extra_resources[0]
    else:
        extra_js, js_exports, js_modules, extra_css = [], {}, {}, []
    extra_css += app.config.nbsite_pyodide_conf.get('extra_css', [])
    context["script_files"] += extra_js
    context["css_files"] += extra_css

    module_tags = ""
    for export, module in js_modules.items():
        module_tags += JS_MODULE_TAG.format(file=module)
    for export, module in js_exports.items():
        module_tags += JS_MODULE_EXPORT.format(name=export, file=module)
    if module_tags:
        context["body"] = f'{module_tags}{context["body"]}'

    # Remove Scripts and CSS from page if no pyodide cells are found.
    if any(
        'pyodide' in cb.attributes.get('classes', [])
        for cb in doctree.traverse(nodes.literal_block)
    ):
        return

    # Remove JS files
    pyodide_scripts = (
        app.config.nbsite_pyodide_conf['scripts'] +
        ['_static/run_cell.js', '_static/WorkerHandler.js']
    )

    context["script_files"] = [
        ii for ii in context["script_files"]
        if ii not in pyodide_scripts
    ]

    # Remove pyodide CSS files
    context["css_files"] = [
        ii for ii in context["css_files"]
        if ii not in ['_static/runbutton.css']
    ]


def setup(app):
    """Setup sphinx-gallery sphinx extension"""
    app.add_config_value('nbsite_pyodide_conf', DEFAULT_PYODIDE_CONF, 'html')

    app.connect('builder-inited', init_conf)
    app.connect('build-finished', write_worker)
    app.connect('html-page-context', html_page_context)
    app.connect('build-finished', PyodideDirective.terminate)

    app.add_directive('pyodide', PyodideDirective)

    app.add_css_file('runbutton.css')
    app.add_js_file('run_cell.js')
    app.add_js_file('WorkerHandler.js')

    return {
        'version': '0.5',
        'parallel_read_safe': True,
        'parallel_write_safe': True,
    }
