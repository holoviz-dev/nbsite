#!/usr/bin/env python

"""_Title.ipynb -> The Title



"""

import os
import shutil
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

# I think it's ok to assume these exist for a sphinx site...

# (.doctrees in build folder by default only for sphinx<1.8)
for folder in (".doctrees", "_sources"):
    d = os.path.join(htmldir,folder)
    try:
        print("removing %s"%d)
        shutil.rmtree(d)
    except:
        pass

for file_ in ("objects.inv",):
    f = os.path.join(htmldir,file_)
    try:
        print("removing %s"%f)
        os.remove(f)
    except:
        pass

for path in IGetFiles(htmldir):
    if os.path.splitext(path)[1].lower() == '.ipynb':
        print("removing %s"%path)
        os.remove(path)
