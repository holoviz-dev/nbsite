import pytest

from nbsite.nbbuild import FixNotebookLinks


class TestFixNotebookLinks:

    @pytest.mark.parametrize(
        "markdowntext, expected_output",
        [
            # Case: one link in the text
            ("foo [a](b.ipynb) bar", [("[a](b.ipynb)", "b")]),
            # Case: no link to .ipynb
            ("foo [a](b.md) bar", []),
            # Case: two links in the text
            (
                "foo [a](b.ipynb) bar [c](d.ipynb) baz.",
                [("[a](b.ipynb)", "b"), ("[c](d.ipynb)", "d")],
            ),
            # Case: Link has an anchor
            (
                "foo [a](b.ipynb#some-anchor) bar",
                [("[a](b.ipynb#some-anchor)", "b")],
            ),
            # Case: Two links has an anchor
            (
                "foo [a](b.ipynb#spam) bar [c](d.ipynb#eggs) baz.",
                [("[a](b.ipynb#spam)", "b"), ("[c](d.ipynb#eggs)", "d")],
            ),
        ],
    )
    def test_extract_links(self, markdowntext, expected_output):
        assert list(FixNotebookLinks._extract_links(markdowntext)) == expected_output

    @pytest.mark.parametrize(
        "notebook_stem, expected_output",
        [
            ("notebook", ["notebook.rst", "notebook.md"]),
            (
                "01 notebook",
                ["01 notebook.rst", "notebook.rst", "01 notebook.md", "notebook.md"],
            ),
            (
                "01-notebook",
                ["01-notebook.rst", "notebook.rst", "01-notebook.md", "notebook.md"],
            ),
            (
                "01_notebook",
                ["01_notebook.rst", "notebook.rst", "01_notebook.md", "notebook.md"],
            ),
        ],
    )
    def test_get_potential_link_targets(self, notebook_stem, expected_output):
        output = list(FixNotebookLinks._get_potential_link_targets(notebook_stem))
        assert output == expected_output