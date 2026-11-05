from unittest import mock

import pytest

from nbsite.gallery import gen

pytest.importorskip("bs4")
pytest.importorskip("lxml")


def deployed_examples(html, status_code=200):
    response = mock.Mock(status_code=status_code, content=html.encode())
    with mock.patch.object(gen.requests, "get", return_value=response):
        return gen.get_deployed_examples("https://example.com")


@pytest.mark.parametrize(
    "html,expected",
    [
        (
            '<div class="list-group"><h4>a</h4><h4>b</h4></div>',
            ["a", "b"],
        ),
        (
            '<ul class="cards-grid"><li><a class="card-link" href="./a" id="/a">A</a></li></ul>',
            ["a"],
        ),
        (
            '<ul id="cards" class="pn-grid"><li><a class="pn-card-link" href="./a" id="/a">'
            '<h2>A</h2><span>/a</span></a></li></ul>',
            ["a"],
        ),
        ('<ul><li><a href="./a">a</a></li></ul>', ["a"]),
        ("<html><body><p>No apps</p></body></html>", []),
        ("", []),
    ],
    ids=["list-group", "cards-grid", "pn-grid", "plain-ul", "no-list", "empty"],
)
def test_get_deployed_examples(html, expected):
    assert deployed_examples(html) == expected


def test_get_deployed_examples_bad_status():
    assert deployed_examples("<ul><li><a>a</a></li></ul>", status_code=404) == []
