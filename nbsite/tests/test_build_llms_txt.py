from pathlib import Path

from nbsite.scripts import MarkdownSource, build_markdown_docs


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
