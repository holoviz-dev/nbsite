#!/usr/bin/env python

"""_Title.ipynb -> The Title



"""

import os
import shutil

import glob
import re
import sys

# if only someone had made a way to handle parameters
htmldir = os.path.abspath(sys.argv[1])

if not (len(sys.argv)>2 and sys.argv[2] == 'take_a_chance'):
    print("This quickly thrown together script will delete things from your computer; you should check it yourself before you run it. Once you've done so, pass 'take_a_chance' as the second argument.")
    sys.exit(1)


def IGetFiles(d):
    for thing in os.scandir(d):
        if thing.is_dir():
            yield from IGetFiles(thing.path)
        else:
            yield thing.path
    
for folder in (".doctrees", "_sources"):
    d = os.path.join(htmldir,folder)
    print("removing %s"%d)
    shutil.rmtree(d)

for file_ in ("objects.inv",):
    f = os.path.join(htmldir,file_)
    print("removing %s"%f)
    os.remove(f)

for path in IGetFiles(htmldir):
    if os.path.splitext(path)[1].lower() == '.ipynb':
        print("removing %s"%path)
        os.remove(path)
