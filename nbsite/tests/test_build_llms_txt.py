from pathlib import Path

import pytest

from nbsite.scripts import MarkdownSource, build_markdown_docs
from nbsite.scripts._build_llms_txt import _normalize_markdown


def _make_fake_pandoc_output(input_suffix: str) -> str:
    return (
        "\n\n\n"
        "# example\n\n\n"
        "<div class=\"automodule\" members=\"\" show-inheritance=\"\">\n\n"
        "<a href=\"../index.html\" class=\"nav-link\" "
        "aria-label=\"Home\"><em></em></a>\n"
        "<span class=\"pre\">class</span> example\n\n"
        f"converted from {input_suffix}\n\n"
        "</div>\n"
    )


def test_build_markdown_docs_converts_rst_to_md(tmp_path, monkeypatch):
    source_dir = tmp_path / "doc"
    source_dir.mkdir()
    output_dir = tmp_path / "builtdocs" / "markdown"
    rendered_dir = tmp_path / "builtdocs"
    rst_file = source_dir / "reference_manual" / "example.rst"
    rst_file.parent.mkdir(parents=True)
    rst_file.write_text("example\n=======\n")
    html_file = rendered_dir / "reference_manual" / "example.html"
    html_file.parent.mkdir(parents=True)
    html_file.write_text("<h1>example</h1>")

    def fake_run(cmd, capture_output, text):
        output_path = Path(cmd[cmd.index("-o") + 1])
        input_path = Path(cmd[-1])
        output_path.write_text(_make_fake_pandoc_output(input_path.suffix))

        class Result:
            returncode = 0
            stderr = ""

        return Result()

    monkeypatch.setattr("nbsite.scripts._build_llms_txt.subprocess.run", fake_run)

    generated = build_markdown_docs(
        (
            MarkdownSource(
                source_dir=source_dir,
                output_dir=output_dir,
                rendered_source_dir=rendered_dir,
            ),
        ),
        output_dir,
    )

    assert generated == [Path("reference_manual/example.md")]
    output_text = (output_dir / "reference_manual" / "example.md").read_text()
    assert output_text.startswith("# example\n")
    assert not output_text.startswith("\n")
    assert "converted from .html" in output_text
    assert "[Home](../index.html)" in output_text
    assert "class example" in output_text
    assert "<" not in output_text
    assert "\n\n\n" not in output_text


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
