import glob
import os
import re
import sys

from collections import ChainMap
from os.path import dirname

from sphinx.application import Sphinx

from .scripts import clean_dist_html, fix_links
from .util import copy_files

DEFAULT_SITE_ORDERING = [
    "Introduction",
    "Getting Started",
    "User Guide",
    "Topics",
    "FAQ",
    "API"
]

def init(project_root='', doc='doc', theme=''):
    """
    Start an nbsite project: create a doc folder containing nbsite
    template files

    Use the theme argument to specify a particular theme to use as template
    """
    paths = _prepare_paths(project_root, doc=doc)
    if theme:
        copy_files(os.path.join(dirname(__file__), 'templates', theme),
                   paths['doc'])
    else:
        copy_files(os.path.join(dirname(__file__), 'templates', 'basic'),
                   paths['doc'])

hosts = {
    # no trailing slash
    'GitHub': 'https://raw.githubusercontent.com'
}


def build(what='html',
          output='builtdocs',
          project_root='',
          doc='doc',
          project_name='',
          host='GitHub',
          repo='',
          branch='main',
          org='',
          binder='none',
          disable_parallel=False,
          examples='examples',
          examples_assets='assets',
          clean_dry_run=False,
          inspect_links=False,
          overwrite=False):
    """
    Build the site from the rst files and the notebooks

    Usually this is run after `nbsite scaffold`
    """
    env = {
        'PROJECT_NAME':project_name,
        'PROJECT_ROOT':project_root if project_root!='' else os.getcwd(),
        'HOST':host,
        'REPO':repo,
        'BRANCH':branch,
        'ORG':org,
        'EXAMPLES':examples,
        'DOC':doc,
        'EXAMPLES_ASSETS':examples_assets,
        'BINDER':binder
    }
    none_vals = {k:v for k,v in env.items() if v is None}
    if none_vals:
        raise Exception("Missing value for %s" % list(none_vals.keys()))

    paths = _prepare_paths(project_root, examples=examples, doc=doc, examples_assets=examples_assets)
    if overwrite:
        for path in glob.glob(os.path.join(paths['doc'], '**', '*.ipynb'), recursive=True):
            print('Removing evaluated notebook from {}'.format(path))
            os.remove(path)

    parallel = 0 if disable_parallel else os.cpu_count()
    # Code smell as there should be a way to configure Sphinx/Nbsite without
    # env vars, but that's how it was done at the time Sphinx was called
    # via subprocess.
    _environ = dict(os.environ)
    os.environ.update(env)
    try:
        app = Sphinx(
            srcdir=paths["doc"],
            confdir=paths["doc"],
            outdir=output,
            doctreedir=os.path.join(output, ".doctrees"),
            buildername=what,
            parallel=parallel,
        )
        app.build()
    finally:
        os.environ.clear()
        os.environ.update(_environ)

    print('Copying json blobs (used for holomaps) from {} to {}'.format(paths['doc'], output))
    copy_files(paths['doc'], output, '**/*.json')
    copy_files(paths['doc'], output, 'json_*')
    if 'examples_assets' in paths:
        build_assets = os.path.join(output, examples_assets)
        print("Copying examples assets from %s to %s"%(paths['examples_assets'],build_assets))
        copy_files(paths['examples_assets'], build_assets)
    fix_links(output, inspect_links)

    # create a .nojekyll file in output for github compatibility
    with open(os.path.join(output, '.nojekyll'), 'w') as f:
        f.write('')

    if not clean_dry_run:
        print("Call `nbsite build` with `--clean-dry-run` to not actually delete files.")

    clean_dist_html(output, clean_dry_run)

def _prepare_paths(root,examples='',doc='',examples_assets=''):
    if root=='':
        root = os.getcwd()
    paths = {'project': os.path.abspath(root)}
    if examples!='':
        paths['examples'] = examples if os.path.isabs(examples) else os.path.join(paths['project'],examples)
    if doc!='':
        paths['doc'] = doc if os.path.isabs(doc) else os.path.join(paths['project'],doc)
    if examples_assets!='':
        paths['examples_assets'] = os.path.join(paths['examples'], examples_assets)
    return paths

def _is_root(x,root):
    return os.path.abspath(x) == os.path.abspath(root)

