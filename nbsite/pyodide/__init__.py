import asyncio
import hashlib
import io
import json
import os
import pathlib
import sys
import traceback as tb
import warnings

from collections import defaultdict
from html import escape
from multiprocessing import Pipe, get_context
from pathlib import Path
from typing import (
    Any, Dict, List, Tuple,
)

import param
import portalocker

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
from panel.reactive import ReactiveCustomBase
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

RESOURCE_FILE = '.extra_resources.json'

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
    'preamble': "",
    'setup_code': "",
    'warn_message': "Executing this cell will download Python runtime (typically 40+ MB).",
    'requires': {}
}

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
        for model in param.concrete_descendents(ReactiveCustomBase).values():
            if not model._loaded():
                continue
            js += getattr(model, '__javascript__', []) or []
            model_css = (getattr(model, '__css__', []) or []) + (getattr(model, '_bundle_css', []) or [])
            for c in model_css:
                if c.startswith('https://') and c not in css:
                    css.append(c)
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

def write_resources(out_dir, source, resources):
    """
    Writes resources extracted from process to a shared JSON file to
    which will be read on document write. On windows uses in-memory
    variable since parallelization is not supported.

    Arguments
    ---------
    out_dir: str
        The build directory
    source: str
        The source file the resources are assosicated with.
    resources: dict[str, any]
        The resources to add to the resource dictionary.
    """
    out_path = pathlib.Path(os.fspath(out_dir))
    out_path.mkdir(exist_ok=True)
    resources_file = out_path / RESOURCE_FILE
    existing = resources_file.is_file()
    with portalocker.Lock(resources_file, 'a+') as rfile:
        rfile.seek(0)

        # Load existing resources from file
        all_resources = {}
        if existing:
            all_resources = json.load(rfile)
            rfile.seek(0)
            rfile.truncate()

        if source in all_resources:
            # Merge with existing resources for source file
            source_resources = all_resources[source]
            source_resources['css'] += [css for css in resources['css'] if css not in source_resources['css']]
            source_resources['js'] += [js for js in resources['js'] if js not in source_resources['js']]
            source_resources['js_exports'].update(resources['js_exports'])
            source_resources['js_modules'].update(resources['js_modules'])
        else:
            # Add new resources for this source file
            all_resources[source] = source_resources = resources
        json.dump(all_resources, rfile)
        rfile.flush()
        os.fsync(rfile.fileno())



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

    _exec_state = defaultdict(lambda: {
        'source': None,
        'context': {},
        'count': 0,
        'total': None,
        'process': None,
        'conn': None,
        'cache': {},
        'hash': None
    })

    @classmethod
    def _execution_process(cls, pipe):
        """
        Process execution loop to run in separate process that is used
        to evaluate code.
        """
        async def event_loop():
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
                    mime_type = None
                    if (isinstance(out, (Model, Viewable, Viewer)) or
                        any(pane.applies(out) for pane in CONVERT_PANE_TYPES)):
                        try:
                            _, content = _model_json(as_panel(out), msg['target'])
                            mime_type = 'application/bokeh'
                        except Exception:
                            content = None
                            warnings.warn(
                                f'Could not render {out!r} generated from executed code directive:\n\n{code}\n\n'
                                f'Failed with following error:\n\n{tb.format_exc()}'
                            )
                    elif out is not None:
                        try:
                            content, mime_type = format_mime(out)
                        except Exception:
                            content = None
                            warnings.warn(f'Could not render {out!r} generated from executed code directive: {code}')
                    else:
                        content = None
                    js, js_exports, js_modules, css, global_exports = extract_extensions(code)
                pipe.send((content, mime_type, stdout.getvalue(), stderr.getvalue(), js, js_exports, js_modules, css, global_exports))

            tasks = asyncio.all_tasks() - {asyncio.current_task()}
            for task in tasks:
                task.cancel()
            await asyncio.gather(*tasks, return_exceptions=True)

        asyncio.get_event_loop().run_until_complete(event_loop())
        pipe.close()

    @classmethod
    def terminate(cls, *args):
        """
        Terminates a running process.
        """
        for source in cls._exec_state.copy():
            cls._kill(source)

    @classmethod
    def _launch_process(cls, source, timeout=5):
        """
        Launches a process to execute code in.
        """
        cls._exec_state[source]['conn'], child_conn = Pipe()
        cls._exec_state[source]['process'] = process = get_context('spawn').Process(
            target=cls._execution_process, args=(child_conn,), daemon=True
        )
        process.start()

    @classmethod
    def _kill(cls, source, clear=True):
        state = cls._exec_state[source]
        if state['process']:
            try:
                state['conn'].send({'type': 'close'})
                state['process'].join()
            except Exception:
                state['process'].terminate()
        if clear:
            del cls._exec_state[source]

    def run(self):
        outdir = self.state.document.settings.env.app.outdir
        cache_path = pathlib.Path(str(outdir)) / '.pyodide'
        cache_path.mkdir(exist_ok=True)
        current_source = self.state_machine.get_source()
        if current_source not in self._exec_state:
            with open(current_source, encoding='utf-8') as src_doc:
                content = src_doc.read()
            content_hash = hashlib.md5(content.encode('utf-8')).hexdigest()
            cache_file = cache_path / f'{content_hash}.json'
            if cache_file.is_file():
                with open(cache_file, encoding='utf-8') as cf:
                    self._exec_state[current_source]['cache'] = json.load(cf)
            else:
                self._launch_process(current_source)
            total = content.count('{pyodide}')
            self._exec_state[current_source]['total'] = total
            self._exec_state[current_source]['hash'] = content_hash
        else:
            self._exec_state[current_source]['count'] += 1
        state = self._exec_state[current_source]
        count = state['count']
        cache_file = cache_path / f'{state["hash"]}.json'

        # Construct code block node
        classes = 'pyodide'
        if 'class' in self.options:
            classes += f" {self.options['class']}"
        self.options['class'] = [classes]
        self.options['id'] = cellid = f'codecell{count}-py'
        roles.set_classes(self.options)
        code = '\n'.join(self.content)
        doctree_node = nodes.literal_block(code, code, **self.options)
        doctree_node['language'] = 'python'

        if self.options.get('skip-embed'):
            return [doctree_node]

        # Send execution request to client and wait for result
        conn = state['conn']
        try:
            code_hash = hashlib.md5(code.encode('utf-8')).hexdigest()
            if code_hash in state['cache']:
                result = state['cache'][code_hash]
            elif conn:
                conn.send({'type': 'execute', 'target': f'output-{cellid}', 'code': code})
                if conn.poll(60):
                    state['cache'][code_hash] = result = conn.recv()
                else:
                    raise RuntimeError('Timed out')
            else:
                raise RuntimeError('Process was shut down')
        except Exception:
            self._kill(current_source, clear=False)
            return [doctree_node]
        finally:
            # If we are in the last pyodide cell kill the process
            if (count+1) == state['total']:
                self._kill(current_source)
                cache_file.write_text(json.dumps(state['cache']))

        output, mime_type, stdout, stderr, js, js_exports, js_modules, css, global_exports = result

        # Write out resources
        resources = {
            'css': css,
            'js': js,
            'js_exports': js_exports,
            'js_modules': js_modules
        }
        write_resources(outdir, current_source, resources)

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
              async function embed_bokeh_{count} () {{
                if (window.Bokeh && window.Bokeh.Panel{exports}) {{
                  await Bokeh.embed.embed_item({output})
                }} else {{
                   setTimeout(embed_bokeh_{count}, 200)
                }}
              }};
              embed_bokeh_{count}()
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

    out_dir = pathlib.Path(str(app.outdir))
    resource_file = out_dir / RESOURCE_FILE
    if resource_file.is_file():
        resource_file.unlink()

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

    resource_file = pathlib.Path(str(app.outdir)) / RESOURCE_FILE
    if resource_file.is_file():
        resources = json.loads(resource_file.read_text())
    else:
        resources = {}
    code_resources = [
        (r['js'], r['js_exports'], r['js_modules'], r['css'])
        for filename, r in resources.items()
        if filename.endswith(sourcename)
    ]
    if code_resources:
        extra_js, js_exports, js_modules, extra_css = code_resources[0]
    else:
        extra_js, js_exports, js_modules, extra_css = [], {}, {}, []
    extra_css += app.config.nbsite_pyodide_conf.get('extra_css', [])
    existing_js = [
        getattr(js, 'filename', js) or js for js in context["script_files"]
    ]
    for js in extra_js:
        if js not in existing_js:
            context["script_files"].append(js)
    context["css_files"] += extra_css

    module_tags = app.config.nbsite_pyodide_conf['preamble']
    for export, module in js_modules.items():
        module_tags += JS_MODULE_TAG.format(file=module)
    for export, module in js_exports.items():
        module_tags += JS_MODULE_EXPORT.format(name=export, file=module)
    if module_tags:
        context["body"] = f'{module_tags}{context["body"]}'

    if any(
        'pyodide' in cb.attributes.get('classes', [])
        for cb in doctree.traverse(nodes.literal_block)
    ):
        return

    # Remove Scripts and CSS from page if no pyodide cells are found.
    pyodide_scripts = (
        app.config.nbsite_pyodide_conf['scripts'] +
        ['_static/run_cell.js', '_static/WorkerHandler.js']
    )

    context["script_files"][:] = [
        ii for ii in context["script_files"]
        if (getattr(ii, 'filename', ii) or ii) not in pyodide_scripts
    ]

    # Remove pyodide CSS files
    context["css_files"][:] = [
        ii for ii in context["css_files"]
        if (getattr(ii, 'filename', ii) or ii) not in ['_static/runbutton.css']
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
