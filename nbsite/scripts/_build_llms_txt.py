"""Reusable helpers for building markdown docs and llms.txt.

Individual repos provide an `llms_config.py` module to customize source
roots, section definitions, index pages, and label formatting.
"""

from __future__ import annotations

import shutil
import subprocess
import sys

from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable, Iterable, Sequence

LabelBuilder = Callable[[Path], str]
PathPredicate = Callable[[Path], bool]


def default_label(path: Path) -> str:
    return path.stem.replace("_", " ")


def index_label(path: Path) -> str:
    if path.stem == "index":
        return path.parent.name.replace("_", " ") if path.parent != Path(".") else "home"
    return default_label(path)


def _is_included(rel_path: Path, include_suffixes: Sequence[str], exclude_dir_names: Sequence[str]) -> bool:
    if any(part in exclude_dir_names for part in rel_path.parts):
        return False
    return rel_path.suffix in include_suffixes


@dataclass(frozen=True)
class MarkdownSource:
    """A source tree to mirror into the markdown output tree."""

    source_dir: Path
    output_dir: Path
    include_suffixes: tuple[str, ...] = (".md", ".ipynb")
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


def build_markdown_docs(sources: Sequence[MarkdownSource], markdown_root: Path) -> list[Path]:
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

            if path.suffix == ".ipynb" and source.convert_notebooks:
                if _convert_notebook(path, destination.parent):
                    generated.append(destination.with_suffix(".md").relative_to(markdown_root))
                    print(f"  Converted {destination.with_suffix('.md').relative_to(markdown_root)}")

    return generated


def generate_index_pages(markdown_root: Path, categories: Sequence[IndexCategory], markdown_base_url: str) -> list[Path]:
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
            lines.append(f"- [{category.label_builder(md_file)}]({markdown_base_url}/{md_file.relative_to(markdown_root).as_posix()})")

        index_file = category_dir / "index.md"
        index_file.write_text("\n".join(lines) + "\n", encoding="utf-8")
        generated_indexes.append(index_file.relative_to(markdown_root))
        print(f"  Generated index: {index_file.relative_to(markdown_root)}")

    return generated_indexes


def _build_links(paths: Iterable[Path], markdown_base_url: str, label_builder: LabelBuilder) -> list[str]:
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
        f"All documentation is available as markdown files under {config.markdown_base_url}/.",
        "",
    ]

    for section in config.sections:
        section_paths = [path for path in generated_paths if _matches_prefix(path, section.path_prefix) and section.path_filter(path)]
        if not section_paths:
            continue

        lines.extend([f"## {section.title}", "", f"{section.description}", ""])
        lines.extend(_build_links(section_paths, config.markdown_base_url, section.label_builder))
        lines.append("")

    if generated_indexes:
        lines.extend(["## Reference Indexes", ""])
        lines.extend(_build_links(generated_indexes, config.markdown_base_url, index_label))
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
    generated_indexes = generate_index_pages(config.markdown_root, config.index_categories, config.markdown_base_url)
    print("Generating llms.txt...")
    return generate_llms_txt(config, generated_paths, generated_indexes)
