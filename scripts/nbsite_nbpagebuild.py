#!/usr/bin/env python

"""
Auto-generates the rst files corresponding to the Notebooks in examples/

nbsite_nbpagebuild.py project /path/to/examples /path/to/doc
"""

import os
import glob
import re
import sys

project = sys.argv[1]
examples_path = os.path.abspath(sys.argv[2])
doc_path = os.path.abspath(sys.argv[3])

print("Making rst for notebooks in %s and putting them %s"%(examples_path,doc_path))

for filename in glob.iglob(os.path.join(examples_path,"**","*.ipynb"), recursive=True):
    fromhere = filename.split(examples_path)[1].lstrip('/')
    # TODO: decide what to do about gallery later
    if fromhere.startswith('gallery'):
        continue    
    fullpath = os.path.abspath(os.path.join(doc_path,fromhere))
    dirname = os.path.dirname(fullpath)
    os.makedirs(dirname, exist_ok=True)
    # title is filename with spaces for underscores, and no digits- prefix
    title = os.path.basename(fullpath)[:-6].replace('_', ' ')
    title = re.match('(\d*-)?(?P<title>.*)',title).group('title')
    fullpathrst = os.path.join(dirname, title) + '.rst'
    fullpathrst = fullpathrst.replace(' ','_')
    # TODO: hardcoded
    todo = "../../examples/"
    with open(fullpathrst, 'w') as rst_file:
        rst_file.write(title+'\n')
        rst_file.write('_'*len(title)+'\n\n')
        rst_file.write(".. notebook:: %s %s\n" % (project, todo+fromhere))
        rst_file.write("    :offset: 1\n")
        rst_file.write('\n\n-------\n\n')
        rst_file.write('`Right click to download this notebook from GitHub.'
                       ' <https://raw.githubusercontent.com/ioam/%s/master/examples/%s>`_\n' % (project,fromhere))



