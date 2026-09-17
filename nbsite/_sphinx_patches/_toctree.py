"""Resolve the global toctree of the site once instead of for every page.

Themes like pydata-sphinx-theme render the navigation of the whole site on
every page with the ``toctree()`` template function, for which Sphinx copies
the table of contents of every document of the site again for every page.
When not collapsing, the result only depends on the page through the
``current`` classes and the relative links, so the toctree is resolved once
and those are applied to it, and undone again, for every page.
"""

from collections import Counter
from contextlib import contextmanager

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


def _mark_current(node, docname, marked):
    """The ``current`` part of ``_toctree_add_classes``, recording what it marks."""
    for subnode in node.children:
        if isinstance(subnode, (addnodes.compact_paragraph, nodes.list_item, nodes.bullet_list)):
            _mark_current(subnode, docname, marked)
        elif isinstance(subnode, nodes.reference):
            if subnode['refuri'] == docname:
                if not subnode['anchorname']:
                    branchnode = subnode
                    while branchnode:
                        branchnode['classes'].append('current')
                        marked['classes'].append(branchnode)
                        branchnode = branchnode.parent
                if subnode.parent.parent.get('iscurrent'):
                    return
                while subnode:
                    subnode['iscurrent'] = True
                    marked['iscurrent'].append(subnode)
                    subnode = subnode.parent


@contextmanager
def _page_toctree(builder, cached, docname):
    """Apply the ``current`` classes and relative links of a page to the toctree."""
    marked = {'classes': [], 'iscurrent': []}
    _mark_current(cached['tree'], docname, marked)
    for refnode, refuri, anchorname in cached['references']:
        refnode['refuri'] = builder.get_relative_uri(docname, refuri) + anchorname
    try:
        yield cached['tree']
    finally:
        # A node is marked again for every reference of the page in the toctree
        for node in marked['classes']:
            if 'current' in node['classes']:
                node['classes'].remove('current')
        for node in marked['iscurrent']:
            node.attributes.pop('iscurrent', None)
        for refnode, refuri, _anchorname in cached['references']:
            refnode['refuri'] = refuri


def _build_cache(builder, includehidden, maxdepth, titles_only):
    env, tags = builder.env, builder.tags
    resolved = [
        entries
        for toctree in env.master_doctree.findall(addnodes.toctree)
        if (entries := _resolve_entries(env, toctree, maxdepth, titles_only, includehidden, tags))
        is not None
    ]
    cache = {'entries': resolved, 'tree': None, 'references': [], 'deeper_than_maxdepth': set()}
    if len(resolved) != 1:
        # Sphinx merges the toctrees of the site by moving their children together
        return cache

    entries, toctree_maxdepth = resolved[0]
    tree = entries.deepcopy()
    _toctree._toctree_add_classes(tree, 1, '')
    tree = _toctree._toctree_copy(tree, 1, toctree_maxdepth, False, tags)
    if isinstance(tree[-1], nodes.Element) and len(tree[-1]) == 0:  # No titles found
        return cache

    references = [
        (refnode, refnode['refuri'], refnode['anchorname'])
        for refnode in tree.findall(nodes.reference)
        if url_re.match(refnode['refuri']) is None
    ]
    # Pages pruned from the toctree are not marked as current in it, while
    # Sphinx marks them before pruning and keeps the classes of their parents
    in_tree = Counter(refuri for _refnode, refuri, _anchorname in references)
    in_entries = Counter(
        refnode['refuri']
        for refnode in entries.findall(nodes.reference)
        if url_re.match(refnode['refuri']) is None
    )
    # A page listed more than once can be pruned from only some of the places
    deeper = set(in_entries - in_tree)

    cache.update(tree=tree, references=references, deeper_than_maxdepth=deeper)
    return cache


def _resolved_for_page(builder, cached, docname):
    """Resolve the toctree for a page, as ``_resolve_toctree`` does."""
    tags = builder.tags
    toctrees = []
    for entries, toctree_maxdepth in cached['entries']:
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


def _builder_cache(builder):
    return builder.__dict__.setdefault('_nbsite_toctree_cache', {})


def _has_only_nodes(builder):
    """``only`` nodes hide their references from the ``current`` classes when a
    table of contents is deep copied, so the entries would depend on the page."""
    cache = _builder_cache(builder)
    if 'has_only_nodes' not in cache:
        cache['has_only_nodes'] = any(
            next(iter(toc.findall(addnodes.only)), None) is not None
            for toc in builder.env.tocs.values()
        )
    return cache['has_only_nodes']


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

    cache = _builder_cache(self)
    key = (kwargs['includehidden'], int(kwargs.get('maxdepth', 0)), kwargs.get('titles_only', False))
    if key not in cache:
        cache[key] = _build_cache(self, *key)
    cached = cache[key]

    if cached['tree'] is not None and docname not in cached['deeper_than_maxdepth']:
        with _page_toctree(self, cached, docname) as toctree:
            return self.render_partial(toctree)['fragment']
    return self.render_partial(_resolved_for_page(self, cached, docname))['fragment']
