"""
nb_interactivity_warning extension adds a warning box to pages built from
a Jupyter or MyST Markdown notebook, similarly to the warning added by
the NotebookDirective.

This extension depends on:
- nbsite/_shared_templates/nb-interactivity-warning.html
- nbsite/_shared_static/scroller.css (also needed for the NotebookDirective)
"""

from sphinx.application import Sphinx
from sphinx.util.logging import getLogger

from .. import __version__ as nbs_version

logger = getLogger(__name__)


def add_sidebar_content(
    app: Sphinx, pagename: str, templatename: str, context: dict, doctree
):
    """
    Adds custom content to the right sidebar if the page is a Jupyter Notebook.
    """
    print("XXX", pagename, context.get("page_source_suffix") )
    if context.get("page_source_suffix") == ".ipynb" or (
        context.get("page_source_suffix") == ".md"
        # There might be other ways to find this out, seems to work.
        and "kernelspec" in app.env.metadata[pagename]
    ):
        sidebar_items = context.get("theme_secondary_sidebar_items", [])
        if "nb-interactivity-warning" in sidebar_items:
            return
        # theme_secondary_sidebar_items can be a list or a comma-separated string.
        if isinstance(sidebar_items, str):
            if sidebar_items:
                sidebar_items = ", ".join([sidebar_items, "nb-interactivity-warning"])
            else:
                sidebar_items = "nb-interactibity-warning"
        else:
            sidebar_items.append("nb-interactivity-warning")
        context["theme_secondary_sidebar_items"] = sidebar_items
        print("YYY", context["theme_secondary_sidebar_items"])
        logger.debug(
            "Adding 'nb-interactivity-warning' item to the secondary sidebar: %s",
            pagename,
        )


def setup(app: Sphinx):
    # Event triggered when HTML pages are built
    app.connect("html-page-context", add_sidebar_content)
    return {
        "version": nbs_version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
