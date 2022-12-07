# Embed notebook with MyST-NB

```{warning}
This needs the latest MyST-NB
```

This is a MyST Markdown file that uses the *eval-rst* directive
to wrap an *include* directive, to embed a Jupyter Notebook processed
with MyST-NB

```{eval-rst}
.. include:: holoviz.ipynb
   :parser: myst_nb.docutils_
```
