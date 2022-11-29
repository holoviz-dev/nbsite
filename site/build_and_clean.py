import shutil
import subprocess
import time

from pathlib import Path
from pydoc import importfile

start = time.perf_counter()

examples_dir = 'examples'
doc_dir = 'doc'
out_dir = 'builtdocs'
notebook_dir = 'playground/notebook_directive'

cur_dir = Path(__file__).parent

def remove_mess():

    # Cache used by MyST-NB / Jupyter Cache
    jupyter_cache_dir = 'jupyter_execute'
    shutil.rmtree(cur_dir / jupyter_cache_dir, ignore_errors=True)

    # Basically remove all the rst and ipynb files from the galleries
    # in the doc folder.
    conf_module = importfile('doc/conf.py')
    galleries = conf_module.nbsite_gallery_conf['galleries']
    for gallery in galleries:
        gallery_dir = cur_dir / doc_dir/ gallery
        (gallery_dir / 'index.rst').unlink(missing_ok=True)
        for section in gallery_dir.iterdir():
            for f in section.glob('*.rst'):
                f.unlink(missing_ok=True)
            for f in section.glob('*.ipynb'):
                f.unlink(missing_ok=True)

    # Remove the rst and ipynb files from the doc notebook
    nb_dir = cur_dir / doc_dir / notebook_dir
    for f in nb_dir.glob('*.rst'):
            f.unlink(missing_ok=True)
    for f in nb_dir.glob('*.ipynb'):
        f.unlink(missing_ok=True)


print('> Remove output dir...\n')
shutil.rmtree(cur_dir / out_dir, ignore_errors=True)

print('\n> Remove previous artefacts...\n')
remove_mess()

cmd_gen_rst = f'nbsite generate-rst --project-name showcase --doc {doc_dir} --examples {examples_dir}'
cmd_build = f'nbsite build --what html --doc {doc_dir} --examples {examples_dir} --output {out_dir}'

print('\n> Generate RST...\n')
subprocess.run(cmd_gen_rst.split(' '))
print('\n> Build...\n')
subprocess.run(cmd_build.split(' '))

print('\n> Clean up...')
remove_mess()

print(f'Done in {time.perf_counter() - start:.1f} s')
