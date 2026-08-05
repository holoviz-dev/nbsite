from pathlib import Path

import pytest

from nbsite.scripts._build_llms_txt import (
    LlmsBuildConfig, LlmsSection, MarkdownSource, _convert_notebook,
    _deepen_relative_links, _normalize_markdown, _strip_markdown_noise,
    build_markdown_docs, generate_llms_txt,
)

# def _make_fake_pandoc_output(input_suffix: str) -> str:
#     return (
#         "\n\n\n"
#         "# example\n\n\n"
#         "<div class=\"automodule\" members=\"\" show-inheritance=\"\">\n\n"
#         "<a href=\"../index.html\" class=\"nav-link\" "
#         "aria-label=\"Home\"><em></em></a>\n"
#         "<span class=\"pre\">class</span> example\n\n"
#         f"converted from {input_suffix}\n\n"
#         "</div>\n"
#     )


def test_build_markdown_docs_exclude_files(tmp_path):
    source_dir = tmp_path / "doc"
    source_dir.mkdir(exist_ok=True)
    output_dir = tmp_path / "builtdocs" / "markdown"
    keep = source_dir / "keep.md"
    drop = source_dir / "releases.md"
    keep.write_text("# Keep\n")
    drop.write_text("# Releases\n")

    generated = build_markdown_docs(
        (
            MarkdownSource(
                source_dir=source_dir,
                output_dir=output_dir,
                exclude_files=(Path("releases.md"),),
            ),
        ),
        output_dir,
    )

    assert Path("keep.md") in generated
    assert Path("releases.md") not in generated
    assert (output_dir / "keep.md").exists()
    assert not (output_dir / "releases.md").exists()


def test_build_markdown_docs_converts_rst_to_md(tmp_path):
    source_dir = tmp_path / "doc"
    source_dir.mkdir()
    output_dir = tmp_path / "builtdocs" / "markdown"
    rst_file = source_dir / "reference_manual" / "example.rst"
    rst_file.parent.mkdir(parents=True)
    rst_file.write_text("example\n=======\n\nThis is an example.\n")

    generated = build_markdown_docs(
        (
            MarkdownSource(
                source_dir=source_dir,
                output_dir=output_dir,
            ),
        ),
        output_dir,
    )

    assert generated == [Path("reference_manual/example.md")]
    output_text = (output_dir / "reference_manual" / "example.md").read_text()
    assert "example" in output_text.lower()
    assert "This is an example." in output_text


def test_build_markdown_docs_output_dir_outside_markdown_root(tmp_path):
    source_dir = tmp_path / "doc"
    source_dir.mkdir()
    markdown_root = tmp_path / "markdown"
    output_dir = tmp_path / "elsewhere"
    (source_dir / "guide.md").write_text("# guide\n")

    with pytest.raises(ValueError, match="must be.*located under markdown_root"):
        build_markdown_docs(
            (
                MarkdownSource(
                    source_dir=source_dir,
                    output_dir=output_dir,
                ),
            ),
            markdown_root,
        )


def test_normalize_markdown_preserves_code_block_whitespace():
    text = "text\n\n```\ndef f():\n    return 1   \n```\n"
    assert _normalize_markdown(text) == "text\n\n```\ndef f():\n    return 1   \n```\n"


def test_normalize_markdown_collapses_blank_lines_outside_code_blocks():
    text = "# heading\n\n\n\npara\n\n\n```\n\n\n```\n"
    assert _normalize_markdown(text) == "# heading\n\npara\n\n```\n\n\n```\n"


def test_generate_llms_txt_grouped_subsections(tmp_path):
    config = LlmsBuildConfig(
        project_title="Demo",
        project_description="Demo docs.",
        markdown_root=tmp_path,
        llms_output_path=tmp_path / "llms.txt",
        markdown_base_url="/markdown",
        sections=(
            LlmsSection(
                title="how to",
                description="How-to guides.",
                path_prefix=Path("how_to"),
                group="Documentation",
            ),
            LlmsSection(
                title="tutorials",
                description="Tutorials.",
                path_prefix=Path("tutorials"),
                group="Documentation",
            ),
            LlmsSection(
                title="Reference",
                description="Component reference.",
                path_prefix=Path("reference"),
            ),
        ),
    )
    paths = [
        Path("how_to/brand.md"),
        Path("tutorials/basic.md"),
        Path("reference/widgets/index.md"),
    ]
    generate_llms_txt(config, paths)
    lines = (tmp_path / "llms.txt").read_text().splitlines()
    assert "## Documentation" in lines
    assert "### how to" in lines
    assert "> How-to guides." in lines
    assert "### tutorials" in lines
    assert "## Reference" in lines
    assert "### " not in "".join(lines[lines.index("## Reference"):])


