import os

from .util import copy_files

def init(path):
    tmplate = os.path.join(os.path.dirname(__file__),'tmplate')
    copy_files(tmplate,path)
