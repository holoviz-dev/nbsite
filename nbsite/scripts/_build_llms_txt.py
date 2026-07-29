"""Reusable helpers for building markdown docs and llms.txt.

Individual repos provide an `llms_config.py` module to customize source
roots, section definitions, index pages, and label formatting.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
import tempfile

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

from bs4 import BeautifulSoup

LabelBuilder = Callable[[Path], str]
PathPredicate = Callable[[Path], bool]

HTML_PAGE_SELECTORS = (
    "main#main-content",
    "article.bd-article",
    "article",
    "div.bd-content",
    "div.document",
    "body",
)

HTML_STRIP_TAGS = (
    "header",
    "nav",
    "aside",
    "footer",
    "script",
    "style",
)

MARKDOWN_STRIP_TAGS = (
    "span",
    "div",
    "em",
    "strong",
    "p",
    "small",
    "sup",
    "sub",
    "code",
    "pre",
    "section",
    "article",
    "main",
    "nav",
    "ul",
    "ol",
    "li",
    "table",
    "tbody",
    "thead",
    "tr",
    "td",
    "th",
    "blockquote",
    "kbd",
    "img",
)


def default_label(path: Path) -> str:
    return path.stem.replace("_", " ")


def index_label(path: Path) -> str:
    if path.stem == "index":
        if path.parent != Path("."):
            return path.parent.name.replace("_", " ")
        return "home"
    return default_label(path)


def _is_included(
    rel_path: Path,
    include_suffixes: Sequence[str],
    exclude_dir_names: Sequence[str],
) -> bool:
    if any(part in exclude_dir_names for part in rel_path.parts):
        return False
    return rel_path.suffix in include_suffixes


@dataclass(frozen=True)
class MarkdownSource:
    """A source tree to mirror into the markdown output tree."""

    source_dir: Path
    output_dir: Path
    rendered_source_dir: Path | None = None
    include_suffixes: tuple[str, ...] = (".md", ".ipynb", ".rst")
    exclude_dir_names: tuple[str, ...] = (".ipynb_checkpoints",)
    copy_markdown: bool = True
    convert_notebooks: bool = True


@dataclass(frozen=True)
class IndexCategory:
    """A markdown directory that should receive an index.md file."""

    directory: Path
    title: str
    description: str
    label_builder: LabelBuilder = index_label


@dataclass(frozen=True)
class LlmsSection:
    """A group of generated markdown pages to list in llms.txt."""

    title: str
    description: str
    path_prefix: Path
    label_builder: LabelBuilder = default_label
    path_filter: PathPredicate = field(default=lambda _path: True)


@dataclass(frozen=True)
class LlmsBuildConfig:
    project_title: str
    project_description: str
    markdown_root: Path
    llms_output_path: Path
    markdown_base_url: str = "/markdown"
    sources: tuple[MarkdownSource, ...] = ()
    sections: tuple[LlmsSection, ...] = ()
    index_categories: tuple[IndexCategory, ...] = ()


def _iter_source_files(source: MarkdownSource) -> Iterable[Path]:
    for path in sorted(source.source_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(source.source_dir)
        if _is_included(rel_path, source.include_suffixes, source.exclude_dir_names):
            yield path


def _convert_notebook(notebook_path: Path, output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "markdown",
            "--output-dir",
            str(output_dir),
            str(notebook_path),
        ],
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        print(f"  Warning: failed to convert {notebook_path}: {result.stderr.strip()}")
        return False
    return True


def _pandoc_command(
    input_format: str,
    output_path: Path,
    input_path: Path,
) -> list[str]:
    return [
        "pandoc",
        "-f",
        input_format,
        "-t",
        "gfm",
        "-o",
        str(output_path),
        str(input_path),
    ]


def _select_html_body(soup: BeautifulSoup):
    for selector in HTML_PAGE_SELECTORS:
        input_node = soup.select_one(selector)
        if input_node is not None:
            return input_node
    return soup


def _remove_html_wrappers(text: str) -> str:
    def _replace_anchor(match: re.Match[str]) -> str:
        attrs = match.group(1)
        inner_html = match.group(2)
        soup = BeautifulSoup(f"<a {attrs}>{inner_html}</a>", "html.parser")
        anchor = soup.a
        if anchor is None:
            return inner_html

        href = anchor.get("href", "")
        label = anchor.get_text(" ", strip=True)
        if label.startswith("[") and label.endswith("]") and len(label) > 2:
            label = label[1:-1]
        if not label:
            label = anchor.get("aria-label") or anchor.get("title") or href
        return f"[{label}]({href})" if href else label

    text = re.sub(r"<a\b([^>]*)>(.*?)</a>", _replace_anchor, text, flags=re.S)
    text = re.sub(
        r"</?(?:"
        r"span|div|em|strong|p|small|sup|sub|code|pre|section|article|main|nav|"
        r"ul|ol|li|table|tbody|thead|tr|td|th|blockquote|kbd|img"
        r")(?:\s[^>]*)?>",
        "",
        text,
        flags=re.I,
    )
    return re.sub(r"<!--.*?-->", "", text, flags=re.S)


def _normalize_markdown(text: str) -> str:
    lines: list[str] = []
    in_code_block = False
    seen_content = False
    pending_blank = False

    for raw_line in text.splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()

        if stripped.startswith("```") or stripped.startswith("~~~"):
            in_code_block = not in_code_block

        if not seen_content:
            if not stripped:
                continue
            seen_content = True

        if not stripped and not in_code_block:
            if pending_blank:
                continue
            pending_blank = True
            lines.append("")
            continue

        pending_blank = False
        lines.append(line)

    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines) + "\n"


def _convert_rst(
    rst_path: Path,
    output_path: Path,
    rendered_html_path: Path | None = None,
) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    input_path = rst_path
    input_format = "rst"
    temp_path: Path | None = None

    if rendered_html_path is not None and rendered_html_path.exists():
        html = rendered_html_path.read_text(encoding="utf-8")
        soup = BeautifulSoup(html, "html.parser")
        input_node = _select_html_body(soup)

        for tag in input_node.find_all(HTML_STRIP_TAGS):
            tag.decompose()

        extracted_html = str(input_node)
        temp = tempfile.NamedTemporaryFile(
            "w",
            suffix=".html",
            delete=False,
            encoding="utf-8",
        )
        try:
            temp.write(extracted_html)
            temp.close()
            temp_path = Path(temp.name)
            input_path = temp_path
            input_format = "html"
        finally:
            if not temp.closed:
                temp.close()
    try:
        result = subprocess.run(
            _pandoc_command(input_format, output_path, input_path),
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            print(f"  Warning: failed to convert {rst_path}: {result.stderr.strip()}")
            return False
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    text = output_path.read_text(encoding="utf-8")
    text = _remove_html_wrappers(text)
    output_path.write_text(_normalize_markdown(text), encoding="utf-8")
    return True


def build_markdown_docs(
    sources: Sequence[MarkdownSource],
    markdown_root: Path,
) -> list[Path]:
    """Copy markdown files and convert notebooks into the markdown tree."""

    generated: list[Path] = []
    for source in sources:
        for path in _iter_source_files(source):
            rel = path.relative_to(source.source_dir)
            destination = source.output_dir / rel

            if path.suffix == ".md" and source.copy_markdown:
                destination.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(path, destination)
                generated.append(destination.relative_to(markdown_root))
                print(f"  Copied {destination.relative_to(markdown_root)}")
                continue

            if path.suffix == ".rst" and source.copy_markdown:
                md_destination = destination.with_suffix(".md")
                rendered_html_path = None
                if source.rendered_source_dir is not None:
                    rendered_html_path = source.rendered_source_dir / rel.with_suffix(".html")
                if _convert_rst(path, md_destination, rendered_html_path):
                    md_rel = md_destination.relative_to(markdown_root)
                    generated.append(md_rel)
                    print(f"  Converted {md_rel}")
                continue

            if path.suffix == ".ipynb" and source.convert_notebooks:
                if _convert_notebook(path, destination.parent):
                    md_rel = destination.with_suffix(".md").relative_to(markdown_root)
                    generated.append(md_rel)
                    print(f"  Converted {md_rel}")

    return generated


def generate_index_pages(
    markdown_root: Path,
    categories: Sequence[IndexCategory],
    markdown_base_url: str,
) -> list[Path]:
    """Create index.md pages for categories that contain generated markdown."""

    generated_indexes: list[Path] = []
    for category in categories:
        category_dir = markdown_root / category.directory
        if not category_dir.exists():
            continue

        md_files = sorted(f for f in category_dir.glob("*.md") if f.name != "index.md")
        if not md_files:
            continue

        lines = [
            f"# {category.title}",
            "",
            f"{category.description}",
            "",
        ]
        for md_file in md_files:
            rel_md = md_file.relative_to(markdown_root).as_posix()
            lines.append(f"- [{category.label_builder(md_file)}]({markdown_base_url}/{rel_md})")

        index_file = category_dir / "index.md"
        index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        generated_indexes.append(index_file.relative_to(markdown_root))
        print(f"  Generated index: {index_file.relative_to(markdown_root)}")

    return generated_indexes


def _build_links(
    paths: Iterable[Path],
    markdown_base_url: str,
    label_builder: LabelBuilder,
) -> list[str]:
    return [f"- [{label_builder(path)}]({markdown_base_url}/{path.as_posix()})" for path in sorted(paths)]


def _matches_prefix(path: Path, prefix: Path) -> bool:
    return prefix in {Path(), Path(".")} or path.is_relative_to(prefix)


def generate_llms_txt(
    config: LlmsBuildConfig,
    generated_paths: Sequence[Path],
    generated_indexes: Sequence[Path] = (),
) -> Path:
    """Write llms.txt for a repo using the generated markdown paths."""

    lines = [
        f"# {config.project_title}",
        "",
        config.project_description,
        "",
        (f"All documentation is available as markdown files under {config.markdown_base_url}/."),
        "",
    ]

    for section in config.sections:
        section_paths = [path for path in generated_paths if _matches_prefix(path, section.path_prefix) and section.path_filter(path)]
        if not section_paths:
            continue

        lines.extend([f"## {section.title}", "", f"{section.description}", ""])
        lines.extend(
            _build_links(
                section_paths,
                config.markdown_base_url,
                section.label_builder,
            )
        )
        lines.append("")

    if generated_indexes:
        lines.extend(["## Reference Indexes", ""])
        lines.extend(
            _build_links(
                generated_indexes,
                config.markdown_base_url,
                index_label,
            )
        )
        lines.append("")

    config.llms_output_path.parent.mkdir(parents=True, exist_ok=True)
    config.llms_output_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Generated {config.llms_output_path}")
    return config.llms_output_path


def build_llms_docs(config: LlmsBuildConfig) -> Path:
    """Run the full markdown and llms.txt build for a repo."""

    config.markdown_root.mkdir(parents=True, exist_ok=True)
    print("Building markdown docs...")
    generated_paths = build_markdown_docs(config.sources, config.markdown_root)
    print("Generating category indexes...")
    generated_indexes = generate_index_pages(
        config.markdown_root,
        config.index_categories,
        config.markdown_base_url,
    )
    print("Generating llms.txt...")
    return generate_llms_txt(config, generated_paths, generated_indexes)
