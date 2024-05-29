import json
import shutil

import pytest

from nbsite.cmd import build, generate_rst

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
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Here is a ref to another notebook with the [right number](0_Zeroth_Notebook.ipynb)."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Here is a ref to it with the [wrong number](1_Zeroth_Notebook.ipynb)."
   ]
  },
  {
   "cell_type": "markdown",
   "metadata": {},
   "source": [
    "Here is a ref to it with [no number](Zeroth_Notebook.ipynb)."
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

APPENDIX_0_CONTENT = u"""{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print('first cell')"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "import foo"
   ]
  },
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print('last cell')"
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

   Zeroth Notebook <Zeroth_Notebook>
   First Notebook <First_Notebook>
   Appendix 0 <Appendix_0>
"""

EXAMPLE_0_RST = u"""
***************
Zeroth Notebook
***************

.. notebook:: test_project ../examples/0_Zeroth_Notebook.ipynb
    :offset: 0
"""

EXAMPLE_1_RST = u"""
**************
First Notebook
**************

.. notebook:: test_project ../examples/1_First_Notebook.ipynb
    :offset: 0
"""

APPENDIX_0_RST = u"""
**********
Appendix 0
**********

.. notebook:: test_project ../examples/Appendix_0.ipynb
    :offset: 0
"""

@pytest.fixture(autouse=True)
def tmp_module(tmp_path):
    """This sets up a temporary directory structure meant to mimic a module
    """
    project = tmp_path / "static_module"
    project.mkdir()
    (project / "examples").mkdir()
    (project / "examples" / "0_Zeroth_Notebook.ipynb").write_text(EXAMPLE_0_CONTENT)
    (project / "examples" / "1_First_Notebook.ipynb").write_text(EXAMPLE_1_CONTENT)
    (project / "examples" / "Appendix_0.ipynb").write_text(APPENDIX_0_CONTENT)
    (project / "examples" / "data").mkdir()
    (project / "examples" / "data" / "data_0.csv").write_text(DATA_FILE_0_CONTENT)
    (project / "examples" / "data" / "data_1.csv").write_text(DATA_FILE_1_CONTENT)
    return project

@pytest.fixture(scope='function')
def tmp_project(tmp_path, tmp_module):
    """
    This sets up a temporary directory structure meant to mimic the project.

    All test output should write to this project. and tmp_module should
    be treated as immutable. Since this is function-scoped, every test
    will have a clean slate.
    """
    project = tmp_path / "test_project"
    project.mkdir()
    shutil.copytree(tmp_module, project, dirs_exist_ok=True)
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
    assert (project / "doc" / "Zeroth_Notebook.rst").is_file()
    assert (project / "doc" / "First_Notebook.rst").is_file()
    assert (project / "doc" / "Appendix_0.rst").is_file()

def test_generate_rst_with_skip_one_notebook(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*0_.*')
    assert not (project / "doc" / "Zeroth_Notebook.rst").is_file()
    assert (project / "doc" / "First_Notebook.rst").is_file()

def test_generate_rst_with_skip_list_of_notebooks(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*0_.*, .*1_.*')
    assert not (project / "doc" / "Zeroth_Notebook.rst").is_file()
    assert not (project / "doc" / "First_Notebook.rst").is_file()

def test_generate_rst_with_skip_glob_matching_both_notebooks(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*Notebook.*')
    assert not (project / "doc" / "Zeroth_Notebook.rst").is_file()
    assert not (project / "doc" / "First_Notebook.rst").is_file()

def test_generate_rst_with_skip_glob_matching_both_notebooks_undercase(tmp_project):
    project = tmp_project
    generate_rst("test_project", project_root=str(project), skip='.*notebook.*')
    assert not (project / "doc" / "Zeroth_Notebook.rst").is_file()
    assert not (project / "doc" / "First_Notebook.rst").is_file()


def test_generate_rst_with_keep_numbers(tmp_project):

    expected_index_toc = (
        '    Introduction <self>\n'
        '    0 Zeroth Notebook <0_Zeroth_Notebook>\n'
        '    1 First Notebook <1_First_Notebook>\n'
        '    Appendix 0 <Appendix_0>')

    project = tmp_project
    (project / "examples" / "index.ipynb").write_text(EXAMPLE_0_CONTENT)
    generate_rst("test_project", project_root=str(project), keep_numbers=True)
    assert (project / "doc" / "index.rst").is_file()
    assert expected_index_toc in (project / "doc" / "index.rst").read_text()
    assert (project / "doc" / "0_Zeroth_Notebook.rst").is_file()
    assert (project / "doc" / "1_First_Notebook.rst").is_file()

def test_generate_rst_with_strip_numbers_is_default(tmp_project):

    expected_index_toc = (
        '    Introduction <self>\n'
        '    Zeroth Notebook <Zeroth_Notebook>\n'
        '    First Notebook <First_Notebook>\n'
        '    Appendix 0 <Appendix_0>')

    project = tmp_project
    (project / "examples" / "index.ipynb").write_text(EXAMPLE_0_CONTENT)
    generate_rst("test_project", project_root=str(project))
    assert (project / "doc" / "index.rst").is_file()
    actual_index = (project / "doc" / "index.rst").read_text()
    assert expected_index_toc in actual_index
    assert (project / "doc" / "Zeroth_Notebook.rst").is_file()
    assert (project / "doc" / "First_Notebook.rst").is_file()

def test_generate_rst_with_nblink_as_none(tmp_project):

    expected = ['**************',
                'First Notebook',
                '**************',
                '', '.. notebook:: test_project ../examples/1_First_Notebook.ipynb',
                '    :offset: 0']
    project = tmp_project
    generate_rst("test_project", project_root=str(project), nblink='none',
                 host='GitHub', org='holoviz', repo='nbsite', branch='main')
    rstpath = (project / "doc" / "First_Notebook.rst")
    assert rstpath.is_file()
    with open(rstpath, 'r') as f:
        contents = f.read().splitlines()
        assert  contents[5:] == expected

def test_generate_rst_with_nblink_top(tmp_project):

    expected = ['**************',
                'First Notebook',
                '**************',
                '',
                '`Right click to download this notebook from GitHub. <https://raw.githubusercontent.com/holoviz/nbsite/main/examples/1_First_Notebook.ipynb>`_',
                '', '', '-------', '',
                '.. notebook:: test_project ../examples/1_First_Notebook.ipynb',
                '    :offset: 0']

    project = tmp_project
    generate_rst("test_project", project_root=str(project), nblink='top',
                 host='GitHub', org='holoviz', repo='nbsite', branch='main')
    rstpath = (project / "doc" / "First_Notebook.rst")
    assert rstpath.is_file()
    with open(rstpath, 'r') as f:
        contents = f.read().splitlines()
        assert  contents[5:] == expected

def test_generate_rst_with_nblink_both(tmp_project):

    expected = ['**************',
                'First Notebook',
                '**************',
                '',
                '`Right click to download this notebook from GitHub. <https://raw.githubusercontent.com/holoviz/nbsite/main/examples/1_First_Notebook.ipynb>`_',
                '', '', '-------', '',
                '.. notebook:: test_project ../examples/1_First_Notebook.ipynb',
                '    :offset: 0',
                '', '', '-------', '',
                '`Right click to download this notebook from GitHub. <https://raw.githubusercontent.com/holoviz/nbsite/main/examples/1_First_Notebook.ipynb>`_']

    project = tmp_project
    generate_rst("test_project", project_root=str(project), nblink='both',
                 host='GitHub', org='holoviz', repo='nbsite', branch='main')
    rstpath = (project / "doc" / "First_Notebook.rst")
    assert rstpath.is_file()
    with open(rstpath, 'r') as f:
        contents = f.read().splitlines()
        assert  contents[5:] == expected

def test_generate_rst_with_nblink_bottom(tmp_project):

    expected = ['**************',
                'First Notebook',
                '**************',
                '',
                '.. notebook:: test_project ../examples/1_First_Notebook.ipynb',
                '    :offset: 0',
                '', '', '-------', '',
                '`Right click to download this notebook from GitHub. <https://raw.githubusercontent.com/holoviz/nbsite/main/examples/1_First_Notebook.ipynb>`_']

    project = tmp_project
    generate_rst("test_project", project_root=str(project), nblink='bottom',
                 host='GitHub', org='holoviz', repo='nbsite', branch='main')
    rstpath = (project / "doc" / "First_Notebook.rst")
    assert rstpath.is_file()
    with open(rstpath, 'r') as f:
        contents = f.read().splitlines()
        assert  contents[5:] == expected

def test_generate_rst_with_no_nblink_set_defaults_to_bottom(tmp_project):
    expected = ['**************',
                'First Notebook',
                '**************',
                '',
                '.. notebook:: test_project ../examples/1_First_Notebook.ipynb',
                '    :offset: 0',
                '', '', '-------', '',
                '`Right click to download this notebook from GitHub. <https://raw.githubusercontent.com/holoviz/nbsite/main/examples/1_First_Notebook.ipynb>`_']

    project = tmp_project
    generate_rst("test_project", project_root=str(project),
                 host='GitHub', org='holoviz', repo='nbsite', branch='main')
    rstpath = (project / "doc" / "First_Notebook.rst")
    assert rstpath.is_file()
    with open(rstpath, 'r') as f:
        contents = f.read().splitlines()
        assert  contents[5:] == expected

#### Don't need to do much testing of build it depends on sphinx
@pytest.mark.slow
def test_build(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "doc" / "0_Zeroth_Notebook.ipynb").is_file()
    assert (project / "doc" / "1_First_Notebook.ipynb").is_file()
    assert (project / "builtdocs" / "Zeroth_Notebook.html").is_file()
    assert (project / "builtdocs" / "First_Notebook.html").is_file()

@pytest.mark.slow
def test_build_with_nblink_at_top_succeeds(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    generate_rst("test_project", project_root=str(project), nblink='top',
                 host='GitHub', org='holoviz', repo='nbsite', branch='main')
    rstpath = (project / "doc" / "First_Notebook.rst")
    assert rstpath.is_file()
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "builtdocs" / "First_Notebook.html").is_file()
    html = (project / "builtdocs" / "First_Notebook.html").read_text()
    assert 'This is another temporary notebook that gets created for tests' in html, \
           "The notebook did not get build to html properly - look for sphinx warnings and errors"

@pytest.mark.slow
def test_build_with_just_one_rst(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "builtdocs" / "Zeroth_Notebook.html").is_file()
    assert not (project / "builtdocs" / "First_Notebook.html").is_file()
    assert (project / "builtdocs" / ".nojekyll").is_file()

@pytest.mark.slow
def test_build_deletes_by_default(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert not (project / "builtdocs" / ".doctrees").is_dir()
    assert (project / "builtdocs" / "First_Notebook.html").is_file()
    # Used to test for 10, bumped to 11 as the sphinx-design extension
    # adds a `_sphinx_design_static` folder in `builtdocs/`.
    # Further incremented when sphinx-rediraffe was added as it adds _rediraffe_redirected.json
    assert len(list((project / "builtdocs").iterdir())) == 12

@pytest.mark.slow
def test_build_with_clean_dry_run_does_not_delete(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='', clean_dry_run=True)
    assert (project / "builtdocs" / ".doctrees").is_dir()
    assert (project / "builtdocs" / "First_Notebook.html").is_file()
    # Used to test for 12, bumped to 13 as the sphinx-design extension
    # adds a `_sphinx_design_static` folder in `builtdocs/`.
    # Further incremented when sphinx-rediraffe was added as it adds _rediraffe_redirected.json
    assert len(list((project / "builtdocs").iterdir())) == 14

@pytest.mark.slow
def test_build_copies_json(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "example_json_blob.json").write_text("some json")
    (project / "doc" / "topics").mkdir()
    (project / "doc" / "topics" / "nested_example_json_blob.json").write_text("some json")
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "builtdocs" / "example_json_blob.json").is_file()
    assert (project / "builtdocs" / "topics").is_dir()
    assert (project / "builtdocs" / "topics" / "nested_example_json_blob.json").is_file()

@pytest.mark.slow
def test_build_with_error_output(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    (project / "doc" / "Appendix_0.rst").write_text(APPENDIX_0_RST)
    assert not (project / "doc" / "Appendix_0.ipynb").is_file()
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "doc" / "1_First_Notebook.ipynb").is_file()
    assert (project / "doc" / "Appendix_0.ipynb").is_file()
    nb = json.loads((project / "doc" / "Appendix_0.ipynb").read_text())
    assert nb['cells'][1]['outputs'][0]['ename'] == 'ModuleNotFoundError'
    assert len(nb['cells'][2]['outputs']) == 0

@pytest.mark.slow
def test_build_with_fixes_links(tmp_project):
    project = tmp_project
    (project / "doc").mkdir()
    (project / "doc" / "conf.py").write_text(CONF_CONTENT)
    (project / "examples" / "index.ipynb").write_text(EXAMPLE_0_CONTENT)
    generate_rst("test_project", project_root=str(project))
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "doc" / "1_First_Notebook.ipynb").is_file()
    assert (project / "builtdocs" / "First_Notebook.html").is_file()
    html = (project / "builtdocs" / "First_Notebook.html").read_text()
    assert '<a class="reference internal" href="Zeroth_Notebook.html"><span class="std std-doc">right number' in html
    assert '<a class="reference internal" href="Zeroth_Notebook.html"><span class="std std-doc">wrong number' in html
    assert '<a class="reference internal" href="Zeroth_Notebook.html"><span class="std std-doc">no number' in html

@pytest.mark.slow
def test_build_cell_content_displayed_as_html(tmp_project):
    project = tmp_project
    (project / "doc").mkdir()
    (project / "doc" / "conf.py").write_text(CONF_CONTENT)
    (project / "examples" / "index.ipynb").write_text(EXAMPLE_0_CONTENT)
    generate_rst("test_project", project_root=str(project))
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "doc" / "1_First_Notebook.ipynb").is_file()
    assert (project / "builtdocs" / "First_Notebook.html").is_file()
    html = (project / "builtdocs" / "First_Notebook.html").read_text()
    # Small check to ensure cells are parsed and injected in the HTML output
    assert '<p>Here is a ref to another notebook with the <a class="reference internal" href="Zeroth_Notebook.html"><span class="std std-doc">right number</span></a>.</p>' in html  # noqa

@pytest.mark.slow
def test_build_with_keep_numbers_passes_even_when_link_target_does_not_exist(tmp_project):
    project = tmp_project
    (project / "doc").mkdir()
    (project / "doc" / "conf.py").write_text(CONF_CONTENT)
    (project / "examples" / "index.ipynb").write_text(EXAMPLE_0_CONTENT)
    generate_rst("test_project", project_root=str(project), keep_numbers=True)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "doc" / "1_First_Notebook.ipynb").is_file()
    assert (project / "builtdocs" / "1_First_Notebook.html").is_file()
    html = (project / "builtdocs" / "1_First_Notebook.html").read_text()
    assert '<a class="reference internal" href="0_Zeroth_Notebook.html"><span class="std std-doc">right number' in html
    assert '<span class="xref myst">wrong number</span>' in html
    assert '<span class="xref myst">no number</span>' in html
