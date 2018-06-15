# version comes from git if available, otherwise from .version file
try:
    from _pyctbuild import Version
    __version__ = str(Version(fpath=__file__,archive_commit="$Format:%h$",reponame="nbsite"))
except:
    import os, json
    __version__ = json.load(open(os.path.join(os.path.dirname(__file__),'.version'),'r'))['version_string']
    del os, json


# make pyct's example/data commands available if possible
from functools import partial
try:
    from pyct.cmd import copy_examples as _copy, fetch_data as _fetch, examples as _examples
    copy_examples = partial(_copy, 'nbsite')
    fetch_data = partial(_fetch, 'nbsite')
    examples = partial(_examples, 'nbsite')
except ImportError:
    def _missing_cmd(*args,**kw): return("install pyct to enable this command (e.g. `conda install -c pyviz pyct`)")
    _copy = _fetch = _examples = _missing_cmd
    def _err(): raise ValueError(_missing_cmd())
    fetch_data = copy_examples = examples = _err
del partial, _examples, _copy, _fetch
