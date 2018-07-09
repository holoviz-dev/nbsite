import os
import glob

from .util import copy_files

def init(path):
    tmplate = os.path.join(os.path.dirname(__file__),'tmplate')
    copy_files(tmplate,path)


git_hosts = {
    # no trailing slash
    'GitHub': 'https://raw.githubusercontent.com'
}

# TODO: really needs cleaning up! Currently just prototyping new behavior.
def generate_rst(
        project,
        examples_path="./examples",
        doc_path="./doc",
#        title_formatter=None,
        git_host='GitHub',
        git_org=None,        
        git_repo=None,
        git_branch='master',
        # legacy support
        offset=0,        
        overwrite=False):
    """Auto-generates the rst files corresponding to the Notebooks in
    examples_path

    Takes title from filename, replacing underscores with spaces:
    The_Title.ipynb -> The Title
    01_The_Title.ipynb -> 01 The Title
    01_Hyphen-Conscious_Title.ipynb -> 01 Hyphen-Conscious Title

    and index.ipynb gets title from directory

    Legacy options:
      * offset: allows to skip leading n cells
      * overwrite: will replace existing rst files
    """
    if git_repo is None:
        git_repo = project
    print("Making rst for notebooks in %s and putting them %s..."%(examples_path,doc_path))
    for filename in glob.iglob(os.path.join(examples_path,"**","*.ipynb"), recursive=True):
        fromhere = filename.split(examples_path)[1].lstrip('/')
        # TODO: decide what to do about gallery later
        if fromhere.startswith('gallery'):
            continue    
        fullpath = os.path.abspath(os.path.join(doc_path,fromhere))
        dirname = os.path.dirname(fullpath)
        os.makedirs(dirname, exist_ok=True)
        title = os.path.basename(fullpath)[:-6]
        fullpathrst = os.path.join(dirname, title) + '.rst'
        not_doing_index = True
        if title == 'index':
            not_doing_index = False
            # if path is the doc root, use project for title, otherwise use dir
            if dirname==doc_path:
                title = project
            else:            
                title = os.path.split(os.path.dirname(fullpath))[1]
            # because pyviz has been capitalizing file names but not directory names...
            title = title.title()
        # title is filename with spaces for underscores
        title = title.replace("_", ' ')
        # and no digits- prefix
        #title = re.match('(\d*-)?(?P<title>.*)',title).group('title')
        #fullpathrst = fullpathrst.replace(' ','_')
        if os.path.exists(fullpathrst):
            if not overwrite:
                print("...skipping %s"%fullpathrst)
                continue

        print("...writing %s"%fullpathrst)
        with open(fullpathrst, 'w') as rst_file:
            rst_file.write('*'*len(title)+'\n')        
            rst_file.write(title+'\n')
            rst_file.write('*'*len(title)+'\n\n')
            rst_file.write(".. notebook:: %s %s" % (project,os.path.relpath(examples_path,start=dirname)+'/'+fromhere+"\n"))
            rst_file.write("    :offset: %s\n" % offset)
            if all([git_host,git_org,git_repo,git_branch,not_doing_index]):
                # TODO: this is a hack! paths need to be cleaned up. assume examples/ at same level as module
                examples = os.path.relpath(examples_path,os.path.join(os.path.dirname(__import__(project).__file__),".."))
                rst_file.write('\n\n-------\n\n')
                rst_file.write('`Right click to download this notebook from ' + git_host + '.'
                               ' <%s/%s/%s/%s/%s/%s>`_\n' % (git_hosts[git_host],git_org,git_repo,git_branch,examples,fromhere))
            if not not_doing_index:
                rst_file.write("%s\n"%_toctree(os.path.dirname(filename),os.path.dirname(fullpath),os.path.relpath(examples_path,start=os.getcwd())))

def _toctree(nbpath,docpath,examples):
    dirs = sorted(set([os.path.dirname(os.path.relpath(x,start=examples)) for x in glob.glob(os.path.join(nbpath,"**","index.ipynb"))]))
    nbs = set([os.path.splitext(os.path.basename(x))[0] for x in glob.iglob(os.path.join(nbpath,'*.ipynb'), recursive=False)])
    rst = set([os.path.splitext(os.path.basename(x))[0] for x in glob.iglob(os.path.join(docpath,'*.rst'), recursive=False)])
    if 'index' in rst or 'index' in nbs: 
        try:
            rst.remove('index')
        except:
            pass
        try:
            nbs.remove('index')
        except:
            pass
        if 'Introduction' not in nbs:
            rst.add('Introduction <self>')

    toctree = """
.. toctree::
    :titlesonly:
    :maxdepth: 2
"""
    for entry in sorted(nbs.union(rst)):
        toctree += """
    %s"""%entry

    for entry in dirs:
        toctree += """
    %s <%s/index>"""%(entry.replace("_"," ").title(),entry)
        
    return toctree
