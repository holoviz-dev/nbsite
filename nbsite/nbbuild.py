"""
Copyright (c) 2017-2021 HoloViz developers.

Copyright (c) 2013 Nathan Goldbaum. All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are
met:

   * Redistributions of source code must retain the above copyright
notice, this list of conditions and the following disclaimer.
   * Redistributions in binary form must reproduce the above
copyright notice, this list of conditions and the following disclaimer
in the documentation and/or other materials provided with the
distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS
"AS IS" AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT
LIMITED TO, THE IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR
A PARTICULAR PURPOSE ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT
OWNER OR CONTRIBUTORS BE LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL,
SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT
LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES; LOSS OF USE,
DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON ANY
THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
"""

import os, string, glob, copy, re, sys, shutil

import nbformat

from docutils.parsers.rst import directives, Directive
from docutils.statemachine import string2lines
from docutils.utils import new_document
from myst_nb.parser import nb_to_tokens, nb_output_to_disc, tokens_to_docutils

from nbconvert import NotebookExporter, PythonExporter
from nbconvert.preprocessors import (
    ExecutePreprocessor, CellExecutionError, Preprocessor
)
from .cmd import hosts, _prepare_paths

NOTEBOOK_VERSION = 4

interactivity_warning_binder = """
This web page was generated from a Jupyter notebook and not all 
interactivity will work on this website. <a
href="{download_link}">Right-click to download and run</a> or <a 
href="{binder_link}">Launch on Binder</a> for full Python-backed 
interactivity.
"""

interactivity_warning = """
This web page was generated from a Jupyter notebook and not all 
interactivity will work on this website. <a 
href="{download_link}">Right click to download and run locally</a> for full 
Python-backed interactivity.
"""

#from nbformat.v4 import output_from_msg
class ExecutePreprocessor1000(ExecutePreprocessor):
    """Sigh"""
    _ipython_startup = None
    @property
    def kc(self):
        return self._kc

    @kc.deleter
    def kc(self):
        del self._kc

    @kc.setter
    def kc(self,v):
        self._kc=v
        if self._ipython_startup is not None:
            msg_id = self._kc.execute( # noqa: a mess
                self._ipython_startup,silent=False,store_history=False,allow_stdin=False,stop_on_error=True)


    def handle_comm_msg(self, outs, msg, cell_index):
        """
        Comm messages are not handled correctly in some cases so we
        just ignore them during export.
        """
        pass


class SkipOutput(Preprocessor):
    """A transformer to skip the output for cells containing a certain string"""

    def __init__(self, substring=None, **kwargs):
        self.substring = substring
        super(SkipOutput, self).__init__(**kwargs)

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            if self.substring in cell['source']:
                cell['outputs'] = []
        return cell, resources

    def __call__(self, nb, resources):
        return self.preprocess(nb,resources)


class NotebookSlice(Preprocessor):
    """A transformer to select a slice of the cells of a notebook"""


    def __init__(self, substring=None, end=None, offset=0, **kwargs):
        self.substring = substring
        self.end = end
        self.offset = offset
        super(NotebookSlice, self).__init__(**kwargs)

    def _find_slice(self, nbc, substring, endstr):
        start = 0 if substring is None else None
        end = None
        try:
            end = int(endstr)
            count = 0
        except:
            count = None

        for ind, cell in enumerate(nbc.cells):
            source = cell['source']
            if start is None and substring in source:
                start = ind
            if None not in [start, count]:
                if end is not None and count >= end:
                    end = ind
                    break
                count += 1
            elif start is not None:
                if endstr is None:
                    break
                elif endstr in source:
                    end = ind + 1
                    break

        if start is None:
            raise Exception('Invalid notebook slice start')
        if end is None and endstr is not None:
            raise Exception('Invalid notebook slice end string match')

        return (max([start,self.offset]),end)

    def preprocess(self, nb, resources):
        nbc = copy.deepcopy(nb)
        start,end = self._find_slice(nbc, self.substring, self.end)
        nbc.cells = nbc.cells[start:end]
        return nbc, resources

    def __call__(self, nb, resources):
        return self.preprocess(nb,resources)


class FixNotebookLinks(Preprocessor):
    """
    Fixes relative notebook links by pointing to ReST or Markdown
    source files and if necessary stripping leading numbering
    (e.g. 0_notebook.ipynb) which are stripped by the generate-rst
    script.
    """

    file_types = ['rst', 'md']

    def __init__(self, nb_path, **kwargs):
        self.nb_path = nb_path
        super(FixNotebookLinks, self).__init__(**kwargs)

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] != 'markdown':
            return cell, resources
        matches = re.findall('\[.+\]\((.+\.ipynb)\)', cell['source'])
        for match in matches:
            for ft in self.file_types:
                file_path = os.path.join(self.nb_path, match[:-5] + ft)
                if os.path.isfile(file_path):
                    cell['source'] = cell['source'].replace(
                        '(%s)' % match, '(%s)' % (match[:-5] + ft)
                    )
                    break

                # Try unnumbered path
                num_name = os.path.basename(file_path)
                name = re.split(r"^\d+( |-|_)", num_name)[-1]
                unnumbered_path = file_path.replace(num_name, name)
                if os.path.isfile(unnumbered_path):
                    cell['source'] = cell['source'].replace(
                        '(%s)' % match, '(%s)' % name
                    )
                    break
        return cell, resources

    def __call__(self, nb, resources):
        return self.preprocess(nb,resources)


