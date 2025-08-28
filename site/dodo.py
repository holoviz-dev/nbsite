import shutil

from pathlib import Path
from pydoc import importfile

DOIT_CONFIG = {
    "verbosity": 2,
    "backend": "sqlite3",
}


def clean_rst_gallery():
    # Basically remove all the rst and ipynb files from the galleries
    # in the doc folder.
    conf_module = importfile('doc/conf.py')
    if hasattr(conf_module, 'nbsite_gallery_conf'):
        galleries = conf_module.nbsite_gallery_conf['galleries']
        for gallery in galleries:
            gallery_dir = Path('doc')/ gallery
            (gallery_dir / 'index.rst').unlink(missing_ok=True)
            for section in gallery_dir.iterdir():
                for f in section.glob('*.rst'):
                    f.unlink(missing_ok=True)


def task_generate_rst():
    return {
        'actions': [
            'nbsite generate-rst --project-name showcase --doc doc --examples examples'
        ],
        'clean': [
            'git clean -fxd "doc/**/*.rst"'
        ]
    }


def task_build_site():

    def clean_artifacts():

        # Basically remove all the rst and ipynb files from the galleries
        # in the doc folder.
        conf_module = importfile('doc/conf.py')
        if hasattr(conf_module, 'nbsite_gallery_conf'):
            galleries = conf_module.nbsite_gallery_conf['galleries']
            for gallery in galleries:
                gallery_dir = Path('doc')/ gallery
                (gallery_dir / 'index.rst').unlink(missing_ok=True)
                for section in gallery_dir.iterdir():
                    for f in section.glob('*.rst'):
                        f.unlink(missing_ok=True)
                    for f in section.glob('*.ipynb'):
                        f.unlink(missing_ok=True)
                # Thumbnails are pulled from S3
                if gallery == 'playground/example_gallery':
                    shutil.rmtree(gallery_dir)
                # no_image thumbnails for section1 of this gallery
                if gallery == 'playground/example_gallery2':
                    shutil.rmtree(gallery_dir / 'section1')

        if hasattr(conf_module, 'nbsite_gallery_inlined_conf'):
            gallery = conf_module.nbsite_gallery_inlined_conf['path']
            gallery_dir = Path('doc') / gallery
            (gallery_dir / 'index.rst').unlink(missing_ok=True)
            for section in gallery_dir.iterdir():
                for f in section.glob('*.rst'):
                    f.unlink(missing_ok=True)
                for f in section.glob('*.ipynb'):
                    f.unlink(missing_ok=True)

        # Remove the rst and ipynb files from the doc notebook
        nb_dir = Path('doc') / 'playground' / 'notebook_directive'
        for f in nb_dir.glob('*.rst'):
            if f == nb_dir / 'example2.rst':
                continue
            f.unlink(missing_ok=True)
        for f in nb_dir.glob('*.ipynb'):
            f.unlink(missing_ok=True)

    return {
        'actions': [
            'nbsite build --what html --doc doc --examples examples --output builtdocs',
        ],
        'clean': [
            'rm -rf builtdocs/',
            'rm -rf jupyter_execute/',
            clean_artifacts,
        ]
    }


def task_all_build():
    return {
        'actions': None,
        'task_dep': [
            'generate_rst',
            'build_site'
        ],
    }
