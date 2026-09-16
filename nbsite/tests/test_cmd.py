import json
import shutil

from collections import Counter

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

CONF_RECORD_EVALUATED_CONTENT = u"""
import os

from nbsite.shared_conf import *
from nbsite.shared_conf import setup as _shared_setup


def _record_evaluated(app, docname, source):
    evaluated = sorted(f for f in os.listdir(app.srcdir) if f.endswith(".ipynb"))
    with open(os.path.join(app.srcdir, "..", "read_sources.txt"), "a") as f:
        f.write(docname + ":" + ",".join(evaluated) + "\\n")


def setup(app):
    _shared_setup(app)
    app.connect("source-read", _record_evaluated)
"""

CONF_RECORD_TOCTREE_CONTENT = u"""
import os

import pydata_sphinx_theme.toctree as _toctree

from nbsite.shared_conf import *

_add_toctree_functions = _toctree.add_toctree_functions


def _recording_add_toctree_functions(app, pagename, templatename, context, doctree):
    _add_toctree_functions(app, pagename, templatename, context, doctree)
    generate_toctree_html = context["generate_toctree_html"]

    def recording_generate_toctree_html(*args, **kwargs):
        with open(os.path.join(app.srcdir, "..", "toctree_calls.txt"), "a") as f:
            f.write(pagename + "\\n")
        return generate_toctree_html(*args, **kwargs)

    context["generate_toctree_html"] = recording_generate_toctree_html


_toctree.add_toctree_functions = _recording_add_toctree_functions
"""

CODE_NOTEBOOK_CONTENT = u"""{
 "cells": [
  {
   "cell_type": "code",
   "execution_count": null,
   "metadata": {},
   "outputs": [],
   "source": [
    "print('executed')"
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

def _embed_notebook(delay_before_write):
    source = [
        "import os, time, uuid\n",
        "path = os.path.join(os.environ.get('PANEL_EMBED_SAVE_PATH', './'), 'json_' + uuid.uuid4().hex)\n",
        "os.makedirs(path)\n",
        f"time.sleep({delay_before_write})\n",
        "with open(os.path.join(path, '0.json'), 'w') as f:\n",
        "    f.write('{}')\n",
        "print(os.path.basename(path))",
    ]
    return json.dumps({
        "cells": [{
            "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source,
        }],
        "metadata": {"language_info": {"name": "python", "pygments_lexer": "ipython3"}},
        "nbformat": 4,
        "nbformat_minor": 2,
    })


def _code_notebook(source):
    return json.dumps({
        "cells": [{
            "cell_type": "code", "execution_count": None, "metadata": {}, "outputs": [], "source": source,
        }],
        "metadata": {"language_info": {"name": "python", "pygments_lexer": "ipython3"}},
        "nbformat": 4,
        "nbformat_minor": 2,
    })


def _notebook_rst(title, notebook):
    return f"""
{'*' * len(title)}
{title}
{'*' * len(title)}

.. notebook:: test_project ../examples/{notebook}
    :offset: 0
"""


CODE_NOTEBOOK_SKIP_EXECUTE_RST = u"""
*************
Code Notebook
*************

.. notebook:: test_project ../examples/Code_Notebook.ipynb
    :offset: 0
    :skip_execute: True
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
def test_build_evaluates_notebooks_before_reading_sources(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "conf.py").write_text(CONF_RECORD_EVALUATED_CONTENT)
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    read_sources = (project / "read_sources.txt").read_text().splitlines()
    assert sorted(read_sources) == [
        "First_Notebook:0_Zeroth_Notebook.ipynb,1_First_Notebook.ipynb",
        "Zeroth_Notebook:0_Zeroth_Notebook.ipynb,1_First_Notebook.ipynb",
        "index:0_Zeroth_Notebook.ipynb,1_First_Notebook.ipynb",
    ]

