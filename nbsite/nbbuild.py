"""
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

import os, string, glob, re, copy, ast, sys

from sphinx.util.compat import Directive
from docutils import nodes
from docutils.parsers.rst import directives
from IPython.nbconvert import html, python
from IPython.nbformat.current import read, write

import nbconvert
import nbformat
from nbconvert.preprocessors import ExecutePreprocessor, CellExecutionError


from nbformat.v4 import output_from_msg
class ExecutePreprocessor1000(ExecutePreprocessor):
    """Sigh"""
    _ipython_startup = None
    @property
    def kc(self):
        return self._kc

    @kc.setter
    def kc(self,v):
        self._kc=v
        if self._ipython_startup is not None:
            msg_id = self._kc.execute(
                self._ipython_startup,silent=False,store_history=False,allow_stdin=False,stop_on_error=True)
# you can attempt to debug your startup code with this hack...            
#            exec_reply = self._wait_for_reply(msg_id, self._ipython_startup)
#            while True:
#                msg = self.kc.iopub_channel.get_msg()
#                if msg['parent_header'].get('msg_id') != msg_id:
#                    continue
#                else:
#                    try:
#                        output = output_from_msg(msg)
#                    except:
#                        continue
#                    if output.output_type == 'error':
#                        raise ValueError("Startup code failed: %s %s\n%s"%(output.ename,output.evalue,output.traceback))
#                    break


try:
    from nbconvert.preprocessors import Preprocessor
except ImportError:
    try:
        from IPython.nbconvert.preprocessors import Preprocessor
    except ImportError:
        # IPython < 2.0
        from IPython.nbconvert.transformers import Transformer as Preprocessor


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


    def __call__(self, nb, resources): return self.preprocess(nb,resources)


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

    def __call__(self, nb, resources): return self.preprocess(nb,resources)


class NotebookDirective(Directive):
    """Insert an evaluated notebook into a document

    This uses runipy and nbconvert to transform a path to an unevaluated notebook
    into html suitable for embedding in a Sphinx document.
    """
    required_arguments = 2
    optional_arguments = 6
    option_spec = {'skip_exceptions' : directives.flag,
                   'substring':str, 'end':str,
                   'skip_execute':bool, 'skip_output':str, 'offset':int}

    def run(self):
        # check if raw html is supported
        if not self.state.document.settings.raw_enabled:
            raise self.warning('"%s" directive disabled.' % self.name)

        # Process paths and directories
        project = self.arguments[0].lower()
        rst_file = os.path.abspath(self.state.document.current_source)
        rst_dir = os.path.dirname(rst_file)
        nb_abs_path = os.path.abspath(os.path.join(rst_dir, self.arguments[1]))
        nb_filepath, nb_basename = os.path.split(nb_abs_path)

        rel_dir = os.path.relpath(rst_dir, setup.confdir)
        dest_dir = os.path.join(setup.app.builder.outdir, rel_dir)
        dest_path = os.path.join(dest_dir, nb_basename)

        if not os.path.exists(dest_dir):
            os.makedirs(dest_dir)

        # Process file inclusion options
        include_opts = self.arguments[2:]
        include_nb = True if 'ipynb' in include_opts else False
        include_eval = True if 'eval' in include_opts else False
        include_script = True if 'py' in include_opts else False

        link_rst = ''
        if len(include_opts):
            link_rst = 'Direct Downloads: ('

        if include_nb:
            link_rst += formatted_link(nb_basename) + '; '

        if include_eval:
            dest_path_eval = string.replace(dest_path, '.ipynb', '_evaluated.ipynb')
            rel_path_eval = string.replace(nb_basename, '.ipynb', '_evaluated.ipynb')
            link_rst += formatted_link(rel_path_eval) + ('; ' if include_script else '')
        else:
            dest_path_eval = os.path.join(dest_dir, 'temp_evaluated.ipynb')

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

        # Evaluate Notebook and insert into Sphinx doc
        skip_exceptions = 'skip_exceptions' in self.options

        # Make temp_evaluated.ipynb include the notebook name
        nb_name = os.path.split(nb_abs_path)[1].replace('.ipynb','')
        dest_path_eval = dest_path_eval.replace('temp_evaluated.ipynb',
                               '{nb_name}_temp_evaluated.ipynb'.format(nb_name=nb_name))

        # Parse slice
        evaluated_text = evaluate_notebook(nb_abs_path, dest_path_eval,
                                           skip_exceptions=skip_exceptions,
                                           substring=self.options.get('substring'),
                                           end=self.options.get('end'),
                                           skip_execute=self.options.get('skip_execute'),
                                           skip_output=self.options.get('skip_output'),
                                           offset=self.options.get('offset', 0),
                                           timeout=setup.config.nbbuild_cell_timeout,
                                           ipython_startup=setup.config.nbbuild_ipython_startup)

        # Insert evaluated notebook HTML into Sphinx

        self.state_machine.insert_input([link_rst], rst_file)

        # create notebook node
        attributes = {'format': 'html', 'source': 'nb_path'}
        nb_node = notebook_node('', evaluated_text, **attributes)
        (nb_node.source, nb_node.line) = \
            self.state_machine.get_source_and_line(self.lineno)

        # add dependency
        self.state.document.settings.record_dependencies.add(nb_abs_path)

        # clean up png files left behind by notebooks.
        png_files = glob.glob("*.png")
        for file in png_files:
            os.remove(file)

        return [nb_node]


class notebook_node(nodes.raw):
    pass


def nb_to_python(nb_path):
    """convert notebook to python script"""
    exporter = python.PythonExporter()
    output, resources = exporter.from_filename(nb_path)
    return output


def nb_to_html(nb_path, preprocessors=[]):
    """convert notebook to html"""
    exporter = html.HTMLExporter(template_file='basic',
                                 preprocessors=preprocessors)
    output, resources = exporter.from_filename(nb_path)
    return output


# TODO: (does it matter) have lost NotebookRunner.MIME_MAP['application/vnd.bokehjs_load.v0+json'] = 'html'
# TODO: (does it matter) have lost NotebookRunner.MIME_MAP['application/vnd.bokehjs_exec.v0+json'] = 'html'
def evaluate_notebook(nb_path, dest_path=None, skip_exceptions=False,substring=None, end=None, skip_execute=None,skip_output=None, offset=0, timeout=300, ipython_startup=None):

    notebook = nbformat.read(nb_path, as_version=4)
    kwargs = dict(timeout=timeout,
                  kernel_name='python%s'%sys.version_info[0],
                  allow_errors=skip_exceptions)

    cwd = os.getcwd()
    filedir, filename = os.path.split(nb_path)
    os.chdir(filedir)
    #profile_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'profile_docs')
    #print("Ignoring %s...hope that's ok"%profile_dir)
    not_nb_runner = ExecutePreprocessor1000(**kwargs)
    if ipython_startup is not None:
        not_nb_runner._ipython_startup = ipython_startup

    if not os.path.isfile(dest_path):
        print('INFO: Running temp notebook {dest_path!s}'.format(
            dest_path=os.path.abspath(dest_path)))
        try:
            if not skip_execute:
                not_nb_runner.preprocess(notebook,{})
        except CellExecutionError as e:
            print('')
            print(e)
            # Return the traceback, filtering out ANSI color codes.
            # http://stackoverflow.com/questions/13506033/filtering-out-ansi-escape-sequences
            return 'Notebook conversion failed with the following traceback: \n%s' % \
                re.sub(r'\\033[\[\]]([0-9]{1,2}([;@][0-9]{0,2})*)*[mKP]?', '', str(e))
        os.chdir(cwd)

        if skip_execute:
            write(notebook, open(dest_path, 'w'), 'json')
        else:
            ne = nbconvert.NotebookExporter()
            newnb, _ = ne.from_notebook_node(notebook)
            with open(dest_path,'w') as f:
                f.write(newnb)
            
    else:
        print('INFO: Skipping existing temp notebook {dest_path!s}'.format(
            dest_path=os.path.abspath(dest_path)))

    preprocessors = [] if substring is None and not offset else [NotebookSlice(substring, end, offset)]
    preprocessors = (preprocessors + [SkipOutput(skip_output)]) if skip_output else preprocessors
    ret = nb_to_html(dest_path, preprocessors=preprocessors)
    return ret


def formatted_link(path):
    return "`%s <%s>`__" % (os.path.basename(path), path)


def visit_notebook_node(self, node):
    self.visit_raw(node)


def depart_notebook_node(self, node):
    self.depart_raw(node)


def setup(app):
    setup.app = app
    setup.config = app.config
    setup.confdir = app.confdir

    app.add_config_value('nbbuild_cell_timeout',300,'html')
    app.add_config_value('nbbuild_ipython_startup',"from nbsite.ipystartup import *",'html')
    
    app.add_node(notebook_node,
                 html=(visit_notebook_node, depart_notebook_node))

    app.add_directive('notebook', NotebookDirective)


if __name__ == '__main__':
    raise NoLongerUsingAsScript
    import argparse, sys
    path, filename = os.path.split(__file__)
    sys.path.append(os.path.abspath(path))
    sys.path.append(os.path.abspath(os.path.join("..", "..")))
    parser = argparse.ArgumentParser()
    parser.add_argument('nbpaths', nargs='*')
    parser.add_argument('-d', '--dest', nargs=1)
    parser.add_argument('-s', '--skip', action='store_true')
    args = parser.parse_args()
    dest_path = os.paths.abspath(args.dest) if args.dest else None
    skip = args.skip
    for nbpath in args.nbpaths:
        nbpath = os.path.abspath(nbpath)
        with open(nbpath[:-6] + '.html', 'w') as f:
            nb_html = evaluate_notebook(nbpath, dest_path=dest_path, skip_exceptions=skip)
            f.write(nb_html)
