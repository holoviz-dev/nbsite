"""Reusable helpers for building markdown docs and llms.txt.

Individual repos provide an ``llms_config.py`` module to customize source
roots, section definitions, index pages, and label formatting.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import tempfile

from dataclasses import dataclass, field
from itertools import groupby
from pathlib import Path, PurePosixPath
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

_STRIP_TAGS_RE = re.compile(
    r"</?(?:" + "|".join(re.escape(t) for t in MARKDOWN_STRIP_TAGS) + r")(?:\s[^>]*)?>",
    re.I,
)

# Meta-refresh used by Sphinx/MyST stub pages that only redirect to an index
# fragment (e.g. Panel how-to section landings). Attribute order varies.
_META_REFRESH_RE = re.compile(
    r"http-equiv\s*=\s*[\"']refresh[\"'][^>]*\bcontent\s*=\s*[\"'][^\"']*url=\s*([^\"'\s#>]+)(?:#([^\"'\s]+))?"
    r"|\bcontent\s*=\s*[\"'][^\"']*url=\s*([^\"'\s#>]+)(?:#([^\"'\s]+))?[\"'][^>]*http-equiv\s*=\s*[\"']refresh[\"']",
    re.I | re.S,
)


_NUM_PREFIX_RE = re.compile(r"^\d+[-_ ]")


def _strip_numeric_prefix(rel: Path) -> Path:
    """Strip a leading ``<digits>-``/``_``/`` `` prefix from each path part.

    Mirrors nbsite's ``cmd._path_and_order`` behavior for rst generation, so
    e.g. ``1-Introduction.ipynb`` becomes ``Introduction.md`` in the markdown
    output tree instead of keeping the ordering prefix in the visible name.
    """
    return Path(*(_NUM_PREFIX_RE.sub("", part) for part in rel.parts))


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
    """Yield source files, preferring .ipynb over .rst when both exist."""
    # Collect all included paths grouped by their directory + stem (not just
    # stem) so that e.g. how_to/callbacks/index.md and how_to/state/index.md
    # are treated as distinct pages instead of colliding on "index".
    stem_to_paths: dict[Path, list[Path]] = {}
    for path in sorted(source.source_dir.rglob("*")):
        if not path.is_file():
            continue
        rel_path = path.relative_to(source.source_dir)
        if _is_included(rel_path, source.include_suffixes, source.exclude_dir_names, source.exclude_files):
            key = rel_path.with_suffix("")
            stem_to_paths.setdefault(key, []).append(path)

    # For each stem, emit the preferred file: .ipynb beats .rst; otherwise
    # preserve the sorted order.
    for siblings in stem_to_paths.values():
        preferred = (
            next((p for p in siblings if p.suffix == ".ipynb"), None)
            or next((p for p in siblings if p.suffix != ".rst"), None)
            or siblings[0]
        )
        yield preferred


def _run_command(command: list[str], warning_context: str) -> bool:
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode == 0:
        return True
    print(f"  Warning: failed to convert {warning_context}: {result.stderr.strip()}")
    return False


def _convert_notebook(source_path: Path) -> str | None:
    """Convert a Jupyter notebook to Markdown."""
    try:
        from ._ipynb_converter import convert_notebook

        return convert_notebook(source_path)
    except Exception as exc:
        print(f"  Warning: failed to convert {source_path}: {exc}")
        return None


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


def _extract_meta_refresh(text: str) -> tuple[str, str | None] | None:
    """Return ``(url, fragment)`` from a meta-refresh redirect, if present."""
    match = _META_REFRESH_RE.search(text)
    if match is None:
        return None
    url = match.group(1) or match.group(3)
    fragment = match.group(2) or match.group(4)
    if not url:
        return None
    return url, fragment


def _prepare_html_node(node) -> None:
    """Strip chrome from a BeautifulSoup node before pandoc conversion."""
    for tag in node.find_all(HTML_STRIP_TAGS):
        tag.decompose()

    for dt in node.select("dt.sig, dt.sig-object"):
        for tag in dt.find_all("a", class_="headerlink"):
            tag.decompose()
        source = dt.find("a", string=lambda t: t and "source" in t.lower() if t else False)
        if source is not None:
            source.decompose()
        for tag in dt.find_all(True):
            tag.unwrap()

    for dt in node.select("dl.field-list dt"):
        strong, classifier = dt.find("strong"), dt.find("span", class_="classifier")
        if strong is not None and classifier is not None:
            strong.insert_after(" : ")
            strong.unwrap()
            classifier.unwrap()

    # Header permalinks and empty anchors add noise in LLM markdown.
    for tag in node.find_all("a", class_="headerlink"):
        tag.decompose()


def _html_node_to_temp_file(node) -> Path:
    """Write a prepared HTML node to a temp file for pandoc."""
    _prepare_html_node(node)
    temp = tempfile.NamedTemporaryFile(
        "w",
        suffix=".html",
        delete=False,
        encoding="utf-8",
    )
    temp.write(str(node))
    temp.close()
    return Path(temp.name)


def _convert_html_to_markdown(
    html_path: Path,
    output_path: Path,
    *,
    fragment: str | None = None,
    warning_context: str | None = None,
) -> bool:
    """Convert rendered HTML (or one ``id=fragment`` section) to markdown."""
    html = html_path.read_text(encoding="utf-8")
    soup = BeautifulSoup(html, "html.parser")
    if fragment:
        node = soup.find(id=fragment)
        if node is None:
            print(
                f"  Warning: redirect target #{fragment} not found in {html_path}"
            )
            return False
    else:
        node = _select_html_body(soup)

    temp_path = _html_node_to_temp_file(node)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    try:
        if not _run_command(
            _pandoc_command("html", output_path, temp_path),
            warning_context or str(html_path),
        ):
            return False
    finally:
        temp_path.unlink(missing_ok=True)

    _sanitize_markdown_output(output_path, deepen_relative_links=True)
    return True


def _try_expand_redirect_markdown(
    source_path: Path,
    output_path: Path,
    rendered_html_path: Path | None,
) -> bool:
    """Expand a meta-refresh stub page into the redirected section's content.

    Panel how-to landings are thin MyST pages that only meta-refresh to
    ``index.html#section``. Copying them yields nearly empty markdown. When
    rendered HTML is available, pull the target section instead.

    Without rendered HTML there is nowhere to resolve the redirect target
    from, so this is a no-op rather than emitting a spurious warning for
    every stub page in projects that don't set ``rendered_source_dir``.
    """
    if rendered_html_path is None or not rendered_html_path.exists():
        return False

    text = source_path.read_text(encoding="utf-8")
    target = _extract_meta_refresh(text) or _extract_meta_refresh(
        rendered_html_path.read_text(encoding="utf-8")
    )
    if target is None:
        return False

    url, fragment = target
    if url.startswith(("http:", "https:", "#", "mailto:")):
        return False

    target_html = (rendered_html_path.parent / url).resolve()
    if not target_html.is_file():
        print(f"  Warning: redirect target missing for {source_path}: {target_html}")
        return False

    return _convert_html_to_markdown(
        target_html,
        output_path,
        fragment=fragment,
        warning_context=str(source_path),
    )


def _remove_html_wrappers(text: str) -> str:
    text = re.sub(
        r"<span\b[^>]*title=\"Extension loaded\.[^\"]*\"[^>]*>\u2139</span>",
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
    text = _STRIP_TAGS_RE.sub("", text)
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
    """Remove Sphinx/MyST/HTML-conversion artifacts that carry no value for LLMs."""
    # Remove {eval-rst} code blocks
    text = re.sub(r"```\{eval-rst\}\n.*?\n```", "", text, flags=re.S)

    # MyST pyodide fences are executable docs chrome; keep the code as plain python.
    # Handles `{pyodide}`, the doubled-brace `{{pyodide}`, and any backtick
    # count (3+), so fences nested with 4 backticks are normalized too.
    text = re.sub(r"^(`{3,})\{\{?pyodide\}?\s*$", r"\1python", text, flags=re.M)

    # Remove MySTMarkdown targets like (option-name)=
    text = re.sub(r"^\([a-zA-Z_-]+\)=$", "", text, flags=re.M)

    # Remove :::{directive} blocks (including content)
    text = re.sub(r"^:::\{[^}]+\}\n.*?\n:::$", "", text, flags=re.M | re.S)

    # Remove single-line :::{directive} content
    text = re.sub(r"^:::\{[^}]+\}.*$", "", text, flags=re.M)

    # Clean up cross-reference syntax: [`name`](target) -> name
    text = re.sub(r"\[`([^`]+)`\]\([^)]*\)", r"`\1`", text)

    # Clean up [text](target) cross-references that look like internal refs
    text = re.sub(r"\[([^\]]+)\]\([a-zA-Z_-]+\)", r"`\1`", text)

    text = re.sub(r"\s*\[#\]\(#[^)]*\)", "", text)
    text = re.sub(r"\[source\]\([^)]*\)", "", text)

    # Remove Jupyterlite / GitHub download banners (optionally followed by ---).
    text = re.sub(
        r"^\s*\[Open this notebook in Jupyterlite\]\([^)]*\)"
        r"(?:\s*\|\s*\[Download this notebook from GitHub[^\]]*\]\([^)]*\))?"
        r"\s*(?:\n+\s*---\s*)?\n?",
        "",
        text,
        flags=re.M | re.I,
    )

    # Remove the Jupyter-notebook banner (with or without the "On this page" preamble)
    # and the trailing "Edit on GitHub / Show Source" links that always follow it.
    text = re.sub(
        r"\n*(?:This web page was generated from a Jupyter notebook and not all\s*\n?"
        r"interactivity will work on this website\.\s*\n*On this page\s*\n*)?"
        r"\[\s*Edit on\s*\n?GitHub\]\([^)]*\)\s*\n*\[\s*Show\s*\n?Source\]\([^)]*\)\n*",
        "",
        text,
        flags=re.S,
    )

    def _to_markdown_link(match: re.Match[str]) -> str:
        url, fragment = match.group(1), match.group(2) or ""
        if url.startswith(("http:", "https:", "#", "mailto:")):
            return f"({url}{fragment})"
        stem = url.removesuffix('.html').removesuffix('.ipynb')
        stem = _strip_numeric_prefix(PurePosixPath(stem)).as_posix()
        return f"({stem}.md{fragment})"

    text = re.sub(
        r"\((?!http|https|#|mailto)([^()]*\.(?:html|ipynb))(#[^)]*)?\)",
        _to_markdown_link,
        text,
    )
    text = text.replace(r"\*\*", "**")

    # Remove multiple blank lines left behind
    text = re.sub(r"\n{3,}", "\n\n", text)

    return text


def _deepen_relative_links(text: str) -> str:
    """Add one ``../`` to links pointing at shared Sphinx assets."""

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


def _convert_rst(
    rst_path: Path,
    output_path: Path,
    rendered_html_path: Path | None = None,
) -> bool:
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if rendered_html_path is not None and rendered_html_path.exists():
        # Prefer the Sphinx-rendered page so directives/cards expand usefully.
        return _convert_html_to_markdown(
            rendered_html_path,
            output_path,
            warning_context=str(rst_path),
        )

    if not _run_command(
        _pandoc_command("rst", output_path, rst_path),
        str(rst_path),
    ):
        return False
    _sanitize_markdown_output(output_path)
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
            destination = source.output_dir / _strip_numeric_prefix(rel)

            if path.suffix == ".md" and source.copy_markdown:
                destination.parent.mkdir(parents=True, exist_ok=True)
                rendered_html_path = _rendered_html_for(source, rel)
                # Expand meta-refresh stubs (e.g. how-to section landings that
                # only point at index.html#section) into real section content.
                if _try_expand_redirect_markdown(path, destination, rendered_html_path):
                    md_rel = destination.relative_to(markdown_root)
                    generated.append(md_rel)
                    print(f"  Expanded redirect {md_rel}")
                    continue
                shutil.copy2(path, destination)
                # Always sanitize copied markdown so MyST chrome (pyodide
                # fences, Jupyterlite banners, etc.) is stripped consistently.
                _sanitize_markdown_output(destination)
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
                content = _convert_notebook(path)
                if content is not None:
                    md_destination.parent.mkdir(parents=True, exist_ok=True)
                    md_destination.write_text(content, encoding="utf-8")
                    md_rel = md_destination.relative_to(markdown_root)
                    _sanitize_markdown_output(md_destination)
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
            category.description,
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
    """Build a compact URL-pattern inventory for an llms.txt section.

    Instead of listing every page as a separate markdown link, this renders
    a single URL pattern plus a grouped inventory of path components.

    Path structure is detected once, then one of these modes is chosen:

    - **dotted_api**: all stems look like ``pkg.mod.method`` (3+ dot parts)
    - **category_example**: all paths are exactly ``category/example``
    - **mixed**: mix of standalone names and ``category/example``
    - **nested**: any path deeper than ``category/example``
    - **fallback**: flat list of every page (single-component or unknown shape)
    """

    def _rel(path: Path) -> str:
        """Relative stem under the section prefix, used as the pattern fill-in."""
        try:
            return path.relative_to(section.path_prefix).with_suffix("").as_posix()
        except ValueError:
            return path.stem

    rels = sorted(_rel(p) for p in section_paths)
    if not rels:
        return []

    # Two views of the same stems:
    # - slash_parts: directory-style hierarchy (foo/bar/baz) e.g explanation/api/callbacks
    # - dot_parts: dotted API names (pkg.mod.method) e.g hvplot.hvPlot.box
    slash_parts = [tuple(Path(r).parts) for r in rels]
    dot_parts = [tuple(r.split(".")) for r in rels]
    depths = [len(p) for p in slash_parts]
    min_depth, max_depth = min(depths), max(depths)

    # Prefer dotted API when every stem is clearly module-like. Checked first
    # so paths such as ``pkg.mod.fn`` are not treated as flat single segments.
    if all(len(d) >= 3 for d in dot_parts):
        return _pattern_dotted_api(section.url_pattern, rels, dot_parts)

    # Exact two-level tree: gallery-style category/example pages.
    if min_depth == 2 and max_depth == 2:
        return _pattern_slash_tree(
            section.url_pattern,
            where="{path} = {category}/{example}",
            rels=rels,
            slash_parts=slash_parts,
            nested_only=False,
        )

    # Standalone pages plus optional category/example children.
    if min_depth == 1 and max_depth == 2:
        return _pattern_slash_tree(
            section.url_pattern,
            where="{path} = {example} or {category}/{example}",
            rels=rels,
            slash_parts=slash_parts,
            nested_only=True,
        )

    # Deeper trees: keep first segment as category, join the rest with '/'.
    if max_depth > 2:
        return _pattern_slash_tree(
            section.url_pattern,
            where="{path} = {example} or {category}/{...}/{example}",
            rels=rels,
            slash_parts=slash_parts,
            nested_only=True,
        )

    # Single-component paths (or anything else): list them all.
    return _pattern_fallback(section.url_pattern, rels)


def _pattern_header(url_pattern: str, where: str, example: str) -> list[str]:
    """Shared pattern line + concrete example URL.

    ``where`` is concatenated (not interpolated) so brace placeholders such as
    ``{path}`` survive into the output instead of being treated as f-string fields.
    Both ``path`` and ``stem`` are passed to ``format`` so either placeholder works.
    """
    return [
        f"Page URL pattern: `{url_pattern}` where " + where,
        f"  e.g. `{url_pattern.format(path=example, stem=example)}`",
    ]


def _group_by_first(parts_list: Sequence[tuple[str, ...]]) -> list[str]:
    """Group paths by their first segment; join the remainder with ``/``."""
    lines: list[str] = []
    # Input must already be sorted so groupby sees contiguous keys.
    for category, entries in groupby(parts_list, key=lambda p: p[0]):
        children = ("/".join(entry[1:]) for entry in entries)
        lines.append(f"  {category}: {', '.join(children)}")
    return lines


def _pattern_dotted_api(
    url_pattern: str,
    rels: Sequence[str],
    dot_parts: Sequence[tuple[str, ...]],
) -> list[str]:
    """Group dotted API stems as ``module...: method, method``."""
    body = _pattern_header(url_pattern, "{stem} = {module}.{method}", rels[0])
    for stem, entries in groupby(dot_parts, key=lambda d: ".".join(d[:-1])):
        body.append(f"  {stem}: {', '.join(e[-1] for e in entries)}")
    return body


def _pattern_slash_tree(
    url_pattern: str,
    where: str,
    rels: Sequence[str],
    slash_parts: Sequence[tuple[str, ...]],
    *,
    nested_only: bool,
) -> list[str]:
    """Render slash-hierarchy inventories, optionally with a standalone row.

    When ``nested_only`` is True, single-segment paths are listed under
    ``standalone:`` (not a URL category — just pages with no subdirectory)
    and only multi-segment paths are grouped by category. When False, every
    path is assumed multi-segment and grouped directly.
    """
    body = _pattern_header(url_pattern, where, rels[0])
    if nested_only:
        # Label deliberately avoids looking like a path category name.
        standalone = [r for r, p in zip(rels, slash_parts) if len(p) == 1]
        if standalone:
            body.append(f"  standalone: {', '.join(standalone)}")
        to_group = [p for p in slash_parts if len(p) >= 2]
    else:
        to_group = list(slash_parts)
    body.extend(_group_by_first(to_group))
    return body


def _pattern_fallback(url_pattern: str, rels: Sequence[str]) -> list[str]:
    """Last resort: pattern line plus a full comma-separated page list."""
    return [
        f"Page URL pattern: `{url_pattern}`",
        f"  e.g. `{url_pattern.format(stem=rels[0], path=rels[0])}`",
        f"Available pages ({len(rels)}): {', '.join(rels)}",
    ]


def _dedup_paths(paths: Iterable[Path], root: Path) -> list[Path]:
    """Return *paths* with duplicates removed, keyed by stem-relative posix string."""
    seen: set[str] = set()
    result: list[Path] = []
    for path in paths:
        try:
            key = path.relative_to(root).with_suffix("").as_posix()
        except ValueError:
            key = path.with_suffix("").as_posix()
        if key not in seen:
            seen.add(key)
            result.append(path)
    return result


def _render_section(
    section: LlmsSection,
    section_paths: Sequence[Path],
    markdown_base_url: str,
) -> list[str]:
    """Return the lines that represent one section's body in llms.txt."""
    if section.url_pattern is not None:
        body = _build_url_pattern_body(section, section_paths)
    else:
        body = _build_links(
            section_paths,
            markdown_base_url,
            section.label_builder,
            section.description_builder,
        )
        if section.note:
            body = body + ["", section.note]
    return body


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
        f"All documentation is available as markdown files under {config.markdown_base_url}/.",
        "",
    ]

    current_group: str | None = None
    for section in config.sections:
        candidates = [
            path for path in generated_paths
            if _matches_prefix(path, section.path_prefix) and section.path_filter(path)
        ]
        section_paths = _dedup_paths(candidates, config.markdown_root)
        if not section_paths:
            continue

        body = _render_section(section, section_paths, config.markdown_base_url)

        if section.group is not None:
            if section.group != current_group:
                lines.extend([f"## {section.group}", ""])
                if section.group_description:
                    lines.extend([section.group_description, ""])
                current_group = section.group
            lines.extend([f"### {section.title}", f"> {section.description}", ""])
        else:
            lines.extend([f"## {section.title}", "", section.description, ""])

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
