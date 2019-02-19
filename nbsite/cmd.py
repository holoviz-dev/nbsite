import os
import glob
import re
import sys
import subprocess
from os.path import dirname
from collections import ChainMap

from .util import copy_files

def init(project_root='',doc='doc'):
    """Start an nbsite project: create a doc folder containing nbsite
template files

    """
    paths = _prepare_paths(project_root,doc=doc)
    copy_files(os.path.join(dirname(__file__),'tmplate2'),
               paths['doc'])

hosts = {
    # no trailing slash
    'GitHub': 'https://raw.githubusercontent.com'
}

# TODO: clean up these fns + related arg parsing: parameterize, and
# maybe add task dependencies

def fix_links(output, inspect_links):
    args = ["nbsite_fix_links.py", output]
    if inspect_links:
        args.append( "--inspect-links")
    subprocess.check_call(args)


def build(what='html',
          output='builtdocs',
          project_root='',
          doc='doc',
          examples='examples',
          examples_assets='assets',
          clean_dry_run=False,
          inspect_links=False):
    """
    Build the site from the rst files and the notebooks

    Usually this is run after `nbsite scaffold`
    """
    # TODO: also have an overwrite flag
    paths = _prepare_paths(project_root, examples=examples, doc=doc, examples_assets=examples_assets)
    subprocess.check_call(["sphinx-build","-b",what,paths['doc'],output])
    print('Copying json blobs (used for holomaps) from {} to {}'.format(paths['doc'], output))
    copy_files(paths['doc'], output, '**/*.json')
    if 'examples_assets' in paths:
        build_assets = os.path.join(output, examples_assets)
        print("Copying examples assets from %s to %s"%(paths['examples_assets'],build_assets))
        copy_files(paths['examples_assets'], build_assets)
    fix_links(output, inspect_links)
    # create a .nojekyll file in output for github compatibility
    subprocess.check_call(["touch", os.path.join(output, '.nojekyll')])
    if not clean_dry_run:
        print("Call `nbsite build` with `--clean-dry-run` to not actually delete files.")
    clean(output, clean_dry_run)

def clean(output, dry_run=False):
    if dry_run:
        subprocess.check_call(["nbsite_cleandisthtml.py",output])
    else:
        subprocess.check_call(["nbsite_cleandisthtml.py",output,'take_a_chance'])

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
        branch='master',
        offset=0,
        overwrite=False,
        nblink='bottom',
        skip=''):
    """Auto-generates notebook-including rsts from notebooks in examples.

    titles
    ======

    rst file takes title from notebook filename in general, replacing
    underscores with spaces and converting to title case. E.g.

      * The_Title.ipynb -> The Title
      * 01_The_Title.ipynb -> 01 The Title
      * 01_Hyphen-Conscious_Title.ipynb -> 01 Hyphen-Conscious Title
      * 1_some_title.ipynb -> 1 Some Title

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
        default_pyviz_ordering ("Introduction","Getting Started","User
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
    for filename in glob.iglob(os.path.join(paths['examples'],"**","*.ipynb"), recursive=True):
        fromhere = filename.split(paths['examples'])[1].lstrip('/') # TODO: not win
        # TODO: decide what to do about gallery later
        if fromhere.startswith('gallery'):
            continue
        if _should_skip(skip, fromhere):
            print('...deliberately skipping', fromhere)
            continue
        rst = os.path.splitext(os.path.join(paths['doc'],fromhere))[0] + ".rst"
        pretitle = _file2pretitle(rst)
        os.makedirs(dirname(rst), exist_ok=True)

        if pretitle != 'index':
            title = _to_title(pretitle)
        else:
            if _is_root(dirname(rst),paths['doc']):
                title = project_name
            else:
                title = _filepath2pretitle(rst,paths['doc'])
            title = _to_title(title,apply_title_case=True)

        if os.path.exists(rst):
            if not overwrite:
                print("...skipping %s"%rst)
                continue

        print("...writing %s"%rst)
        with open(rst, 'w') as rst_file:
            import nbsite
            rst_file.write('..\n   Originally generated by nbsite (%s):\n     %s\n   Will not subsequently be overwritten by nbsite, so can be edited.\n\n'%(nbsite.__version__,' '.join(sys.argv)))
            rst_file.write('*'*len(title)+'\n')
            rst_file.write(title+'\n')
            rst_file.write('*'*len(title)+'\n\n')

            if nblink in ['top', 'both']:
                add_nblink(rst_file, host,org,repo, branch, examples, fromhere)
                rst_file.write('\n\n-------\n\n')

            rst_file.write(".. notebook:: %s %s" % (project_name,os.path.relpath(paths['examples'],start=dirname(rst))+'/'+fromhere+"\n"))
            rst_file.write("    :offset: %s\n" % offset)

            if pretitle=='index':
                rst_file.write("%s\n"%_toctree(dirname(filename),paths['examples']))
            if nblink in ['bottom', 'both']:
                rst_file.write('\n\n-------\n\n')
                add_nblink(rst_file, host,org,repo, branch, examples, fromhere)


def add_nblink(rst_file, host,org,repo,branch,examples, fromhere):
    if all([host,org,repo,branch]):
        info = (hosts[host],org,repo,branch,examples,fromhere)
        rst_file.write('`Right click to download this notebook from ' + host + '.'
                       ' <%s/%s/%s/%s/%s/%s>`_\n' % info)

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

default_pyviz_ordering = ["Introduction","Getting Started","User Guide","Topics","FAQ","API"]
def _title_key(title):
    leading_digits = re.match(r"\d+",title)
    return (0,int(leading_digits.group(0)),title) if leading_digits else (1,default_pyviz_ordering.index(title) if title in default_pyviz_ordering else float("inf"),title)

def _toctree(nbpath,examples_path):
    #
    # rst:
    # ipynb:
    # dir: dir containing index.ipynb

    tocmap = {}
    for ftype in ('ipynb','rst'):
        tocmap[ftype] = {_to_title(k):"<%s>"%k for k in [_file2pretitle(f) for f in glob.iglob(os.path.join(nbpath,'*.'+ftype), recursive=False)]}

    tocmap['dir'] = {_to_title(k,apply_title_case=True):"<%s/index>"%k for k in [_filepath2pretitle(x,examples_path) for x in glob.glob(os.path.join(nbpath,"**","index.ipynb"))]}

    # index shouldn't explicitly appear in toctree...
    if 'index' in tocmap['rst'] or 'index' in tocmap['ipynb']:
        tocmap['rst'].pop('index',None)
        tocmap['ipynb'].pop('index',None)
    # ...except at root (where it gets called Introduction)
    if _is_root(nbpath,examples_path):
        assert not any(['Introduction' in tocmap[x] for x in tocmap]), "index will be shown as Introduction, but Introduction already exists in %s"%examples_path
        tocmap['rst']['Introduction'] ='<self>'

    titles = ChainMap(*[tocmap[x] for x in tocmap])

    toctree = """
.. toctree::
    :titlesonly:
    :maxdepth: 2
"""
    for title in sorted(titles,key=_title_key):
        toctree += """
    %s %s"""%(title,titles[title])

    return toctree
