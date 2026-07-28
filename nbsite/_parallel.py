"""Make Sphinx parallel builds survive a worker dying mid-task.

Sphinx runs the reading and writing phases in forked workers and collects
each result over a pipe. If a worker dies without sending anything (killed by
the OS, a segfault in a C extension, ...) the pipe reaches EOF, ``pipe.recv()``
raises ``EOFError`` and the build is aborted, which happens regularly on CI.

``ParallelTasks`` is patched here so the chunk of a worker that died is re-run
in the main process instead of aborting the build.
"""
import traceback

from sphinx.errors import SphinxParallelError
from sphinx.util import logging, parallel as _parallel

logger = logging.getLogger(__name__)

_orig_init = _parallel.ParallelTasks.__init__
_orig_add_task = _parallel.ParallelTasks.add_task


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
    logger.warning(
        'parallel worker (exitcode %s) died without sending a result, '
        'running its task in the main process', proc.exitcode
    )
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

    while self._precvs_waiting and self._pworking < self.nproc:
        newtid, newprecv = self._precvs_waiting.popitem()
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
