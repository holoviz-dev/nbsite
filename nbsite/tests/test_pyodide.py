import json
import shutil
import subprocess

from types import SimpleNamespace

import pytest

from nbsite.pyodide import DEFAULT_PYODIDE_CONF, write_worker


@pytest.mark.parametrize('lockfile', [False, True])
def test_write_worker_lockfile(tmp_path, monkeypatch, lockfile):
    static = tmp_path / '_static'
    static.mkdir()
    conf = {
        'PYODIDE_URL': 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs',
        'requirements': ['panel>=1', 'pandas', 'https://example.com/my_pkg-1.0-py3-none-any.whl'],
        'lockfile': lockfile,
        'setup_code': '',
        'autodetect_deps': True,
        'requires': {'example.md': ['hvplot']},
        'scripts': [],
        'enable_pwa': False,
    }
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )
    calls = []
    monkeypatch.setattr('nbsite.pyodide.subprocess.run', lambda args, **kwargs: calls.append((args, kwargs)))

    write_worker(app, None)

    worker = (static / 'PyodideWebWorker.js').read_text()
    assert 'import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs";' in worker
    assert "{type: 'module'}" in (static / 'WorkerHandler.js').read_text()
    if lockfile:
        assert len(calls) == 1
        args, kwargs = calls[0]
        assert args[0] == 'node'
        assert json.loads(args[3]) == conf['requirements']
        assert args[4] == str(static / 'pyodide-lock.json')
        assert kwargs['check'] is True
        assert 'const LOCKFILE_PACKAGES = ["panel", "pandas", "my-pkg"]' in worker
    else:
        assert not calls
        assert 'const LOCKFILE_PACKAGES = []' in worker


def test_default_pyodide_version():
    assert DEFAULT_PYODIDE_CONF['PYODIDE_URL'] == 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs'


def test_write_worker_legacy_url(tmp_path):
    (tmp_path / '_static').mkdir()
    conf = dict(DEFAULT_PYODIDE_CONF, PYODIDE_URL='https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js', enable_pwa=False)
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )

    write_worker(app, None)

    assert 'importScripts("https://cdn.jsdelivr.net/pyodide/v0.25.0/full/pyodide.js")' in (tmp_path / '_static' / 'PyodideWebWorker.js').read_text()
    assert "{type: 'module'}" not in (tmp_path / '_static' / 'WorkerHandler.js').read_text()


def test_write_worker_empty_lockfile_requirements(tmp_path, monkeypatch):
    (tmp_path / '_static').mkdir()
    conf = {
        'PYODIDE_URL': 'https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs',
        'requirements': [],
        'lockfile': True,
        'setup_code': '',
        'autodetect_deps': False,
        'requires': {},
        'scripts': [],
        'enable_pwa': False,
    }
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )
    monkeypatch.setattr('nbsite.pyodide.subprocess.run', lambda *args, **kwargs: pytest.fail('Unexpected Node invocation'))

    write_worker(app, None)

    assert 'const LOCKFILE_PACKAGES = []' in (tmp_path / '_static' / 'PyodideWebWorker.js').read_text()


def test_write_worker_lockfile_failure(tmp_path, monkeypatch):
    (tmp_path / '_static').mkdir()
    conf = dict(DEFAULT_PYODIDE_CONF, lockfile=True, enable_pwa=False)
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )

    def fail(*args, **kwargs):
        raise subprocess.CalledProcessError(1, args[0])

    monkeypatch.setattr('nbsite.pyodide.subprocess.run', fail)
    with pytest.raises(RuntimeError, match='matching pyodide npm package'):
        write_worker(app, None)


def test_write_worker_panel_local_wheels(tmp_path, monkeypatch):
    (tmp_path / '_static').mkdir()
    requirements = [
        './wheels/bokeh-3.10.0-py3-none-any.whl',
        './wheels/panel-1.10.0b1-py3-none-any.whl',
        'pyodide-http',
    ]
    conf = dict(DEFAULT_PYODIDE_CONF, requirements=requirements, lockfile=True, enable_pwa=False)
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )
    calls = []
    monkeypatch.setattr('nbsite.pyodide.subprocess.run', lambda args, **kwargs: calls.append(args))

    write_worker(app, None)

    assert json.loads(calls[0][3]) == requirements
    assert 'const LOCKFILE_PACKAGES = ["bokeh", "panel", "pyodide-http"]' in (tmp_path / '_static' / 'PyodideWebWorker.js').read_text()


