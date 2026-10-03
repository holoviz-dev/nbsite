## Sphinx extensions

`nbsite` ships some additional Sphinx extensions.

## `nb_interactivity_warning`

Enabling this extension will add an interactivity warning (similarly to the one added by the `NotebookDirective`) to pages built from Jupyter or MyST Markdown notebooks.

It is enabled by default and can be configured with:
- `nb_interactivity_warning_enable = False`, to disable it
- `nb_interactivity_warning_per_file = True` and adding the tag
  `nb-interactivity-warning` to the notebook metadata, to enable it only
  on specific pages


## `validate_versioned`

Adding this extension is helpful to support versioned sites:

- Checks html_baseurl is set
- Creates a sitemap.xml file in a subdirectory of the docs source
- Creates a robots.txt file in a subdirectory of the docs source

## `pyodide`

With `enable_pwa` (the default), the `pyodide` extension writes a service worker and a web app manifest to the root of the build so pages with Pyodide cells work offline once loaded. The worker answers requests from its cache first. Its cache is named after the project and `version`, and installing a new worker deletes the project's other caches.

That suits a site with a single build per origin. When several builds share an origin, as on a versioned site with `/en/docs/<version>/` directories, set these keys in `nbsite_pyodide_conf`:

```python
nbsite_pyodide_conf = {
    # Name caches after the worker's scope, so one version's worker does not delete another's caches.
    'pwa_scope_caches': True,
    # Revalidate same-origin requests instead of reusing the browser HTTP cache.
    'pwa_fetch_cache': 'no-cache',
    # Confine an installed app to its own build rather than the whole origin.
    'pwa_manifest_scope': './',
    # Change the cache name on every build, not only on version bumps, so re-publishing a version reaches returning visitors.
    'pwa_cache_version': f'{version}+{build_id}',
}
```

The defaults (`False`, `None`, `'/'` and the Sphinx `version`) keep the original behaviour.
