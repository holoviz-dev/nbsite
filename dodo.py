import os

if "PYCTDEV_ECOSYSTEM" not in os.environ:
    os.environ["PYCTDEV_ECOSYSTEM"] = "pip"

from pyctdev import *  # noqa: api

########## DOCS ##########

def task_build_docs():
    """build docs"""
    return {
        'actions': [
            'nbsite generate-rst --org pyviz-dev --repo nbsite --skip ".*sites.*"',
            'nbsite build',
        ],
        'verbosity': 2,
    }