class FixBackticksInDetails(Preprocessor):
    """A preprocessor to make backticks in details cells work."""

    def comment_out_details(self, source):
        """
        Given the source of a cell, comment out  any lines that contain <details>
        """
        filtered = []
        for line in source.splitlines():
            if "details>" in line:
                line ='<!--' + line + '-->'
            filtered.append(line)
        return '\n'.join(filtered)

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'markdown':
            if '<details>' in cell['source'] and "```" in cell['source']:
                cell['source'] = self.comment_out_details(cell['source'])
        return cell, resources

    def __call__(self, nb, resources):
        return self.preprocess(nb,resources)


def get_download_link(relpath, org, branch, repo, examples, host):
    info = (hosts[host], org, repo, branch, examples, relpath)
    return '%s/%s/%s/%s/%s/%s' % info


def get_binder_link(relpath, org, repo, branch, examples):
    # SVG logo: https://mybinder.org/badge_logo.svg
    url="https://mybinder.org/v2/gh/{org}/{repo}/{branch}?filepath={examples}/{relpath}"
    return  url.format(org=org,repo=repo,branch=branch,relpath=relpath,examples=examples)


def formatted_link(path):
    return "`%s <%s>`__" % (os.path.basename(path), path)


def nb_to_python(nb_path):
    """convert notebook to python script"""
    exporter = PythonExporter()
    output, resources = exporter.from_filename(nb_path)
    return output


def evaluate_notebook(nb_path, dest_path=None, skip_exceptions=False,
                      skip_execute=None, timeout=300, ipython_startup=None,
                      patterns_to_take_with_me=None):

    if patterns_to_take_with_me is None:
        patterns_to_take_with_me = []

    notebook = nbformat.read(nb_path, as_version=4)
    kwargs = dict(timeout=timeout,
                  kernel_name='python%s'%sys.version_info[0],
                  allow_errors=skip_exceptions)

    cwd = os.getcwd()
    filedir, filename = os.path.split(nb_path)
    os.chdir(filedir)
    not_nb_runner = ExecutePreprocessor1000(**kwargs)
    if ipython_startup is not None:
        not_nb_runner._ipython_startup = ipython_startup

    if not os.path.isfile(dest_path):
        print('INFO: Writing evaluated notebook to {dest_path!s}'.format(
            dest_path=os.path.abspath(dest_path)))
        try:
            if not skip_execute:
                not_nb_runner.preprocess(notebook,{})
        except CellExecutionError as e:
            print('')
            print(e)
        os.chdir(cwd)

        if skip_execute:
            nbformat.write(notebook, open(dest_path, 'w'))
        else:
            ne = NotebookExporter()
            newnb, _ = ne.from_notebook_node(notebook)
            with open(dest_path,'w') as f:
                f.write(newnb)
            for pattern in patterns_to_take_with_me:
                for f in glob.glob(os.path.join(os.path.dirname(nb_path),pattern)):
                    print("mv %s %s"%(f, os.path.dirname(dest_path)))
                    shutil.move(f,os.path.dirname(dest_path))
    else:
        print('INFO: Skipping existing evaluated notebook {dest_path!s}'.format(
            dest_path=os.path.abspath(dest_path)))


def render_notebook(nb_path, document, preprocessors=[]):
    env = document.settings.env
    doc = new_document(nb_path, document.settings)

    with open(nb_path, encoding='utf-8') as f:
        text = f.read()

    ntbk = nbformat.reads(text, as_version=NOTEBOOK_VERSION)

    for preprocessor in preprocessors:
        ntbk, _ = preprocessor(ntbk, {})

    md_parser, env, tokens = nb_to_tokens(
        ntbk,
        env.myst_config,
        env.config["nb_render_plugin"],
    )

    # Delete rst temporarily to ensure 
    rst_path = nb_path[:-5]+'rst'
    if os.path.isfile(rst_path):
        with open(rst_path) as f:
            rst_text = f.read()
        os.remove(rst_path)
    else:
        rst_text = None

    nb_output_to_disc(ntbk, doc)

    if rst_text is not None:
        with open(rst_path, 'w') as f:
            f.write(rst_text)

    tokens_to_docutils(md_parser, env, tokens, doc)

    return doc.children[1:]


