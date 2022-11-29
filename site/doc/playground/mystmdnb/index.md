---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  name: python3
---

# Text-based Notebooks

This file is a [text-based notebook](https://myst-nb.readthedocs.io/en/latest/authoring/text-notebooks.html) written using MyST-Markdown and with an `.md` extension. Its header indicates MyST-NB that is is an "executable" file. Jupytext can be used to open this file as a notebook.

```
---
jupytext:
  formats: md:myst
  text_representation:
    extension: .md
    format_name: myst
kernelspec:
  display_name: Python 3
  name: python3
---
```

```{code-cell} ipython3
print('hello world')
```

```{toctree}
:titlesonly:
:hidden:
:maxdepth: 2

Intro <self>
holoviz
```