@pytest.mark.slow
def test_build_keeps_json_of_notebooks_in_the_same_directory_evaluated_together(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    # The quick notebook finishes while the slow one is still writing its json
    (project / "examples" / "Embed_Quick.ipynb").write_text(_embed_notebook(0))
    (project / "examples" / "Embed_Slow.ipynb").write_text(_embed_notebook(4))
    (project / "doc" / "Embed_Quick.rst").write_text(_notebook_rst("Embed Quick", "Embed_Quick.ipynb"))
    (project / "doc" / "Embed_Slow.rst").write_text(_notebook_rst("Embed Slow", "Embed_Slow.ipynb"))
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    for name in ("Embed_Quick", "Embed_Slow"):
        evaluated = json.loads((project / "doc" / f"{name}.ipynb").read_text())
        outputs = evaluated["cells"][0]["outputs"]
        assert [o["output_type"] for o in outputs] == ["stream"]
        json_dir = "".join(outputs[0]["text"]).strip()
        assert (project / "doc" / json_dir / "0.json").is_file()
        assert (project / "builtdocs" / json_dir / "0.json").is_file()
    assert not list((project / "examples").glob("json_*"))

def _sidebar_navs(builtdocs):
    navs = {}
    for page in sorted(builtdocs.rglob("*.html")):
        text = page.read_text()
        start = text.find('<nav class="bd-docs-nav bd-links"')
        navs[page.relative_to(builtdocs).as_posix()] = text[start:text.find("</nav>", start)] if start != -1 else None
    return navs


NESTED_TOCTREE_PAGES = {
    "index.rst": "Project\n=======\n\n.. toctree::\n\n   a\n   b/index\n   c\n   b/b2/deep\n",
    "a.rst": "A\n=\n",
    "c.rst": "C\n=\n",
    "b/index.rst": "B\n=\n\n.. toctree::\n\n   b2/index\n",
    "b/b2/index.rst": "B2\n==\n\n.. toctree::\n\n   deep\n",
    "b/b2/deep.rst": "Deep\n====\n",
}

@pytest.mark.slow
def test_build_resolves_toctree_entries_once(tmp_project_with_docs_skeleton, monkeypatch):
    from sphinx.environment.adapters import toctree

    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)

    resolved, nested = [], []
    entries_from_toctree = toctree._entries_from_toctree

    def recording_entries_from_toctree(*args, **kwargs):
        if not nested:
            resolved.append(args)
        nested.append(True)
        try:
            return entries_from_toctree(*args, **kwargs)
        finally:
            nested.pop()

    monkeypatch.setattr(toctree, "_entries_from_toctree", recording_entries_from_toctree)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='', disable_parallel=True)
    assert len(resolved) == 1

@pytest.mark.slow
@pytest.mark.parametrize("navigation_depth", [1, 2, 4])
def test_build_sidebar_of_nested_toctree_is_the_same_without_toctree_cache(tmp_path, navigation_depth):
    theme_options = f'html_theme_options = {{**html_theme_options, "navigation_depth": {navigation_depth}}}\n'
    builtdocs = {}
    for name, extra_conf in [("cached", ""), ("uncached", "nbsite_cache_toctree = False\n")]:
        project = tmp_path / name
        for page, content in NESTED_TOCTREE_PAGES.items():
            (project / "doc" / page).parent.mkdir(parents=True, exist_ok=True)
            (project / "doc" / page).write_text(content)
        (project / "examples").mkdir()
        (project / "doc" / "conf.py").write_text(CONF_CONTENT + theme_options + extra_conf)
        build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
        builtdocs[name] = project / "builtdocs"

    navs = _sidebar_navs(builtdocs["cached"])
    assert 'current' in navs["b/b2/deep.html"]
    assert navs == _sidebar_navs(builtdocs["uncached"])

@pytest.mark.slow
def test_build_with_a_page_listed_twice_in_the_toctree(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    index = INDEX_CONTENT.replace(
        "   First Notebook <First_Notebook>",
        "   First Notebook <First_Notebook>\n   First Notebook Again <First_Notebook>",
    )
    (project / "doc" / "index.rst").write_text(index)
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    navs = _sidebar_navs(project / "builtdocs")
    assert navs["First_Notebook.html"].count('class="current') >= 1
    assert navs["Zeroth_Notebook.html"]

@pytest.mark.slow
def test_build_copies_the_toctree_once(tmp_project_with_docs_skeleton, monkeypatch):
    from sphinx.environment.adapters import toctree

    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)

    copied = []
    toctree_copy = toctree._toctree_copy

    def recording_toctree_copy(node, *args, **kwargs):
        if node.get("toctree"):
            copied.append(node)
        return toctree_copy(node, *args, **kwargs)

    monkeypatch.setattr(toctree, "_toctree_copy", recording_toctree_copy)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='', disable_parallel=True)
    assert len(copied) == 1

