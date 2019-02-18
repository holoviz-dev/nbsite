import os
import glob
import shutil

def copy_files(src, dest, pattern='**'):
    """Copy every file matching pattern from src to dest
    """
    for path in glob.glob(os.path.join(src, pattern), recursive=True):
        if not os.path.isfile(path):
            continue
        d = os.path.join(dest, os.path.dirname(path.split(src)[1][1:]))
        if not os.path.exists(d):
            print('mkdir %s'%d)
            os.makedirs(d)
        f = os.path.join(dest, path.split(src)[1][1:])
        if not os.path.exists(f):
            print("cp %s %s"%(path, f))
            shutil.copy(path, f)
