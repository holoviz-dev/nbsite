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
const source = fs.readFileSync(process.argv[1], 'utf8').replace(/^import \{ loadPyodide \}.*\n/, '');
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
