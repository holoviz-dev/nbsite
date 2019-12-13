#!/usr/bin/env python

"""_Title.ipynb -> The Title



"""

import os
import shutil
import sys

# if only someone had made a way to handle parameters
output = sys.argv[1]
htmldir = os.path.abspath(output)
dry_run =  not (len(sys.argv)>2 and sys.argv[2] == 'take_a_chance')

def IGetFiles(d):
    for thing in os.scandir(d):
        if thing.is_dir():
            yield from IGetFiles(thing.path)
        else:
            yield thing.path

# I think it's ok to assume these exist for a sphinx site...
if dry_run:
    print("This is just a dry-run of removing files from:", htmldir)
else:
    print("Removing files from:", htmldir)

# (.doctrees in build folder by default only for sphinx<1.8)
for folder in (".doctrees", "_sources"):
    d = os.path.join(htmldir,folder)
    try:
        if dry_run:
            print("would remove", folder)
        else:
            print("removing", folder)
            shutil.rmtree(d)
    except:
        pass

for file_ in ():
    f = os.path.join(htmldir,file_)
    try:
        if dry_run:
            print("would remove", file_)
        else:
            print("removing", file_)
            os.remove(f)
    except:
        pass

for path in IGetFiles(htmldir):
    if os.path.splitext(path)[1].lower() == '.ipynb':
        name = path.split(output)[-1]
        if dry_run:
            print("would remove", name)
        else:
            print("removing", name)
            os.remove(path)