def test_write_worker_panel_314_js_url(tmp_path):
    (tmp_path / '_static').mkdir()
    conf = dict(DEFAULT_PYODIDE_CONF, PYODIDE_URL='https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.js', enable_pwa=False)
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )

    write_worker(app, None)

    assert 'import { loadPyodide } from "https://cdn.jsdelivr.net/pyodide/v314.0.7/full/pyodide.mjs"' in (tmp_path / '_static' / 'PyodideWebWorker.js').read_text()
    assert "{type: 'module'}" in (tmp_path / '_static' / 'WorkerHandler.js').read_text()


@pytest.mark.parametrize('result', ['object', 'map', 'empty'])
def test_worker_render_result(tmp_path, result):
    """Worker handles both current object and older Map return values."""
    if not shutil.which('node'):
        pytest.skip('Node is required to execute the generated worker')
    (tmp_path / '_static').mkdir()
    conf = dict(DEFAULT_PYODIDE_CONF, autodetect_deps=False, enable_pwa=False)
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf),
    )
    write_worker(app, None)
    script = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const source = fs.readFileSync(process.argv[1], 'utf8').replace(/\r?\n/g, '\r\n')
  .replace(/^import \{ loadPyodide \}[^\r\n]*\r?$/m, '');
const messages = [];
const values = {content: 'rendered', mime_type: 'text/plain', stdout: 'printed', stderr: 'warning'};
global.self = {
  pyodide: {
    globals: {set() {}},
    runPythonAsync: async () => process.argv[2] === 'empty' ? null :
      process.argv[2] === 'map' ? new Map(Object.entries(values)) : values,
  },
  postMessage: message => messages.push(message),
};
vm.runInThisContext(source);
self.onmessage({data: {type: 'execute', id: 'cell', uuid: 'test'}}).then(() => {
  assert.deepEqual(messages.map(message => message.type),
    process.argv[2] === 'empty' ? ['idle'] : ['render', 'stdout', 'stderr', 'idle']);
  if (process.argv[2] !== 'empty') {
    assert.equal(messages[0].content, 'rendered');
    assert.equal(messages[0].mime, 'text/plain');
  }
}).catch(error => { console.error(error); process.exitCode = 1; });
'''
    subprocess.run(['node', '-e', script, str(tmp_path / '_static' / 'PyodideWebWorker.js'), result], check=True)


SERVICE_WORKER_HARNESS = r'''
const fs = require('node:fs');
const vm = require('node:vm');
const assert = require('node:assert/strict');
const [source, scenario] = [fs.readFileSync(process.argv[1], 'utf8'), process.argv[2]];

const store = new Map([
  ['Docs-0.9', new Map()],
  ['Docs Pyodide App-abc', new Map()],
  ['Docs@https://example.org/en/docs/0.9/-0.9', new Map()],
  ['Docs@https://example.org/en/docs/1.0/-0.9', new Map()],
]);
const fetched = [];
const handlers = {};
const context = {
  console: {log() {}},
  URL, Request, Response,
  caches: {
    keys: async () => [...store.keys()],
    delete: async (name) => store.delete(name),
    open: async (name) => {
      if (!store.has(name)) store.set(name, new Map());
      const entries = store.get(name);
      return {match: async (r) => entries.get(r.url), put: async (r, res) => entries.set(r.url, res)};
    },
  },
  fetch: async (request) => {
    fetched.push(request);
    const path = new URL(request.url).pathname;
    if (path.endsWith('/missing.html')) return new Response('', {status: 404});
    if (path.endsWith('/dir')) return {ok: false, type: 'opaqueredirect', status: 0};
    return new Response('ok');
  },
};
context.self = {
  registration: {scope: 'https://example.org/en/docs/1.0/'},
  location: {origin: 'https://example.org'},
  clients: {claim() {}},
  skipWaiting() {},
  addEventListener: (type, fn) => { handlers[type] = fn; },
};
vm.runInNewContext(source, context);

