import glob
import os
import re
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


def base_version(version):
    """Extract the final release and if available pre-release (alpha, beta,
    release candidate) segments of a PEP440 version, defined with three
    components (major.minor.micro).

    Useful to avoid nbsite/sphinx to display the documentation HTML title
    with a not so informative and rather ugly long version (e.g.
    ``0.13.0a19.post4+g0695e214``). Use it in ``conf.py``::

        version = release = base_version(package.__version__)

    Return the version passed as input if no match is found with the pattern.
    """
    # look at the start for e.g. 0.13.0, 0.13.0rc1, 0.13.0a19, 0.13.0b10
    pattern = r"([\d]+\.[\d]+\.[\d]+(?:a|rc|b)?[\d]*)"
    match = re.match(pattern, version)
    if match:
        return match.group()
    else:
        return version
