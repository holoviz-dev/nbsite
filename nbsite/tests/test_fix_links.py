import warnings

import lxml.html
import pytest

from nbsite.scripts import fix_links


def _write_page(path, body):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(f"<!DOCTYPE html><html><head><title>t</title></head><body>{body}</body></html>")


def _parse(path):
    return lxml.html.fromstring(path.read_text(encoding="utf-8"), parser=lxml.html.HTMLParser(huge_tree=True))


def _attributes(path, tag, attribute):
    tree = _parse(path)
    return [element.get(attribute) for element in tree.iter(tag)]


def test_fix_links_replaces_notebook_extension(tmp_path):
    _write_page(tmp_path / "Other.html", "")
    _write_page(tmp_path / "page.html", '<a href="Other.ipynb#section">link</a>')
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        fix_links(str(tmp_path))
    assert _attributes(tmp_path / "page.html", "a", "href") == ["Other.html#section"]


def test_fix_links_falls_back_to_unnumbered_page(tmp_path):
    _write_page(tmp_path / "Other.html", "")
    _write_page(tmp_path / "page.html", '<a href="01-Other.ipynb">link</a>')
    fix_links(str(tmp_path))
    assert _attributes(tmp_path / "page.html", "a", "href") == ["Other.html"]


def test_fix_links_warns_on_missing_notebook_link(tmp_path):
    _write_page(tmp_path / "page.html", '<a href="Missing.ipynb">link</a>')
    with pytest.warns(UserWarning, match="Found missing link Missing.html"):
        fix_links(str(tmp_path))
    assert _attributes(tmp_path / "page.html", "a", "href") == ["Missing.html"]


def test_fix_links_adds_index_to_directory_links(tmp_path):
    _write_page(
        tmp_path / "page.html",
        '<a href="sub/">sub</a><a href="https://example.com/">external</a><a href="#top">anchor</a>',
    )
    fix_links(str(tmp_path))
    assert _attributes(tmp_path / "page.html", "a", "href") == [
        "sub/index.html", "https://example.com/", "#top",
    ]


def test_fix_links_leaves_external_notebook_links(tmp_path):
    href = "https://github.com/org/repo/blob/main/examples/Other.ipynb"
    _write_page(tmp_path / "page.html", f'<a href="{href}">link</a>')
    fix_links(str(tmp_path))
    assert _attributes(tmp_path / "page.html", "a", "href") == [href]


def test_fix_links_falls_back_to_parent_assets(tmp_path):
    (tmp_path / "assets").mkdir()
    (tmp_path / "assets" / "image.png").write_bytes(b"")
    _write_page(tmp_path / "sub" / "page.html", '<img src="assets/image.png">')
    fix_links(str(tmp_path))
    assert _attributes(tmp_path / "sub" / "page.html", "img", "src") == ["../assets/image.png"]


def test_fix_links_warns_on_missing_assets_image(tmp_path):
    _write_page(tmp_path / "page.html", '<img src="assets/missing.png">')
    with pytest.warns(UserWarning, match="Found reference to missing image assets/missing.png"):
        fix_links(str(tmp_path))
    assert _attributes(tmp_path / "page.html", "img", "src") == ["assets/missing.png"]


def test_fix_links_processes_nested_pages(tmp_path):
    _write_page(tmp_path / "a" / "b" / "Other.html", "")
    _write_page(tmp_path / "a" / "b" / "page.html", '<a href="Other.ipynb">link</a>')
    fix_links(str(tmp_path))
    assert _attributes(tmp_path / "a" / "b" / "page.html", "a", "href") == ["Other.html"]


def test_fix_links_does_not_escape_base64_image_data(tmp_path):
    data = "iVBORw0KGgoAAAANSUhEUgAAAEAAAABACAYAAACqaXHeAAAABHNCSVQICAgIfAhkiAAAAAlwSFlz\nAAAB+wAAAfsBxc2miwAAABl0"
    _write_page(tmp_path / "page.html", f'<img src="data:image/png;base64,{data}">')
    fix_links(str(tmp_path))
    assert "%0A" not in (tmp_path / "page.html").read_text()
    assert _attributes(tmp_path / "page.html", "img", "src") == [
        "data:image/png;base64," + data.replace("\n", ""),
    ]


def test_fix_links_keeps_huge_embedded_output(tmp_path):
    data = "x" * 12_000_000
    _write_page(
        tmp_path / "page.html",
        f'<script type="application/json">{data}</script><a href="sub/">sub</a>',
    )
    fix_links(str(tmp_path))
    tree = lxml.html.fromstring((tmp_path / "page.html").read_text(), parser=lxml.html.HTMLParser(huge_tree=True))
    assert tree.xpath("//script")[0].text == data
    assert _attributes(tmp_path / "page.html", "a", "href") == ["sub/index.html"]


def test_fix_links_keeps_page_content(tmp_path):
    body = (
        '<div class="output"><script type="application/json">{"a": "<b>&amp;</b>"}</script>'
        '<p>café &lt;tag&gt;</p></div>'
    )
    _write_page(tmp_path / "page.html", body)
    fix_links(str(tmp_path))
    tree = lxml.html.fromstring((tmp_path / "page.html").read_text(encoding="utf-8"))
    assert tree.xpath("//script")[0].text == '{"a": "<b>&amp;</b>"}'
    assert tree.xpath("//p")[0].text_content() == "café <tag>"
