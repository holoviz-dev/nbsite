from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.domains.python import PythonDomain
from sphinx.util.parallel import ParallelTasks

from ._parallel import (
    _add_task, _init, _join_one, _merge_python_domaindata, _orig_add_task,
    _orig_init, _orig_join_one, _orig_merge_python_domaindata,
)
from ._toctree import _get_local_toctree, _orig_get_local_toctree


def _patch_parallel_tasks():
    """Patch ``sphinx.util.parallel.ParallelTasks``, idempotently."""
    if ParallelTasks._join_one is _join_one:
        return
    ParallelTasks.__init__ = _init
    ParallelTasks.add_task = _add_task
    ParallelTasks._join_one = _join_one


def _unpatch_parallel_tasks():
    """Restore the original ``sphinx.util.parallel.ParallelTasks``."""
    ParallelTasks.__init__ = _orig_init
    ParallelTasks.add_task = _orig_add_task
    ParallelTasks._join_one = _orig_join_one


def _patch_python_domain_merge():
    """Patch ``PythonDomain.merge_domaindata``, idempotently."""
    PythonDomain.merge_domaindata = _merge_python_domaindata


def _unpatch_python_domain_merge():
    """Restore the original ``PythonDomain.merge_domaindata``."""
    PythonDomain.merge_domaindata = _orig_merge_python_domaindata


def _patch_get_local_toctree():
    """Patch ``StandaloneHTMLBuilder._get_local_toctree``, idempotently."""
    StandaloneHTMLBuilder._get_local_toctree = _get_local_toctree


def _unpatch_get_local_toctree():
    """Restore the original ``StandaloneHTMLBuilder._get_local_toctree``."""
    StandaloneHTMLBuilder._get_local_toctree = _orig_get_local_toctree


def _apply_sphinx_patches(app, config):
    """Patch or restore Sphinx on ``config-inited``, following ``nbsite_sphinx_patches``."""
    if config.nbsite_sphinx_patches:
        _patch_parallel_tasks()
        _patch_python_domain_merge()
        _patch_get_local_toctree()
    else:
        _unpatch_parallel_tasks()
        _unpatch_python_domain_merge()
        _unpatch_get_local_toctree()
