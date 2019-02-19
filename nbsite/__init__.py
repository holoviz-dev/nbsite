import param

NAME = "nbsite"

# version comes from git if available, otherwise from .version file
__version__ = str(param.version.Version(fpath=__file__, archive_commit="$Format:%h$",
                                        reponame=NAME))

# make pyct's example/data commands available from python if possible
try:
    import pyct.cmd
    from functools import partial
    copy_examples = partial(pyct.cmd.copy_examples, NAME),
    fetch_data = partial(pyct.cmd.fetch_data, NAME),
    examples = partial(pyct.cmd.examples, NAME),
    clean_data = partial(pyct.cmd.clean_data, NAME)

except ImportError:
    def _err():
        raise ImportError(
            "install pyct to enable this command "
            "(e.g. `conda install -c pyviz pyct`  or `pip install pyct[cmd]`)")
    fetch_data = copy_examples = clean_data = examples = _err