const respond = (request) => new Promise((resolve) => handlers.fetch({request, respondWith: resolve}));
const navigation = (url) => ({url, method: 'GET', mode: 'navigate', credentials: 'include'});

(async () => {
  let installed;
  handlers.install({waitUntil: (p) => { installed = p; }});
  await installed;
  const kept = [...store.keys()].sort();

  if (scenario === 'default') {
    // Original behaviour: every cache starting with the project name except the current one goes.
    assert.deepEqual(kept, ['Docs-1.0']);
  } else {
    assert.deepEqual(kept, [
      'Docs Pyodide App-abc',
      'Docs-0.9',
      'Docs@https://example.org/en/docs/0.9/-0.9',
      'Docs@https://example.org/en/docs/1.0/-1.0',
    ]);
  }

  const missing = await respond(new Request('https://example.org/en/docs/1.0/missing.html'));
  assert.equal(missing.status, 404);
  const redirect = await respond(navigation('https://example.org/en/docs/1.0/dir'));
  assert.equal(redirect.type, 'opaqueredirect');
  const cacheName = [...store.keys()].find((name) => name.endsWith('1.0'));
  assert.deepEqual([...store.get(cacheName).keys()], []);

  fetched.length = 0;
  await respond(new Request('https://example.org/en/docs/1.0/page.html'));
  await respond(navigation('https://example.org/en/docs/1.0/index.html'));
  await respond(new Request('https://cdn.example.com/lib.js'));
  const [asset, page, external] = fetched;
  if (scenario === 'default') {
    assert.equal(asset.cache, 'default');
    assert.equal(page.mode, 'navigate');
  } else {
    assert.equal(asset.cache, 'no-cache');
    assert.equal(page.cache, 'no-cache');
    assert.equal(page.redirect, 'manual');
  }
  assert.equal(external.cache, 'default');
  assert.equal(store.get(cacheName).size, 3);
})().catch((error) => { console.error(error); process.exitCode = 1; });
'''


def _write_pwa(tmp_path, **options):
    (tmp_path / '_static').mkdir()
    conf = dict(DEFAULT_PYODIDE_CONF, autodetect_deps=False, **options)
    app = SimpleNamespace(
        builder=SimpleNamespace(format='html', outdir=tmp_path),
        config=SimpleNamespace(nbsite_pyodide_conf=conf, project='Docs', version='1.0', html_title='Docs 1.0'),
    )
    write_worker(app, None)


@pytest.mark.parametrize('scenario', ['default', 'versioned'])
def test_service_worker_caches(tmp_path, scenario):
    if not shutil.which('node'):
        pytest.skip('Node is required to execute the generated service worker')
    options = {} if scenario == 'default' else {'pwa_scope_caches': True, 'pwa_fetch_cache': 'no-cache'}
    _write_pwa(tmp_path, **options)
    subprocess.run(['node', '-e', SERVICE_WORKER_HARNESS, str(tmp_path / 'PyodideServiceWorker.js'), scenario], check=True)


def test_service_worker_defaults_unchanged(tmp_path):
    _write_pwa(tmp_path)
    worker = (tmp_path / 'PyodideServiceWorker.js').read_text()
    assert "const appCacheName = 'Docs-1.0';" in worker
    assert 'const fetchCache = null;' in worker
    assert json.loads((tmp_path / 'site.webmanifest').read_text())['scope'] == '/'


def test_service_worker_overrides(tmp_path):
    _write_pwa(tmp_path, pwa_cache_version='1.0+build.7', pwa_manifest_scope='./')
    worker = (tmp_path / 'PyodideServiceWorker.js').read_text()
    assert "const appCacheName = 'Docs-1.0+build.7';" in worker
    assert json.loads((tmp_path / 'site.webmanifest').read_text())['scope'] == './'
