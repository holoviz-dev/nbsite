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
            # Case: Link has an anchor
            (
                "foo [a](b.ipynb#some-anchor) bar",
                [("[a](b.ipynb#some-anchor)", "b.ipynb")],
            ),
            # Case: Two links has an anchor
            (
                "foo [a](b.ipynb#spam) bar [c](d.ipynb#eggs) baz.",
                [("[a](b.ipynb#spam)", "b.ipynb"), ("[c](d.ipynb#eggs)", "d.ipynb")],
            ),
        ],
    )
    def test_extract_links(self, markdowntext, expected_output):
        assert list(FixNotebookLinks._extract_links(markdowntext)) == expected_output

    @pytest.mark.parametrize(
        "notebook_filename, expected_output",
        [
            # Case: Simple notebook name. No numbers
            ("notebook.ipynb", ["notebook.rst", "notebook.md"]),
            (
                "01 notebook.ipynb",
                ["01 notebook.rst", "notebook.rst", "01 notebook.md", "notebook.md"],
            ),
            (
                "01-notebook.ipynb",
                ["01-notebook.rst", "notebook.rst", "01-notebook.md", "notebook.md"],
            ),
            (
                "01_notebook.ipynb",
                ["01_notebook.rst", "notebook.rst", "01_notebook.md", "notebook.md"],
            ),
        ],
    )
    def test_get_potential_link_targets(self, notebook_filename, expected_output):
        output = list(FixNotebookLinks._get_potential_link_targets(notebook_filename))
        assert output == expected_output