def test_generate_llms_txt_link_descriptions(tmp_path):
    config = LlmsBuildConfig(
        project_title="Demo",
        project_description="Demo docs.",
        markdown_root=tmp_path,
        llms_output_path=tmp_path / "llms.txt",
        markdown_base_url="/markdown",
        sections=(
            LlmsSection(
                title="Reference",
                description="Component reference pages.",
                path_prefix=Path("reference"),
                description_builder=lambda path: "an input widget" if path.parent.name == "widgets" else None,
            ),
        ),
    )
    paths = [Path("reference/widgets/index.md"), Path("reference/panes/index.md")]
    generate_llms_txt(config, paths)
    lines = (tmp_path / "llms.txt").read_text().splitlines()
    assert any(line.endswith(": an input widget") and "/widgets/index.md" in line for line in lines)
    assert any("/panes/index.md" in line and not line.endswith(": an input widget") for line in lines)


# def test_needs_sphinx_resolution_detects_directives(tmp_path):
#     notebook = tmp_path / "api.ipynb"
#     notebook.write_text(
#         '{"cells": [{"cell_type": "markdown", "source": '
#         '[".. automethod:: hvPlot.line"]}]}'
#     )
#     assert _needs_sphinx_resolution(notebook)

#     plain = tmp_path / "gallery.ipynb"
#     plain.write_text(
#         '{"cells": [{"cell_type": "markdown", "source": '
#         '["# Title", "Some prose"]}]}'
#     )
#     assert not _needs_sphinx_resolution(plain)


def test_strip_markdown_noise_removes_html_conversion_artifacts():
    text = (
        "# hvPlot.bar[#](#hvplot-bar)\n\n"
        "hvPlot.bar(*x=None*)[source](https://github.com/example)[#](#hvplot.hvPlot.bar)\n\n"
        "[Home](../index.html)\n\n"
        "[Lag Plots reference](../../ref/api/manual/hvplot.plotting.lag_plot.ipynb)\n\n"
        "This web page was generated from a Jupyter notebook and not all\n"
        "interactivity will work on this website.\n\n"
        "On this page\n\n"
        "[ Edit on\n"
        "GitHub](https://github.com/edit)\n\n"
        "[ Show Source](../../_sources/api.ipynb)\n"
    )
    cleaned = _strip_markdown_noise(text)
    assert "[#]" not in cleaned
    assert "[source]" not in cleaned
    assert "This web page" not in cleaned
    assert "Edit on" not in cleaned
    assert "Show Source" not in cleaned
    assert "[Home](../index.md)" in cleaned
    assert "../../ref/api/manual/hvplot.plotting.lag_plot.md" in cleaned


def test_strip_markdown_noise_unescapes_python_kwargs_asterisks():
    text = "hvPlot.bar(x=None, \\*\\*kwds)\\n"
    cleaned = _strip_markdown_noise(text)
    assert "**kwds" in cleaned
    assert r"\*\*" not in cleaned


def test_deepen_relative_links_only_deepens_shared_assets():
    text = (
        "![bar](../_images/simple_area.png)\n\n"
        "[plotting options](../../ref/plotting_options/index.html)\n\n"
        "[external](https://example.com/img.png)\n"
    )
    deepened = _deepen_relative_links(text)
    assert "../../_images/simple_area.png" in deepened
    assert "../../ref/plotting_options/index.html" in deepened
    assert "https://example.com/img.png" in deepened


def test_convert_notebook_returns_markdown(tmp_path):
    notebook = tmp_path / "simple.ipynb"
    notebook.write_text(
        '{"cells": [{"cell_type": "markdown", "source": ["# Hello\\n", "World"]}, '
        '{"cell_type": "code", "source": ["print(1)"], "outputs": []}]}'
    )
    result = _convert_notebook(notebook)
    assert result is not None
    assert "# Hello" in result
    assert "World" in result


def test_convert_notebook_handles_non_notebook(tmp_path):
    text_file = tmp_path / "notes.txt"
    text_file.write_text("Just some text")
    result = _convert_notebook(text_file)
    assert result is not None
    assert "Just some text" in result