class NotebookDirective(Directive):
    """Insert an evaluated notebook into a document

    This uses runipy and nbconvert to transform a path to an unevaluated notebook
    into html suitable for embedding in a Sphinx document.
    """
    required_arguments = 2
    optional_arguments = 6
    option_spec = {
        'skip_exceptions' : directives.flag,
        'substring': str,
        'end': str,
        'skip_execute': bool,
        'skip_output': str,
        'offset': int,
        'disable_interactivity_warning': bool
    }

    def link_rst(self, nb_basename, nb_abs_path, dest_path):
        # Process file inclusion options
        include_opts = self.arguments[2:]
        include_nb = True if 'ipynb' in include_opts else False
        include_script = True if 'py' in include_opts else False

        link_rst = ''
        if len(include_opts):
            link_rst = 'Direct Downloads: ('

        if include_nb:
            link_rst += formatted_link(nb_basename) + '; '

        if include_script:
            dest_path_script = string.replace(dest_path, '.ipynb', '.py')
            rel_path_script = string.replace(nb_basename, '.ipynb', '.py')
            script_text = nb_to_python(nb_abs_path)
            f = open(dest_path_script, 'w')
            f.write(script_text.encode('utf8'))
            f.close()

            link_rst += formatted_link(rel_path_script)

        if len(include_opts):
            link_rst = ')'

        return link_rst

    def preprocessors(self, dest_dir):
        preprocessors = [FixBackticksInDetails(), FixNotebookLinks(dest_dir)]
        if self.options.get('substring') or self.options.get('offset'):
            preprocessors.append(
                NotebookSlice(
                    self.options.get('substring'),
                    self.options.get('end'),
                    self.options.get('offset')
                )
            )
        if self.options.get('skip_output'):
            preprocessors.append(SkipOutput(self.options['skip_output']))
        return preprocessors

    def interactivity_warning(self, nb_abs_path):        
        project_name = os.environ.get('PROJECT_NAME','')
        project_root = os.environ.get('PROJECT_ROOT','')
        host = os.environ.get('HOST','GitHub')
        branch = os.environ.get('BRANCH','master')
        repo = os.environ.get('REPO','')
        org = os.environ.get('ORG','')
        doc = os.environ.get('DOC','doc')
        examples = os.environ.get('EXAMPLES','examples')
        examples_assets = os.environ.get('EXAMPLES_ASSETS','assets')
        binder = os.environ.get('BINDER','none')

        if repo == '' or project_name == '':
            project_name = repo = project_name or repo
        if org == '':
            org = repo

        paths = _prepare_paths(project_root, examples=examples,
                               doc=doc, examples_assets=examples_assets)
        relpath = os.path.relpath(nb_abs_path, paths['examples'])
        dl_link = get_download_link(relpath, org, branch, repo, examples, host)
        binder_link = get_binder_link(relpath, org, repo, branch, examples)
        
        if binder == 'none':
            inner_msg = interactivity_warning.format(download_link=dl_link)
        else:
            inner_msg = interactivity_warning_binder.format(download_link=dl_link,
                                                            binder_link=binder_link)
        inner_msg = inner_msg.replace('\n', '')
        scroller = f'<div id="scroller-right">{inner_msg}</div>'
        return f'\n.. raw:: html\n\n    {scroller}'

    def run(self):
        # check if raw html is supported
        if not self.state.document.settings.raw_enabled:
            raise self.warning('"%s" directive disabled.' % self.name)

        # Process paths and directories
        #project = self.arguments[0].lower()
        rst_file = os.path.abspath(self.state.document.current_source)
        rst_dir = os.path.dirname(rst_file)
        nb_abs_path = os.path.abspath(os.path.join(rst_dir, self.arguments[1]))
        nb_filepath, nb_basename = os.path.split(nb_abs_path)

        dest_dir = rst_dir
        dest_path = os.path.join(dest_dir, nb_basename)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # Evaluate Notebook and insert into Sphinx doc
        evaluate_notebook(
            nb_abs_path, dest_path,
            skip_exceptions='skip_exceptions' in self.options,
            skip_execute=self.options.get('skip_execute'),
            timeout=setup.config.nbbuild_cell_timeout,
            ipython_startup=setup.config.nbbuild_ipython_startup,
            patterns_to_take_with_me=setup.config.nbbuild_patterns_to_take_along
        )

        preprocessors = self.preprocessors(dest_dir)
        rendered_nodes = render_notebook(
            dest_path, self.state.document, preprocessors
        )
        
        link_rst = self.link_rst(nb_basename, nb_abs_path, dest_path)
        if not ('disable_interactivity_warning' in self.options):
            link_rst += self.interactivity_warning(nb_abs_path)

        # Insert evaluated notebook HTML into Sphinx
        if link_rst:
            include_lines = string2lines(link_rst, convert_whitespace=True)
            self.state_machine.insert_input(include_lines, rst_file)

        # add dependency
        self.state.document.settings.record_dependencies.add(nb_abs_path)

        # TODO: doubt this isdoing anyting
        # clean up png files left behind by notebooks.
        png_files = glob.glob("*.png")
        for file in png_files:
            os.remove(file)

        return rendered_nodes


def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir

    app.add_config_value('nbbuild_cell_timeout',300,'html')
    app.add_config_value('nbbuild_ipython_startup',"from nbsite.ipystartup import *",'html')
    app.add_config_value('nbbuild_patterns_to_take_along',["*.json", "json_*"],'html')

    app.add_directive('notebook', NotebookDirective)
