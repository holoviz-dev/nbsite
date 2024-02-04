import pytest

from nbsite.nbbuild import FixNotebookLinks


class TestFixNotebookLinks:

    @pytest.mark.parametrize(
        "markdowntext, expected_output",
        [
            ("foo [a](b.ipynb) bar", [("[a](b.ipynb)", "b.ipynb")]),
            ("foo [a](b.md) bar", []),
        ],
    )
    def test_get_links(self, markdowntext, expected_output):
        assert list(FixNotebookLinks._get_links(markdowntext)) == expected_output
