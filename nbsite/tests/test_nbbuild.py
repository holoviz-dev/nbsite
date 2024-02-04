import pytest

from nbsite.nbbuild import FixNotebookLinks


class TestFixNotebookLinks:

    @pytest.mark.parametrize(
        "markdowntext, expected_output",
        [
            # Case: one link in the text
            ("foo [a](b.ipynb) bar", [("[a](b.ipynb)", "b.ipynb")]),
            # Case: no link to .ipynb
            ("foo [a](b.md) bar", []),
            # Case: two links in the text
            (
                "foo [a](b.ipynb) bar [c](d.ipynb) baz.",
                [("[a](b.ipynb)", "b.ipynb"), ("[c](d.ipynb)", "d.ipynb")],
            ),
        ],
    )
    def test_get_links(self, markdowntext, expected_output):
        assert list(FixNotebookLinks._get_links(markdowntext)) == expected_output
