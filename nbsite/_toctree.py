"""Resolve the global toctree of the site once instead of for every page.

Themes like pydata-sphinx-theme render the navigation of the whole site on
every page with the ``toctree()`` template function, for which Sphinx copies
the table of contents of every document of the site again for every page.
When not collapsing, the entries do not depend on the page, only the
``current`` classes and relative links do. So the entries are resolved once,
and the rest of ``sphinx.environment.adapters.toctree._resolve_toctree`` is
done for every page with the same Sphinx functions.
"""

from docutils import nodes
from sphinx import addnodes
from sphinx.builders.html import StandaloneHTMLBuilder
from sphinx.environment.adapters import toctree as _toctree
from sphinx.util import url_re
from sphinx.util.matching import Matcher

# Sphinx < 7.2 resolves toctrees with the TocTree class instead
_SUPPORTED = all(
    hasattr(_toctree, name)
    for name in ("_entries_from_toctree", "_toctree_add_classes", "_toctree_copy")
)

_TOCTREE_KWARGS = {"includehidden", "maxdepth", "titles_only"}

_orig_get_local_toctree = StandaloneHTMLBuilder._get_local_toctree


def _resolve_entries(env, toctree, maxdepth, titles_only, includehidden, tags):
    """The start of ``_resolve_toctree``, without the ancestors of the page.

    The ancestors only decide whether the table of contents of a document is
    deep copied or copied and pruned, which gives the same entries when not
    collapsing, apart from ``only`` nodes (see ``_has_only_nodes``).
    """
    if toctree.get('hidden', False) and not includehidden:
        return None
    maxdepth = maxdepth or toctree.get('maxdepth', -1)
    if not titles_only and toctree.get('titlesonly', False):
        titles_only = True
    if not includehidden and toctree.get('includehidden', False):
        includehidden = True
    tocentries = _toctree._entries_from_toctree(
        env,
        True,
        titles_only,
        False,
        includehidden,
        tags,
        set(),
        Matcher(env.config.include_patterns),
        Matcher(env.config.exclude_patterns),
        toctree,
        [],
    )
    if not tocentries:
        return None
    newnode = addnodes.compact_paragraph('', '')
    if caption := toctree.attributes.get('caption'):
        caption_node = nodes.title(caption, '', *[nodes.Text(caption)])
        caption_node.line = toctree.line
        caption_node.source = toctree.source
        caption_node.rawsource = toctree['rawcaption']
        if hasattr(toctree, 'uid'):
            caption_node.uid = toctree.uid
            del toctree.uid
        newnode.append(caption_node)
    newnode.extend(tocentries)
    newnode['toctree'] = True
    return newnode, maxdepth


def _builder_cache(builder):
    return builder.__dict__.setdefault('_nbsite_toctree_cache', {})


def _has_only_nodes(builder):
    """``only`` nodes hide their references from the ``current`` classes
    when a table of contents is deep copied, so the entries would depend on
    the page."""
    cache = _builder_cache(builder)
    if 'has_only_nodes' not in cache:
        cache['has_only_nodes'] = any(
            next(iter(toc.findall(addnodes.only)), None) is not None
            for toc in builder.env.tocs.values()
        )
    return cache['has_only_nodes']


def _global_toctree(builder, docname, includehidden, maxdepth, titles_only):
    env, tags = builder.env, builder.tags
    cache = _builder_cache(builder)
    key = (includehidden, maxdepth, titles_only)
    if key not in cache:
        resolved = (
            _resolve_entries(env, toctree, maxdepth, titles_only, includehidden, tags)
            for toctree in env.master_doctree.findall(addnodes.toctree)
        )
        cache[key] = [entries for entries in resolved if entries is not None]

    toctrees = []
    for entries, toctree_maxdepth in cache[key]:
        newnode = entries.deepcopy()
        _toctree._toctree_add_classes(newnode, 1, docname)
        newnode = _toctree._toctree_copy(newnode, 1, toctree_maxdepth, False, tags)
        if isinstance(newnode[-1], nodes.Element) and len(newnode[-1]) == 0:
            continue
        for refnode in newnode.findall(nodes.reference):
            if url_re.match(refnode['refuri']) is None:
                rel_uri = builder.get_relative_uri(docname, refnode['refuri'])
                refnode['refuri'] = rel_uri + refnode['anchorname']
        toctrees.append(newnode)

    if not toctrees:
        return None
    result = toctrees[0]
    for toctree in toctrees[1:]:
        result.extend(toctree.children)
    return result


def _get_local_toctree(self, docname, collapse=True, **kwargs):
    if (
        collapse
        or not _SUPPORTED
        or not getattr(self.config, 'nbsite_cache_toctree', False)
        or not set(kwargs) <= _TOCTREE_KWARGS
        or _has_only_nodes(self)
    ):
        return _orig_get_local_toctree(self, docname, collapse, **kwargs)
    if 'includehidden' not in kwargs:
        kwargs['includehidden'] = False
    if kwargs.get('maxdepth') == '':
        kwargs.pop('maxdepth')
    toctree = _global_toctree(
        self,
        docname,
        includehidden=kwargs['includehidden'],
        maxdepth=int(kwargs.get('maxdepth', 0)),
        titles_only=kwargs.get('titles_only', False),
    )
    return self.render_partial(toctree)['fragment']


def patch_get_local_toctree():
    """Patch ``StandaloneHTMLBuilder._get_local_toctree``, idempotently."""
    StandaloneHTMLBuilder._get_local_toctree = _get_local_toctree


def unpatch_get_local_toctree():
    """Restore the original ``StandaloneHTMLBuilder._get_local_toctree``."""
    StandaloneHTMLBuilder._get_local_toctree = _orig_get_local_toctree
