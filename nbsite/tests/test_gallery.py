from types import SimpleNamespace

from nbsite.gallery.gen import generate_item_rst, generate_pyodide_markdown


def _gallery_app():
    gallery_conf = {
        'deployment_url': None,
        'download_as': None,
        'examples_dir': 'examples',
        'galleries': {
            'panes': {
                'titles': {
                    'Vega': 'Altair & Vega',
                },
            },
        },
        'github_org': 'holoviz',
        'github_project': 'panel',
        'github_ref': 'main',
        'host': 'GitHub',
        'iframe_spinner': '',
        'jupyterlite_url': None,
        'nblink': None,
        'skip_execute': [],
    }
    return SimpleNamespace(config=SimpleNamespace(nbsite_gallery_conf=gallery_conf))


def test_generate_pyodide_markdown_uses_gallery_title(tmp_path):
    source = tmp_path / 'src'
    dest = tmp_path / 'dest'
    source.mkdir()
    dest.mkdir()
    filename = source / 'Vega.py'
    filename.write_text('print("vega")\n')

    generate_pyodide_markdown(
        _gallery_app(), 'panes', None, None, str(filename), str(source), str(dest),
        'png', str(filename), False, False,
    )

    assert (dest / 'Vega.md').read_text().startswith('# Altair & Vega\n\n')


def test_generate_item_rst_uses_gallery_title(tmp_path):
    source = tmp_path / 'src'
    dest = tmp_path / 'dest'
    source.mkdir()
    dest.mkdir()
    filename = source / 'Vega.py'
    filename.write_text('print("vega")\n')

    generate_item_rst(
        _gallery_app(), 'panes', None, None, str(filename), str(source), str(dest),
        'png', str(filename), False, False,
    )

    assert (dest / 'Vega.rst').read_text().startswith('Altair & Vega\n=============\n\n')
