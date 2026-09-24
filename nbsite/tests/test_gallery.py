import os

from types import SimpleNamespace

import nbformat
import pytest

from nbsite.gallery import gen


@pytest.mark.parametrize('source_override', [False, True], ids=['default', 'source'])
@pytest.mark.parametrize('as_pyodide', [False, True], ids=['rst', 'pyodide'])
@pytest.mark.parametrize('host', ['GitHub', 'assets'])
@pytest.mark.parametrize('nested', [False, True], ids=['unsectioned', 'section-and-backend'])
def test_gallery_source_paths(tmp_path, monkeypatch, source_override, as_pyodide, host, nested):
    """Read examples from source while writing documents under the gallery key and linking to the original files."""
    page = 'reference/classic'
    source = 'reference' if source_override else page
    section = 'elements' if nested else ''
    backend = 'bokeh' if nested else ''
    parts = [p for p in (section, backend) if p]
    doc_dir = tmp_path / 'doc'
    examples_dir = tmp_path / 'examples'
    src_dir = examples_dir.joinpath(source, *parts)
    src_dir.mkdir(parents=True)
    filename = src_dir / 'example.ipynb'
    nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# Original')]), filename)
    if source_override:
        decoy_dir = examples_dir.joinpath(page, *parts)
        decoy_dir.mkdir(parents=True)
        nbformat.write(nbformat.v4.new_notebook(cells=[nbformat.v4.new_markdown_cell('# Decoy')]), decoy_dir / filename.name)

    thumbnails = []

    def resolve_thumbnail(thumb_url_base, dest_dir, basename, download, no_image_thumb):
        thumbnails.append(thumb_url_base)
        return 0, os.path.join(dest_dir, 'thumbnails', f'{basename}.png'), 'png', 'Used existing'

    monkeypatch.setattr(gen, '_resolve_thumbnail', resolve_thumbnail)
    monkeypatch.setattr(gen, 'resize_pad', lambda path: None)
    monkeypatch.setattr(gen, 'get_deployed_url', lambda urls, basename: None)

    content = {'title': 'Examples', 'sections': [section], 'backends': [backend] if backend else []}
    if source_override:
        content['source'] = source
    conf = dict(gen.DEFAULT_GALLERY_CONF, **{
        'examples_dir': '../examples',
        'galleries': {page: content},
        'host': host,
        'github_org': 'holoviz',
        'github_project': 'demo',
        'jupyterlite_url': 'https://lite.example/lab',
        'as_pyodide': as_pyodide,
        'only_use_existing': True,
        'thumbnail_url': 'https://thumb.example',
    })
    app = SimpleNamespace(
        config=SimpleNamespace(nbsite_gallery_conf=conf, html_static_path=['_static'], html_theme_options={}),
        builder=SimpleNamespace(srcdir=str(doc_dir)),
    )
    gen.generate_gallery(app, page)

    dest = doc_dir.joinpath(page, *parts)
    output = (dest / ('example.md' if as_pyodide else 'example.rst')).read_text()
    index = (doc_dir / page / 'index.rst').read_text()
    source_path = '/'.join(['examples', source, *parts, filename.name])
    assert 'example' in index
    thumbnail_path = '/'.join([page, *parts, 'thumbnails', 'example.png'])
    assert f'.. image:: /{thumbnail_path}' in index
    assert str(tmp_path) not in index
    assert 'Decoy' not in output
    if as_pyodide:
        assert '# Original' in output
    else:
        assert f'.. notebook:: demo {os.path.relpath(filename, dest)}' in output
    if host == 'GitHub':
        assert f'https://raw.githubusercontent.com/holoviz/demo/main/{source_path}' in output
    else:
        assert f'/assets/{source_path}' in output
    if source_override:
        lite_path = '/'.join([source, *parts, filename.name])
        assert f'https://lite.example/lab?path=/{lite_path}' in output
    elif as_pyodide:
        backend_slug = '/{backend}' if backend else ''
        assert f'https://lite.example/lab?path=/{page}/{section}{backend_slug}/{filename.name}' in output
    else:
        assert 'https://lite.example/lab' in output
    assert thumbnails == ['/'.join(['https://thumb.example', page, *parts, 'example'])]


@pytest.mark.parametrize('thumbnail_source', [None, 'reference'])
def test_gallery_thumbnail_source(tmp_path, monkeypatch, thumbnail_source):
    """Thumbnail URLs default to the destination key but can follow a separate source path."""
    page = 'reference/classic'
    src_dir = tmp_path / 'examples' / 'reference'
    src_dir.mkdir(parents=True)
    (src_dir / 'example.py').write_text('print("source")')
    urls = []

    def resolve_thumbnail(thumb_url_base, dest_dir, basename, download, no_image_thumb):
        urls.append(thumb_url_base)
        return 0, os.path.join(dest_dir, 'thumbnails', 'example.png'), 'png', 'Used existing'

    monkeypatch.setattr(gen, '_resolve_thumbnail', resolve_thumbnail)
    monkeypatch.setattr(gen, 'resize_pad', lambda path: None)
    content = {'title': 'Examples', 'source': 'reference', 'sections': [''], 'extensions': ['*.py'], 'thumbnail_url': 'https://custom.example'}
    if thumbnail_source is not None:
        content['thumbnail_source'] = thumbnail_source
    conf = dict(gen.DEFAULT_GALLERY_CONF, **{'examples_dir': '../examples', 'galleries': {page: content}, 'only_use_existing': True})
    app = SimpleNamespace(
        config=SimpleNamespace(nbsite_gallery_conf=conf, html_static_path=['_static'], html_theme_options={}),
        builder=SimpleNamespace(srcdir=str(tmp_path / 'doc')),
    )
    gen.generate_gallery(app, page)
    assert urls == [f'https://custom.example/{thumbnail_source or page}/example']


def test_gallery_source_discovers_sections(tmp_path, monkeypatch):
    """Discovered source sections are names relative to the destination gallery, not absolute paths."""
    (tmp_path / 'doc').mkdir()
    src_dir = tmp_path / 'examples' / 'reference' / 'elements'
    src_dir.mkdir(parents=True)
    (src_dir / 'example.py').write_text('print("source")')
    monkeypatch.setattr(gen, '_resolve_thumbnail', lambda *args, **kwargs: (0, '', 'png', 'Used existing'))
    monkeypatch.setattr(gen, 'resize_pad', lambda path: None)
    page = 'reference/classic'
    conf = dict(gen.DEFAULT_GALLERY_CONF, **{
        'examples_dir': '../examples',
        'galleries': {page: {'title': 'Examples', 'source': 'reference', 'extensions': ['*.py']}},
        'only_use_existing': True,
    })
    app = SimpleNamespace(
        config=SimpleNamespace(nbsite_gallery_conf=conf, html_static_path=['_static'], html_theme_options={}),
        builder=SimpleNamespace(srcdir=str(tmp_path / 'doc')),
    )
    gen.generate_gallery(app, page)

    dest = tmp_path / 'doc' / page
    assert (dest / 'elements' / 'example.rst').exists()
    assert 'elements/index' in (dest / 'index.rst').read_text()
