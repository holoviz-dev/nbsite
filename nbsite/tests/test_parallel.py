import multiprocessing
import os

import pytest

from sphinx.errors import SphinxParallelError
from sphinx.util.parallel import ParallelTasks, parallel_available

from nbsite._parallel import patch_parallel_tasks

pytestmark = pytest.mark.skipif(
    not parallel_available, reason='Sphinx parallel builds need forking'
)


@pytest.fixture(autouse=True)
def patched():
    patch_parallel_tasks()


def _die_in_worker(arg):
    if multiprocessing.parent_process() is not None:
        # Emulate a worker killed before it could send back a result
        os._exit(1)
    return f'{arg}-main'


def _echo(arg):
    return arg


def _raise(arg):
    raise ValueError('boom')


def test_task_of_dead_worker_is_run_in_main_process():
    results = []
    tasks = ParallelTasks(2)
    tasks.add_task(_die_in_worker, 'a', lambda arg, result: results.append((arg, result)))
    tasks.join()
    assert results == [('a', 'a-main')]


def test_dead_worker_does_not_stop_the_other_tasks():
    results = []
    tasks = ParallelTasks(2)
    tasks.add_task(_die_in_worker, 'a', lambda arg, result: results.append((arg, result)))
    for arg in 'bc':
        tasks.add_task(_echo, arg, lambda arg, result: results.append((arg, result)))
    tasks.join()
    assert sorted(results) == [('a', 'a-main'), ('b', 'b'), ('c', 'c')]


def test_results_are_collected_normally():
    results = []
    tasks = ParallelTasks(2)
    for arg in 'abc':
        tasks.add_task(_echo, arg, lambda arg, result: results.append((arg, result)))
    tasks.join()
    assert sorted(results) == [('a', 'a'), ('b', 'b'), ('c', 'c')]


def test_failing_task_still_raises():
    tasks = ParallelTasks(2)
    tasks.add_task(_raise, 'a', lambda arg, result: None)
    with pytest.raises(SphinxParallelError):
        tasks.join()
