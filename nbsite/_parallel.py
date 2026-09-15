"""Make Sphinx parallel builds survive a worker dying mid-task.

Sphinx runs the reading and writing phases in forked workers and collects
each result over a pipe. If a worker dies without sending anything (killed by
the OS, a segfault in a C extension, ...) the pipe reaches EOF, ``pipe.recv()``
raises ``EOFError`` and the build is aborted, which happens regularly on CI.

``ParallelTasks`` is patched here so the chunk of a worker that died is re-run
in the main process instead of aborting the build.

``PythonDomain.merge_domaindata`` is patched so the result of a parallel read
does not depend on which chunk is merged first. See
``_merge_python_domaindata``.
"""

import traceback

from sphinx.domains.python import PythonDomain
from sphinx.errors import SphinxParallelError
from sphinx.util import logging, parallel as _parallel

logger = logging.getLogger(__name__)

_orig_init = _parallel.ParallelTasks.__init__
_orig_add_task = _parallel.ParallelTasks.add_task
_orig_join_one = _parallel.ParallelTasks._join_one
_orig_merge_python_domaindata = PythonDomain.merge_domaindata


def _waiting(self):
    # Sphinx renamed ``_precvsWaiting`` to ``_precvs_waiting`` in 8.2.
    try:
        return self._precvs_waiting
    except AttributeError:
        return self._precvsWaiting


def _init(self, nproc):
    _orig_init(self, nproc)
    # Sphinx keeps no reference to the task functions, and ``Process.start``
    # deletes the target and arguments the process was created with, so they
    # have to be recorded to be able to re-run the task of a dead worker.
    self._task_funcs = {}


def _add_task(self, task_func, arg=None, result_func=None):
    self._task_funcs[self._taskid] = task_func
    _orig_add_task(self, task_func, arg, result_func)


def _run_in_main_process(self, tid):
    """Run the task of the worker that died, mimicking ``_process``."""
    proc = self._procs[tid]
    proc.join()
    logger.warning("parallel worker (exitcode %s) died without sending a result, running its task in the main process", proc.exitcode)
    func, arg = self._task_funcs[tid], self._args[tid]
    try:
        result = func() if arg is None else func(arg)
    except BaseException as err:
        errmsg = traceback.format_exception_only(err.__class__, err)[0].strip()
        return True, [], (errmsg, traceback.format_exc())
    return False, [], result


def _join_one(self):
    joined_any = False
    for tid, pipe in self._precvs.items():
        if pipe.poll():
            try:
                exc, logs, result = pipe.recv()
            except EOFError:
                exc, logs, result = _run_in_main_process(self, tid)
            if exc:
                raise SphinxParallelError(*result)
            for log in logs:
                logger.handle(log)
            self._task_funcs.pop(tid)
            self._result_funcs.pop(tid)(self._args.pop(tid), result)
            self._procs[tid].join()
            self._precvs.pop(tid)
            self._pworking -= 1
            joined_any = True
            break

    waiting = _waiting(self)
    while waiting and self._pworking < self.nproc:
        newtid, newprecv = waiting.popitem()
        self._precvs[newtid] = newprecv
        self._procs[newtid].start()
        self._pworking += 1

    return joined_any


def patch_parallel_tasks():
    """Patch ``sphinx.util.parallel.ParallelTasks``, idempotently."""
    if _parallel.ParallelTasks._join_one is _join_one:
        return
    _parallel.ParallelTasks.__init__ = _init
    _parallel.ParallelTasks.add_task = _add_task
    _parallel.ParallelTasks._join_one = _join_one


def unpatch_parallel_tasks():
    """Restore the original ``sphinx.util.parallel.ParallelTasks``."""
    _parallel.ParallelTasks.__init__ = _orig_init
    _parallel.ParallelTasks.add_task = _orig_add_task
    _parallel.ParallelTasks._join_one = _orig_join_one


def _merge_python_domaindata(self, docnames, otherdata):
    """Merge the Python objects of a parallel read like ``note_object``.

    An object documented where it is defined and also through an alias (e.g.
    a class re-exported in a package ``__all__``, registered with
    ``:canonical:``) keeps pointing to its original definition in a serial
    build. Sphinx's merge overwrites instead, so in a parallel build the
    target depended on which chunk finished last.
    """
    for fullname, obj in otherdata['objects'].items():
        if obj.docname not in docnames:
            continue
        existing = self.objects.get(fullname)
        if existing is not None and not existing.aliased and obj.aliased:
            continue
        self.objects[fullname] = obj
    for modname, mod in otherdata['modules'].items():
        if mod.docname in docnames:
            self.modules[modname] = mod


def patch_python_domain_merge():
    """Patch ``PythonDomain.merge_domaindata``, idempotently."""
    PythonDomain.merge_domaindata = _merge_python_domaindata


def unpatch_python_domain_merge():
    """Restore the original ``PythonDomain.merge_domaindata``."""
    PythonDomain.merge_domaindata = _orig_merge_python_domaindata
