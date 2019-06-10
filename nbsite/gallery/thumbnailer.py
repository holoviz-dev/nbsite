from __future__ import unicode_literals
import os, sys, subprocess
from nbconvert.preprocessors import Preprocessor

from holoviews.core import Dimensioned, Store
from holoviews.ipython.preprocessors import OptsMagicProcessor, OutputMagicProcessor
from holoviews.ipython.preprocessors import StripMagicsProcessor, wrap_cell_expression
from holoviews.util.command import export_to_python

import matplotlib.pyplot as plt
plt.switch_backend('agg')


def strip_specific_magics(source, magic):
    """
    Given the source of a cell, filter out specific cell and line magics.
    """
    filtered=[]
    for line in source.splitlines():
        if line.startswith(f'%{magic}'):
            filtered.append(line.lstrip(f'%{magic}').strip(' '))
        if line.startswith(f'%%{magic}'):
            filtered.append(line.lstrip(f'%%{magic}').strip(' '))
        else:
            filtered.append(line)
    return '\n'.join(filtered)


class StripTimeMagicsProcessor(Preprocessor):
    """
    Preprocessor to convert notebooks to Python source strips out just time
    magics while keeping the rest of the cell.
    """

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            cell['source'] = strip_specific_magics(cell['source'], 'time')
        return cell, resources

    def __call__(self, nb, resources): return self.preprocess(nb,resources)


def strip_trailing_semicolons(source, function):
    """
    Give the source of a cell, filter out lines that contain a specified
    function call and end in a semicolon.
    """
    filtered=[]
    for line in source.splitlines():
        if line.endswith(f'{function}();'):
            filtered.append(line[:-1])
        else:
            filtered.append(line)
    return '\n'.join(filtered)


class StripServableSemicolonsProcessor(Preprocessor):
    """
    Preprocessor to convert notebooks to Python source strips out just semicolons
    that come after the servable function call.
    """

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            cell['source'] = strip_trailing_semicolons(cell['source'], 'servable')
        return cell, resources

    def __call__(self, nb, resources): return self.preprocess(nb,resources)


def thumbnail(obj, basename):
    import os
    if isinstance(obj, Dimensioned) and not os.path.isfile(basename+'.png'):
        Store.renderers[Store.current_backend].save(obj, basename, fmt='png')
    elif 'panel' in sys.modules:
        from panel.viewable import Viewable
        if isinstance(obj, Viewable) and not os.path.isfile(basename+'.png'):
            obj.save(basename+'.png')
    return obj


class ThumbnailProcessor(Preprocessor):

    def __init__(self, basename, **kwargs):
        self.basename = basename
        super(ThumbnailProcessor, self).__init__(**kwargs)

    def preprocess_cell(self, cell, resources, index):
        if cell['cell_type'] == 'code':
            template = 'from nbsite.gallery.thumbnailer import thumbnail;thumbnail({{expr}}, {basename!r})'
            cell['source'] = wrap_cell_expression(cell['source'],
                                                  template.format(
                                                      basename=self.basename))
        return cell, resources

    def __call__(self, nb, resources): return self.preprocess(nb,resources)


def execute(code, cwd, env):
    proc = subprocess.Popen(['python'],
                            stdin=subprocess.PIPE, cwd=cwd, env=env)
    proc.communicate(code)
    return proc.returncode

def notebook_thumbnail(filename, subpath):
    basename = os.path.splitext(os.path.basename(filename))[0]
    dir_path = os.path.join(subpath, 'thumbnails')
    absdirpath= os.path.abspath(os.path.join('.', dir_path))
    if not os.path.exists(absdirpath):
        os.makedirs(absdirpath)

    preprocessors = [OptsMagicProcessor(),
                     OutputMagicProcessor(),
                     StripTimeMagicsProcessor(),
                     StripServableSemicolonsProcessor(),
                     StripMagicsProcessor(),
                     ThumbnailProcessor(os.path.abspath(os.path.join(dir_path, basename)))]
    return export_to_python(filename, preprocessors)

if __name__ == '__main__':
    files = []
    abspath = os.path.abspath(sys.argv[1])
    split_path = abspath.split(os.path.sep)
    if os.path.isdir(abspath):
        if 'examples' not in split_path:
            print('Can only thumbnail notebooks in examples/')
            sys.exit()
        subpath = os.path.sep.join(split_path[split_path.index('examples')+1:])
        files = [os.path.join(abspath, f) for f in os.listdir(abspath)
                 if f.endswith('.ipynb')]
    elif os.path.isfile(abspath):
        subpath = os.path.sep.join(split_path[split_path.index('examples')+1:-1])
        files=[abspath]
    else:
        print('Path {path} does not exist'.format(path=abspath))

    for f in files:
        print('Generating thumbnail for file {filename}'.format(filename=f))
        code = notebook_thumbnail(f, subpath)
        try:
            retcode = execute(code.encode('utf8'), cwd=os.path.split(f)[0])
        except Exception as e:
            print('Failed to generate thumbnail for {filename}'.format(filename=f))
            print(str(e))
