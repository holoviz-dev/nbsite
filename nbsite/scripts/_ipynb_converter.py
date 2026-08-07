"""Lightweight Jupyter Notebook (.ipynb) to Markdown converter."""

from __future__ import annotations

import json

from pathlib import Path


def convert_notebook(notebook_path: Path) -> str:
    """Convert a Jupyter notebook file to Markdown.

    Parameters
    ----------
    notebook_path : Path
        Path to the ``.ipynb`` file.

    Returns
    -------
    str
        The notebook content as a Markdown string.

    Raises
    ------
    ValueError
        If the file cannot be decoded as a valid Jupyter notebook.
    """
    try:
        content = json.loads(notebook_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise ValueError(f"Cannot parse {notebook_path} as a Jupyter notebook: {exc}") from exc

    cells = content.get("cells")
    if not isinstance(cells, list):
        raise ValueError(f"{notebook_path} does not contain a 'cells' list")

    md_parts: list[str] = []
    title: str | None = None

    for cell in cells:
        cell_type = cell.get("cell_type", "")
        source_lines = cell.get("source", [])

        if cell_type == "markdown":
            md_parts.append("".join(source_lines))

            if title is None:
                for line in source_lines:
                    if line.startswith("# "):
                        title = line[2:].strip()
                        break

        elif cell_type == "code":
            source = "".join(source_lines)
            if source.strip():
                md_parts.append(f"```python\n{source}\n```")

        elif cell_type == "raw":
            source = "".join(source_lines)
            if source.strip():
                md_parts.append(f"```\n{source}\n```")

    md_text = "\n\n".join(md_parts)

    if title is None:
        metadata_title = content.get("metadata", {}).get("title")
        if metadata_title:
            md_text = f"# {metadata_title}\n\n{md_text}"

    return md_text
