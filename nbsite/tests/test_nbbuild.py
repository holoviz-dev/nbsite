import os
import textwrap

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
            # Case: Relative path
            (
                "foo [a](../foo/b.ipynb#spam) bar.",
                [("[a](../foo/b.ipynb#spam)", "../foo/b.ipynb")],
            ),
            # Case: Multiple links only one .ipynb
            (
                "[HoloViews](https://holoviews.org) ([Interactivity](3_Interactivity.ipynb)).",
                [("[Interactivity](3_Interactivity.ipynb)", "3_Interactivity.ipynb")],
            ),
        ],
    )
    def test_extract_links(self, markdowntext, expected_output):
        assert list(FixNotebookLinks._extract_links(markdowntext)) == expected_output

    @pytest.mark.parametrize(
        "notebook_stem, expected_output",
        [
            # simple
            ("notebook.ipynb", ["notebook.rst", "notebook.md"]),
            (
                # Numeric with space
                "01 notebook.ipynb",
                ["01 notebook.rst", "01 notebook.md", "notebook.rst", "notebook.md"],
            ),
            (
                # Numeric with dash
                "01-notebook.ipynb",
                ["01-notebook.rst", "01-notebook.md", "notebook.rst", "notebook.md"],
            ),
            (
                # Numeric with underscore
                "01_notebook.ipynb",
                ["01_notebook.rst", "01_notebook.md", "notebook.rst", "notebook.md"],
            ),
            (
                # Numeric with relative path
                "../foo/01_notebook.ipynb",
                [
                    "../foo/01_notebook.rst",
                    "../foo/01_notebook.md",
                    "../foo/notebook.rst",
                    "../foo/notebook.md",
                ],
            ),
        ],
    )
    def test_iter_source_file_candidates(self, notebook_stem, expected_output):
        output = list(FixNotebookLinks._iter_source_file_candidates(notebook_stem))
        assert output == expected_output

    @pytest.mark.parametrize(
        "nb_link, target_filename, expected_output",
        [
            ("[a](b.ipynb)", "file.rst", "[a](file.rst)"),
            ("[a](b.ipynb#spam)", "file.rst", "[a](file.rst#spam)"),
            (
                "[sometext](../../somepath/subject.ipynb#spam)",
                "../../otherpath/file.rst",
                "[sometext](../../otherpath/file.rst#spam)",
            ),
        ],
    )
    def test_create_target_link(self, nb_link, target_filename, expected_output):
        assert (
            FixNotebookLinks._create_target_link(nb_link, target_filename)
            == expected_output
        )

    def test_replace_notebook_links(self):

        nb_dir = "/tmp/somepath/user_guide"

        class FixNotebookLinksMockFiles(FixNotebookLinks):

            @staticmethod
            def _file_exists(file_path):
                normalized_path = os.path.normpath(file_path).replace("\\", "/")
                # mock existence of certain files
                return normalized_path in {
                    "/tmp/somepath/user_guide/first.rst",
                    "/tmp/somepath/user_guide/02-Second_Notebook.md",
                    "/tmp/notebooks/Third_Notebook.rst",
                    "/tmp/somepath/foo/Notebook.rst",
                }

        text = textwrap.dedent(
            """
        This is a long text with [a link](first.ipynb) here and another
        [link to a file](02-Second_Notebook.ipynb) here.

        It is also possible to have links with relative paths like
        [this](../../notebooks/03-Third_Notebook.ipynb).

        The text may also contain links with anchors.
        Example: [link to anchor](../foo/Notebook.ipynb#spam)

        Links which do not point to .ipynb files are not touched.
        Example [link untouched](../something.rst#eggs)
        """.strip(
                "\n"
            )
        )

        expected_output = textwrap.dedent(
            """
        This is a long text with [a link](first.rst) here and another
        [link to a file](02-Second_Notebook.md) here.

        It is also possible to have links with relative paths like
        [this](../../notebooks/Third_Notebook.rst).

        The text may also contain links with anchors.
        Example: [link to anchor](../foo/Notebook.rst#spam)

        Links which do not point to .ipynb files are not touched.
        Example [link untouched](../something.rst#eggs)
        """.strip(
                "\n"
            )
        )

        processor = FixNotebookLinksMockFiles(nb_dir)
        assert processor.replace_notebook_links(text, nb_dir) == expected_output
