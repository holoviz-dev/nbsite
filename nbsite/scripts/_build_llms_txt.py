"""Reusable helpers for building markdown docs and llms.txt.

Individual repos provide an `llms_config.py` module to customize source
roots, section definitions, index pages, and label formatting.
"""

from __future__ import annotations

import json
import re
import shutil
import subprocess
import sys
import tempfile

from dataclasses import dataclass, field
from itertools import groupby
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

SPHINX_DIRECTIVE_PATTERN = re.compile(
    r"\.\.\s+(automethod|autofunction|autosummary|autoclass|autodata|"
    r"automodule|currentmodule|plotting-options-table|backend-styling-options)"
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
    exclude_files: Sequence[Path],
) -> bool:
    if any(part in exclude_dir_names for part in rel_path.parts):
        return False
    if rel_path in exclude_files:
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
    exclude_files: tuple[Path, ...] = ()
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
    """A group of generated markdown pages to list in llms.txt.

    If ``group`` is set the section is rendered as a ``###`` subsection
    nested under a ``## <group>`` heading (matching the PMUi layout).
    ``description_builder`` optionally appends ``: <description>`` to each
    bullet link in the section.
    """

    title: str
    description: str
    path_prefix: Path
    label_builder: LabelBuilder = default_label
    path_filter: PathPredicate = field(default=lambda _path: True)
    group: str | None = None
    group_description: str | None = None
    description_builder: Callable[[Path], str | None] | None = None
    note: str | None = None
    url_pattern: str | None = None


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
        if _is_included(rel_path, source.include_suffixes, source.exclude_dir_names, source.exclude_files):
            yield path


def _needs_sphinx_resolution(notebook_path: Path) -> bool:
    """Whether a notebook contains Sphinx directives that nbconvert leaves unresolved."""
    try:
        with open(notebook_path, encoding="utf-8") as f:
            notebook = json.load(f)
    except (OSError, ValueError):
        return False
    for cell in notebook.get("cells", []):
        source = "".join(cell.get("source", []))
        if SPHINX_DIRECTIVE_PATTERN.search(source):
            return True
    return False


def _run_command(command: list[str], warning_context: str) -> bool:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return True
    print(f"  Warning: failed to convert {warning_context}: {result.stderr.strip()}")
    return False