# TODO: needs cleaning up; currently just prototyping new behavior.
# TODO: rename to something like scaffold?
def generate_rst(
        project_name='',        # if not supplied, will default to repo
        project_root='',        # if not supplied, will default to os.getcwd()
        examples="examples",    # relative to project_root
        doc="doc",              # relative to project_root
#        title_formatter=None,
        host='GitHub',
        org='',                 # if not supplied, will default to project_name, or repo
        repo='',                # if not supplied, will default to project_name
        branch='main',
        offset=0,
        overwrite=False,
        nblink='bottom',
        skip='',
        keep_numbers=False,
        binder='none',
        disable_interactivity_warning=False
):
    """Auto-generates notebook-including rsts from notebooks in examples.

    titles
    ======

    rst file takes title from notebook filename in general, replacing
    underscores with spaces and converting to title case. E.g.

      * The_Title.ipynb -> The Title
      * 01_The_Title.ipynb -> The Title
      * 01_Hyphen-Conscious_Title.ipynb -> Hyphen-Conscious Title
      * 1_some_title.ipynb -> Some Title
      * 1_stripped_title.ipynb -> 1 Stripped Title  # with ``keep_numbers`` flag

    But: index.ipynb gets title from its containing directory in
    general, except at the root, where index.ipynb gets the
    project_name as title.


    toctree generation
    ==================

    If there's no index.rst already, the generated index.rst will
    contain a generated toctree, with entries sorted as follows:

      * number-prefixed items grouped before others, sorted first by
        number

      * after dealing with numeric prefixes, items in
        DEFAULT_SITE_ORDERING ("Introduction","Getting Started","User
        Guide","Topics","FAQ","API") grouped next, sorted in that
        order

      * remaining items appear at the end, sorted by text


    overriding titles and toctrees
    ==============================

    Generated rst files won't be overwritten on a subsequent run, so
    can be edited and committed.


    Other options
    =============

      * offset: allows to skip leading n cells
      * overwrite: will overwrite existing rst files [DANGEROUS]
      * keep_numbers: keeps leading numbers in title and path, rather than
        stripping them off.
      * ...

    """
    if repo == '' and project_name == '':
        raise ValueError("Must set at least one of repo or project-name")
    elif repo == '' or project_name == '':
        project_name = repo = project_name or repo

    if org == '':
        org = repo

    paths=_prepare_paths(project_root,examples=examples,doc=doc)

    print("Project='%s': Converting notebooks at '%s' to rst at '%s'..."%(project_name,paths['examples'],paths['doc']))
    for filename in glob.iglob(os.path.abspath(os.path.join(paths['examples'],"**","*.ipynb")), recursive=True):
        relpath = os.path.relpath(filename, paths['examples'])
        # TODO: decide what to do about gallery later
        if relpath.startswith('gallery'):
            continue
        if _should_skip(skip, relpath):
            print('...deliberately skipping', relpath)
            continue
        rst = os.path.splitext(os.path.join(paths['doc'], relpath))[0] + ".rst"
        rst = _path_and_order(rst, keep_numbers)[0]
        pretitle = _file2pretitle(rst)
        os.makedirs(dirname(rst), exist_ok=True)

        if pretitle != 'index':
            title = _to_title(pretitle)
        else:
            if _is_root(dirname(rst),paths['doc']):
                title = project_name
            else:
                title = _filepath2pretitle(rst,paths['doc'])
            title = _to_title(title, apply_title_case=True)

        if os.path.exists(rst):
            if not overwrite:
                print("...skipping %s"%rst)
                continue

        print(f"...writing {rst}")
        with open(rst, 'w') as rst_file:
            import nbsite
            rst_file.write(
                f'..\n   Originally generated by nbsite ({nbsite.__version__}):\n'
                f'   {" ".join(sys.argv)}\n   Will not subsequently be overwritten by '
                'nbsite, so can be edited.\n\n'
            )
            if binder in ['top', 'both']:
                add_binder(rst_file, org, repo, branch, relpath, examples)

            rst_file.write('*'*len(title)+'\n')
            rst_file.write(title+'\n')
            rst_file.write('*'*len(title)+'\n\n')

            if nblink in ['top', 'both']:
                add_nblink(rst_file, host, org, repo, branch, examples, relpath)
                rst_file.write('\n\n-------\n\n')

            rst_file.write(
                ".. notebook:: %s %s" % (project_name, os.path.relpath(paths["examples"], start=dirname(rst)).replace("\\", "/") + "/" + relpath + "\n"),
            )
            rst_file.write("    :offset: %s\n" % offset)
            if disable_interactivity_warning:
                rst_file.write("    :disable_interactivity_warning:\n")

            if pretitle=='index':
                rst_file.write("%s\n"%_toctree(dirname(filename), paths['examples'], keep_numbers))
            if nblink in ['bottom', 'both']:
                rst_file.write('\n\n-------\n\n')
                add_nblink(rst_file, host, org, repo, branch, examples, relpath)
            if binder in ['bottom', 'both']:
                add_binder(rst_file, org, repo, branch, relpath, examples)


