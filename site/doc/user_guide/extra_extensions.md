## Sphinx extensions

`nbsite` ships some additional Sphinx extensions.

## `nb_interactivity_warning`

Enabling this extension will add an interactivity warning (similarly to the one added by the `NotebookDirective`) to pages built from Jupyter or MyST Markdown notebooks.

It is enabled by default and can be configured with:
- `nb_interactivity_warning_enable = False`, to disable it
- `nb_interactivity_warning_per_file = True` and adding the tag
  `nb-interactivity-warning` to the notebook metadata, to enable it only
  on specific pages