def _convert_notebook(notebook_path: Path, output_dir: Path) -> bool:
    output_dir.mkdir(parents=True, exist_ok=True)
    return _run_command(
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
        str(notebook_path),
    )


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
    text = re.sub(
        r"<span\b[^>]*title=\"Extension loaded\.[^\"]*\"[^>]*>ⓘ</span>",
        "",
        text,
        flags=re.I | re.S,
    )
    text = re.sub(r"<script\b.*?>.*?</script>", "", text, flags=re.I | re.S)
    text = re.sub(r"<style\b.*?>.*?</style>", "", text, flags=re.I | re.S)

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
    strip_tags = "|".join(re.escape(tag) for tag in MARKDOWN_STRIP_TAGS)
    text = re.sub(
        rf"</?(?:{strip_tags})(?:\s[^>]*)?>",
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
        was_in_code_block = in_code_block
        stripped = raw_line.strip()

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
        line = raw_line if was_in_code_block else raw_line.rstrip()
        lines.append(line)

    while lines and not lines[0]:
        lines.pop(0)
    while lines and not lines[-1]:
        lines.pop()

    return "\n".join(lines) + "\n"


def _strip_markdown_noise(text: str) -> str:
    """Remove Sphinx/HTML-conversion artifacts that carry no value for LLMs."""
    # Header self-reference anchors: "## Title[#](#title)"
    text = re.sub(r"\s*\[#\]\(#[^)]*\)", "", text)
    # "[source]" links pointing at the source code on GitHub
    text = re.sub(r"\[source\]\([^)]*\)", "", text)
    # Sphinx "This web page was generated from a Jupyter notebook..." footer and
    # the "On this page" / "Edit on GitHub" / "Show Source" navigation block
    text = re.sub(
        (
            r"\nThis web page was generated from a Jupyter notebook and not all\s*\n?"
            r"interactivity will work on this website\.\s*\n*On this page\s*\n*"
            r"\[\s*Edit on\s*\n?GitHub\]\([^)]*\)\s*\n*"
            r"\[\s*Show\s*\n?Source\]\([^)]*\)"
        ),
        "",
        text,
        flags=re.S,
    )
    text = re.sub(
        r"\n*\[\s*Edit on\s*\n?GitHub\]\([^)]*\)\s*\n*\[\s*Show\s*\n?Source\]\([^)]*\)\n*",
        "",
        text,
        flags=re.S,
    )
    # Rewrite internal links to their markdown pages: rendered HTML build uses
    # ``.html`` and notebook sources link ``.ipynb``, both of which resolve to
    # the ``.md`` page in the markdown tree.
    def _to_markdown_link(match: re.Match[str]) -> str:
        url, fragment = match.group(1), match.group(2) or ""
        if url.startswith(("http:", "https:", "#", "mailto:")):
            return f"({url}{fragment})"
        return f"({url.removesuffix('.html').removesuffix('.ipynb')}.md{fragment})"

    text = re.sub(
        r"\((?!http|https|#|mailto)([^()]*\.(?:html|ipynb))(#[^)]*)?\)",
        _to_markdown_link,
        text,
    )
    # Pandoc escapes literal double-asterisks (e.g. ``**kwds`` splat args);
    # unescape so the Python syntax reads literally in the markdown.
    text = text.replace(r"\*\*", "**")
    return text


def _deepen_relative_links(text: str) -> str:
    """Add one ``../`` to links pointing at shared Sphinx assets.

    Rendered Sphinx pages live at ``<root>/<section>/page.html`` while their
    markdown counterparts are emitted one level deeper under
    ``<root>/markdown/<section>/page.md``. Relative links that point up toward
    shared assets (e.g. ``../_images/``) therefore need an extra ``../``.
    Page-to-page links (``../../ref/...``) are mirrored inside the markdown
    tree and must stay unchanged.
    """

    def _replace(match: re.Match[str]) -> str:
        url = match.group(1)
        if url.startswith(("http:", "https:", "#", "mailto:")):
            return match.group(0)
        if re.search(r"\.\./(_images|_static|_sources)/", url):
            return match.group(0).replace(f"({url})", f"(../{url})", 1)
        return match.group(0)

    return re.sub(r"\[[^\]]*\]\((\.\.[^)]*)\)", _replace, text)


def _sanitize_markdown_output(path: Path, deepen_relative_links: bool = False) -> None:
    text = path.read_text(encoding="utf-8")
    text = _remove_html_wrappers(text)
    text = _strip_markdown_noise(text)
    if deepen_relative_links:
        text = _deepen_relative_links(text)
    path.write_text(_normalize_markdown(text), encoding="utf-8")


def _write_rendered_html(rendered_html_path: Path) -> Path | None:
    """Extract the page body from rendered Sphinx HTML into a temp HTML file."""
    html = rendered_html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    input_node = _select_html_body(soup)

    for tag in input_node.find_all(HTML_STRIP_TAGS):
        tag.decompose()

    # Collapse Sphinx signature markup so pandoc emits plain text instead of
    # wrapping each parameter in italic/bold markers (e.g. ``*x=None*``).
    for dt in input_node.select("dt.sig, dt.sig-object"):
        # Drop the "[source]" GitHub link and "#anchorname" headerlink spins.
        for tag in dt.find_all("a", class_="headerlink"):
            tag.decompose()
        source = dt.find("a", string=lambda t: t and "source" in t.lower() if t else False)
        if source is not None:
            source.decompose()
        for tag in dt.find_all(True):
            tag.unwrap()

    # Normalize :param: rows into "<name> : <type>" plain text.
    for dt in input_node.select("dl.field-list dt"):
        strong, classifier = dt.find("strong"), dt.find("span", class_="classifier")
        if strong is not None and classifier is not None:
            strong.insert_after(" : ")
            strong.unwrap()
            classifier.unwrap()

    temp = tempfile.NamedTemporaryFile(
        "w",
        suffix=".html",
        delete=False,
        encoding="utf-8",
    )
    try:
        temp.write(str(input_node))
        temp.close()
        return Path(temp.name)
    finally:
        if not temp.closed:
            temp.close()


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
        temp_path = _write_rendered_html(rendered_html_path)
        if temp_path is not None:
            input_path = temp_path
            input_format = "html"
    try:
        if not _run_command(
            _pandoc_command(input_format, output_path, input_path),
            str(rst_path),
        ):
            return False
    finally:
        if temp_path is not None:
            temp_path.unlink(missing_ok=True)

    _sanitize_markdown_output(output_path, deepen_relative_links=(input_format == "html"))
    return True


def build_markdown_docs(
    sources: Sequence[MarkdownSource],
    markdown_root: Path,
) -> list[Path]:
    """Copy markdown files and convert notebooks into the markdown tree."""

    for source in sources:
        if not source.output_dir.is_relative_to(markdown_root):
            raise ValueError(
                f"MarkdownSource.output_dir ({source.output_dir}) must be "
                f"located under markdown_root ({markdown_root}) so that "
                "generated paths can be expressed relative to it."
            )

    generated: list[Path] = []

    def _rendered_html_for(source: MarkdownSource, rel_path: Path) -> Path | None:
        if source.rendered_source_dir is None:
            return None
        return source.rendered_source_dir / rel_path.with_suffix(".html")

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
                rendered_html_path = _rendered_html_for(source, rel)
                if _convert_rst(path, md_destination, rendered_html_path):
                    md_rel = md_destination.relative_to(markdown_root)
                    generated.append(md_rel)
                    print(f"  Converted {md_rel}")
                continue

            if path.suffix == ".ipynb" and source.convert_notebooks:
                md_destination = destination.with_suffix(".md")
                rendered_html_path = _rendered_html_for(source, rel)
                if (
                    rendered_html_path is not None
                    and rendered_html_path.exists()
                    and _needs_sphinx_resolution(path)
                ):
                    if _convert_rst(path, md_destination, rendered_html_path):
                        md_rel = md_destination.relative_to(markdown_root)
                        generated.append(md_rel)
                        print(f"  Converted {md_rel}")
                elif _convert_notebook(path, destination.parent):
                    md_rel = destination.with_suffix(".md").relative_to(markdown_root)
                    md_path = destination.with_suffix(".md")
                    _sanitize_markdown_output(md_path)
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
            lines.append(f"- [{category.label_builder(md_file.relative_to(markdown_root))}]({markdown_base_url}/{rel_md})")

        index_file = category_dir / "index.md"
        index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        generated_indexes.append(index_file.relative_to(markdown_root))
        print(f"  Generated index: {index_file.relative_to(markdown_root)}")

    return generated_indexes


def _build_links(
    paths: Iterable[Path],
    markdown_base_url: str,
    label_builder: LabelBuilder,
    description_builder: Callable[[Path], str | None] | None = None,
) -> list[str]:
    links = []
    for path in sorted(paths):
        label = label_builder(path)
        link = f"- [{label}]({markdown_base_url}/{path.as_posix()})"
        if description_builder is not None:
            description = description_builder(path)
            if description:
                link += f": {description}"
        links.append(link)
    return links


def _matches_prefix(path: Path, prefix: Path) -> bool:
    return prefix in (Path(), Path(".")) or path.is_relative_to(prefix)


def _build_url_pattern_body(section: LlmsSection, section_paths: Sequence[Path]) -> list[str]:
    def _rel(path: Path) -> str:
        try:
            return path.relative_to(section.path_prefix).with_suffix("").as_posix()
        except ValueError:
            return path.stem

    rels = sorted(_rel(path) for path in section_paths)
    slash_parts = [Path(rel).parts for rel in rels]
    dot_parts = [rel.split(".") for rel in rels]

    if all(len(parts) == 2 for parts in slash_parts):
        body = [
            f"Page URL pattern: `{section.url_pattern}` where {{path}} = {{category}}/{{example}}"
        ]
        first_category, first_example = slash_parts[0]
        body.append(
            f"  e.g. `{section.url_pattern.format(path=f'{first_category}/{first_example}')}`"
        )
        for category, entries in groupby(slash_parts, key=lambda parts: parts[0]):
            body.append(f"  {category}: {', '.join(entry[1] for entry in entries)}")
        return body

    if all(len(parts) >= 3 for parts in dot_parts):
        body = [
            f"Page URL pattern: `{section.url_pattern}` where {{stem}} = {{module}}.{{method}}"
        ]
        first = dot_parts[0]
        first_stem = ".".join(first[:-1])
        body.append(f"  e.g. `{section.url_pattern.format(stem=f'{first_stem}.{first[-1]}')}`")
        key_fn = lambda parts: ".".join(parts[:-1])
        for stem, entries in groupby(dot_parts, key=key_fn):
            body.append(f"  {stem}: {', '.join(entry[-1] for entry in entries)}")
        return body

    pages = ", ".join(rels)
    return [
        f"Page URL pattern: `{section.url_pattern}`",
        f"  e.g. `{section.url_pattern.format(stem=rels[0], path=rels[0])}`",
        f"Available pages ({len(section_paths)}): {pages}",
    ]


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

    current_group: str | None = None
    for section in config.sections:
        section_paths = [path for path in generated_paths if _matches_prefix(path, section.path_prefix) and section.path_filter(path)]
        if not section_paths:
            continue

        if section.url_pattern is not None:
            body = _build_url_pattern_body(section, section_paths)
        else:
            body = _build_links(
                section_paths,
                config.markdown_base_url,
                section.label_builder,
                section.description_builder,
            )
            if section.note:
                body = body + ["", section.note]

        if section.group is not None:
            if section.group != current_group:
                lines.extend([f"## {section.group}", ""])
                if section.group_description:
                    lines.append(section.group_description)
                    lines.append("")
                current_group = section.group
            lines.extend([f"### {section.title}", f"> {section.description}", ""])
            lines.extend(body)
            lines.append("")
        else:
            lines.extend([f"## {section.title}", "", f"{section.description}", ""])
            lines.extend(body)
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
