#!/usr/bin/env python

"""_Title.ipynb -> The Title



"""

import os
import shutil


def IGetFiles(d):
    for thing in os.scandir(d):
        if thing.is_dir():
            yield from IGetFiles(thing.path)
        else:
            yield thing.path

# I think it's ok to assume these exist for a sphinx site...

def clean_dist_html(output, dry_run):
    htmldir = os.path.abspath(output)

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
        except Exception:
            pass

    for path in IGetFiles(htmldir):
        if os.path.splitext(path)[1].lower() == '.ipynb':
            name = path.split(output)[-1]
            if dry_run:
                print("would remove", name)
            else:
                print("removing", name)
                os.remove(path)