def add_nblink(rst_file, host, org, repo, branch, examples, relpath):
    if all([host, org, repo, branch]):
        info = (hosts[host], org, repo, branch, examples,relpath)
        rst_file.write('`Right click to download this notebook from ' + host + '.'
                       ' <%s/%s/%s/%s/%s/%s>`_\n' % info)

def add_binder(rst_file, org, repo, branch, relpath, examples):
    rst_file.write("""
.. note:: Try live in your browser!

  |Binder| to run this notebook in your browser (no setup required).


.. |Binder| image:: https://mybinder.org/badge_logo.svg
   :target: https://mybinder.org/v2/gh/{org}/{repo}/{branch}?filepath={examples}/{relpath}

""".format(org=org,repo=repo,branch=branch,relpath=relpath,examples=examples))

def _should_skip(skip, filename):
    if skip == '':
        return False
    skip_patterns = [p.strip() for p in skip.strip('[]').split(',')]
    return any([re.match(p,filename,re.IGNORECASE) for p in skip_patterns])

def _to_title(name,apply_title_case=False):
    # allow to apply title case for directories, which pyviz has as lower case
    title = name.replace("_"," ")
    if apply_title_case:
        title = title.title()
    return title

def _filepath2pretitle(filepath,root):
    return os.path.relpath(dirname(filepath),start=root)

def _file2pretitle(file_):
    return os.path.splitext(os.path.basename(file_))[0]

def _title_key(title_tup):
    title, order = title_tup[0], title_tup[1]['order']
    if order is not None:
        return (0, order, title)
    elif title in DEFAULT_SITE_ORDERING:
        return (1, DEFAULT_SITE_ORDERING.index(title), title)
    else:
        return (1, float("inf"), title)

def _path_and_order(filepath, keep_numbers):
    num_name = os.path.basename(filepath)
    leading_num = re.match(r"^\d+", num_name)
    if not keep_numbers:
        name = re.split(r"^\d+( |-|_)", num_name)[-1]
        filepath = filepath.replace(num_name, name)
    return filepath, int(leading_num.group(0)) if leading_num else None

def _toctree(nbpath, examples_path, keep_numbers):
    tocmap = {'ipynb': {},'rst': {}}
    for ftype in ('ipynb','rst'):
        for f in glob.iglob(os.path.join(nbpath,'*.'+ftype), recursive=False):
            f, order = _path_and_order(f, keep_numbers)
            k = _file2pretitle(f)
            tocmap[ftype][_to_title(k)] = {'path': "<%s>"%k, 'order': order}

    tocmap['dir'] = {
        _to_title(k, apply_title_case=True): {'path': "<%s/index>"%k, 'order': None} for k in [
            _filepath2pretitle(x, examples_path) for x in glob.glob(os.path.join(nbpath, "**", "index.ipynb"))]}

    # index shouldn't explicitly appear in toctree...
    if 'index' in tocmap['rst'] or 'index' in tocmap['ipynb']:
        tocmap['rst'].pop('index', None)
        tocmap['ipynb'].pop('index', None)
    # ...except at root (where it gets called Introduction)
    if _is_root(nbpath,examples_path):
        if any(['Introduction' in tocmap[x] for x in tocmap]):
            raise ValueError("index will be shown as Introduction, but Introduction "
                             "already exists in %s" % examples_path)

        tocmap['rst']['Introduction'] = {'path': '<self>', 'order': -1}

    titles = ChainMap(*[tocmap[x] for x in tocmap])

    toctree = """
.. toctree::
    :titlesonly:
    :maxdepth: 2
"""
    for title, title_dict in sorted(titles.items(), key=_title_key):
        toctree += """
    %s %s"""%(title, title_dict['path'])

    return toctree
