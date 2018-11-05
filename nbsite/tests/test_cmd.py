import os
import pytest
import pyct.cmd
from nbsite.cmd import generate_rst, build

# Note: a lot of this setup is copied from the new (2018-11-01) test in
# pyct. Potentially this could be consolidated at some point. The fixture
# setup could also move to conftest.py

# Use `pytest  --pdb -m "not slow"` to run just the faster rst generating tests

DATA_FILE_0_CONTENT = u"""
name,score,rank
Alice,100.5,1
Bob,50.3,2
Charlie,25,3
"""

DATA_FILE_1_CONTENT = u"""
name,score,rank
Alice,100.5,1
Bob,50.3,2
Charlie,25,3
Dave,28,4
Eve,25,3
Frank,75,9
"""

EXAMPLE_0_CONTENT = u"""{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "**NOTE:** This is a temporary notebook that gets created for tests."
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python",
   "pygments_lexer": "ipython3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""

EXAMPLE_1_CONTENT = u"""{
 "cells": [
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "**NOTE:** This is another temporary notebook that gets created for tests."
   ]
  }
 ],
 "metadata": {
  "language_info": {
   "name": "python",
   "pygments_lexer": "ipython3"
  }
 },
 "nbformat": 4,
 "nbformat_minor": 2
}
"""

CONF_CONTENT = u"""
from nbsite.shared_conf import *

"""

INDEX_CONTENT = u"""
*******
Project
*******

.. toctree::
   :hidden:
   :maxdepth: 2

   Example_0 <Example_Notebook_0>
   Example_1 <Example_Notebook_1>
"""

EXAMPLE_0_RST = u"""
******************
Example Notebook 0
******************

.. notebook:: test_project ../examples/Example_Notebook_0.ipynb
    :offset: 0
"""

EXAMPLE_1_RST = u"""
******************
Example Notebook 1
******************

.. notebook:: test_project ../examples/Example_Notebook_1.ipynb
    :offset: 0
"""

@pytest.fixture(autouse=True)
def tmp_module(tmp_path):
    """This sets up a temporary directory structure meant to mimic a module
    """
    project = tmp_path / "static_module"
    project.mkdir()
    (project / "examples").mkdir()
    (project / "examples" / "Example_Notebook_0.ipynb").write_text(EXAMPLE_0_CONTENT)
    (project / "examples" / "Example_Notebook_1.ipynb").write_text(EXAMPLE_1_CONTENT)
    (project / "examples" / "data").mkdir()
    (project / "examples" / "data" / "data_0.csv").write_text(DATA_FILE_0_CONTENT)
    (project / "examples" / "data" / "data_1.csv").write_text(DATA_FILE_1_CONTENT)
    return project

@pytest.fixture(autouse=True)
def monkeypatch_find_examples(monkeypatch, tmp_module):
    """Monkeypatching find examples to use a tmp examples.
    """
    def _find_examples(name):
        return os.path.join(str(tmp_module), "examples")
    monkeypatch.setattr(pyct.cmd, '_find_examples', _find_examples)

@pytest.fixture(scope='function')
def tmp_project(tmp_path):
    """
    This sets up a temporary directory structure meant to mimic the project.

    All test output should write to this project. and tmp_module should
    be treated as immutable. Since this is function-scoped, every test
    will have a clean slate.
    """
    project = tmp_path / "test_project"
    project.mkdir()
    path = str(project / "examples")
    pyct.cmd.examples(name="nbsite", path=path)
    return project

@pytest.fixture(scope='function')
def tmp_project_with_docs_skeleton(tmp_project):
    project = tmp_project
    (project / "doc").mkdir()
    (project / "doc" / "conf.py").write_text(CONF_CONTENT)
    (project / "doc" / "index.rst").write_text(INDEX_CONTENT)
    return project


def test_generate_rst(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project))
    assert (project / "doc" / "Example_Notebook_0.rst").is_file()
    assert (project / "doc" / "Example_Notebook_1.rst").is_file()

def test_generate_rst_with_skip_one_notebook(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*Notebook_0.*')
    assert not (project / "doc" / "Example_Notebook_0.rst").is_file()
    assert (project / "doc" / "Example_Notebook_1.rst").is_file()

def test_generate_rst_with_skip_list_of_notebooks(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*Notebook_0.*, .*Notebook_1.*')
    assert not (project / "doc" / "Example_Notebook_0.rst").is_file()
    assert not (project / "doc" / "Example_Notebook_1.rst").is_file()

def test_generate_rst_with_skip_glob_matching_both_notebooks(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*Example.*')
    assert not (project / "doc" / "Example_Notebook_0.rst").is_file()
    assert not (project / "doc" / "Example_Notebook_1.rst").is_file()

def test_generate_rst_with_skip_glob_matching_both_notebooks_undercase(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*example.*')
    assert not (project / "doc" / "Example_Notebook_0.rst").is_file()
    assert not (project / "doc" / "Example_Notebook_1.rst").is_file()

#### Don't need to do much testing of build it depends on sphinx
@pytest.mark.slow
def test_build(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Example_Notebook_0.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "Example_Notebook_1.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "builtdocs" / "Example_Notebook_0.html").is_file()
    assert (project / "builtdocs" / "Example_Notebook_1.html").is_file()

@pytest.mark.slow
def test_build_with_just_one_rst(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Example_Notebook_0.rst").write_text(EXAMPLE_0_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "builtdocs" / "Example_Notebook_0.html").is_file()
    assert not (project / "builtdocs" / "Example_Notebook_1.html").is_file()
    assert not (project / "builtdocs" / ".nojekyll").is_file()

@pytest.mark.slow
def test_build_with_for_github_and_just_one_rst(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Example_Notebook_0.rst").write_text(EXAMPLE_0_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='', for_github=True)
    assert (project / "builtdocs" / "Example_Notebook_0.html").is_file()
    assert (project / "builtdocs" / ".nojekyll").is_file()