@pytest.mark.slow
def test_build_sidebar_is_the_same_without_toctree_cache(tmp_project_with_docs_skeleton, tmp_path):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    uncached = tmp_path / "uncached_project"
    shutil.copytree(project, uncached)
    (uncached / "doc" / "conf.py").write_text(CONF_CONTENT + "nbsite_cache_toctree = False\n")

    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    build('html', str(uncached / "builtdocs"), project_root=str(uncached), examples_assets='')

    navs = _sidebar_navs(project / "builtdocs")
    assert navs["Zeroth_Notebook.html"]
    assert navs == _sidebar_navs(uncached / "builtdocs")

@pytest.mark.slow
def test_build_keeps_existing_json_next_to_notebooks(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "examples" / "data.json").write_text('{"value": 1}')
    source = [
        "import json\n",
        "with open('data.json') as f:\n",
        "    data = json.load(f)\n",
        "with open('created.json', 'w') as f:\n",
        "    json.dump(data, f)",
    ]
    (project / "examples" / "Json_Notebook.ipynb").write_text(_code_notebook(source))
    (project / "doc" / "Json_Notebook.rst").write_text(_notebook_rst("Json Notebook", "Json_Notebook.ipynb"))
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert (project / "examples" / "data.json").is_file()
    assert not (project / "examples" / "created.json").exists()
    assert (project / "doc" / "created.json").is_file()

@pytest.mark.slow
def test_build_does_not_evaluate_notebooks_in_a_pool_with_one_process(tmp_project_with_docs_skeleton, monkeypatch):
    from nbsite import nbbuild

    project = tmp_project_with_docs_skeleton
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)

    pools = []
    process_pool_executor = nbbuild.ProcessPoolExecutor

    def recording_process_pool_executor(*args, **kwargs):
        pools.append(kwargs)
        return process_pool_executor(*args, **kwargs)

    monkeypatch.setattr(nbbuild, "ProcessPoolExecutor", recording_process_pool_executor)
    monkeypatch.setattr("nbsite.cmd.os.cpu_count", lambda: 1)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    assert pools == []
    assert (project / "doc" / "0_Zeroth_Notebook.ipynb").is_file()

@pytest.mark.slow
def test_build_generates_sidebar_navigation_once_per_page(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "doc" / "conf.py").write_text(CONF_RECORD_TOCTREE_CONTENT)
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    calls = Counter((project / "toctree_calls.txt").read_text().splitlines())
    assert {"index", "Zeroth_Notebook", "First_Notebook"} <= set(calls)
    assert set(calls.values()) == {1}

@pytest.mark.slow
def test_build_with_sidebar_nav_bs_alt_template(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    conf = CONF_CONTENT + 'html_sidebars = {"**": ["sidebar-nav-bs-alt"]}\n'
    (project / "doc" / "conf.py").write_text(conf)
    (project / "doc" / "Zeroth_Notebook.rst").write_text(EXAMPLE_0_RST)
    (project / "doc" / "First_Notebook.rst").write_text(EXAMPLE_1_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    html = (project / "builtdocs" / "Zeroth_Notebook.html").read_text()
    assert 'class="bd-docs-nav bd-links"' in html
    assert 'href="First_Notebook.html"' in html

@pytest.mark.slow
def test_build_does_not_execute_notebook_with_skip_execute(tmp_project_with_docs_skeleton):
    project = tmp_project_with_docs_skeleton
    (project / "examples" / "Code_Notebook.ipynb").write_text(CODE_NOTEBOOK_CONTENT)
    (project / "doc" / "Code_Notebook.rst").write_text(CODE_NOTEBOOK_SKIP_EXECUTE_RST)
    build('html', str(project / "builtdocs"), project_root=str(project), examples_assets='')
    evaluated = json.loads((project / "doc" / "Code_Notebook.ipynb").read_text())
    assert evaluated["cells"][0]["outputs"] == []

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
