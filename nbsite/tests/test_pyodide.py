import json
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
