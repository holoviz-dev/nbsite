"""
nb_interactivity_warning extension adds a warning box to pages built from
a Jupyter or MyST Markdown notebook, similarly to the warning added by
the NotebookDirective.

This extension depends on:
- nbsite/_shared_static/scroller.css (also needed for the NotebookDirective)
"""

from sphinx.application import Sphinx
from sphinx.util.logging import getLogger

from .. import __version__ as nbs_version

logger = getLogger(__name__)


HTML_INTERACTIVITY_WARNING = """
<div id="scroller-right">
    This web page was generated from a Jupyter notebook and not all
    interactivity will work on this website.
</div>
"""


def add_interactivity_warning_to_body(
    app: Sphinx, pagename: str, templatename: str, context: dict, doctree
):
    """
    Adds custom content to context body if the page is a Jupyter Notebook.
    """
    if context.get("page_source_suffix") == ".ipynb" or (
        context.get("page_source_suffix") == ".md"
        # There might be other ways to find this out, seems to work.
        and "kernelspec" in app.env.metadata[pagename]
    ):
        if HTML_INTERACTIVITY_WARNING not in context.get('body', ''):
            context['body'] += HTML_INTERACTIVITY_WARNING
            logger.debug(
                "Adding Notebook interactivity warning to page body as HTML: %s",
                pagename,
            )

def setup(app: Sphinx):
    # Event triggered when HTML pages are built
    app.connect("html-page-context", add_interactivity_warning_to_body)
    return {
        "version": nbs_version,
        "parallel_read_safe": True,
        "parallel_write_safe": True,
    }
