import os
import shutil

####
# TODO: should replace with some existing copy fn!

def _IGetFiles(d):
    for thing in os.scandir(d):
        if thing.is_dir():
            yield from _IGetFiles(thing.path)
        else:
            yield thing.path

def copy_files(from_,to_):
    for path in _IGetFiles(from_):
        d = os.path.join(to_,os.path.dirname(path.split(from_)[1][1:]))
        if not os.path.exists(d):
            print('mkdir %s'%d)
            os.makedirs(d)
        f = os.path.join(to_,path.split(from_)[1][1:])
        if not os.path.exists(f):
            print("cp %s %s"%(path,f))
            shutil.copy(path,f)
####


