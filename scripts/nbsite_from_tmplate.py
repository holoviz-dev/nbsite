#!/usr/bin/env python

import os
import sys
import shutil

import nbsite

doc_path = sys.argv[1]

def IGetFiles(d):
    for thing in os.scandir(d):
        if thing.is_dir():
            yield from IGetFiles(thing.path)
        else:
            yield thing.path

tmplate = os.path.join(os.path.dirname(nbsite.__file__),'tmplate')

for path in IGetFiles(tmplate):
    d = os.path.join(doc_path,os.path.dirname(path.split(tmplate)[1][1:]))
    if not os.path.exists(d):
        print('mkdir %s'%d)
        os.makedirs(d)
    f = os.path.join(doc_path,path.split(tmplate)[1][1:])
    if not os.path.exists(f):
        print("cp %s %s"%(path,f))
        shutil.copy(path,f)
