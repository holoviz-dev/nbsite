# NBSite site

This site is mostly used to:

- have a playground for experimenting with NBSite
- provide good documentation practices

Building this site should be really fast, around a minute or less.

## Build the site

The commands are to be executed from this folder.

Install the dependencies with pip:

```
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

A simple task has been implemented to build the site:

```
doit all_build
```

To remove the artefacts run:

```
doit clean --clean-dep all_build
```

To try out the `pyodide` directive the built website has to be served.

```
cd builtdocs
python -m http.server 8000
```

Then in the web browser to go http://localhost:8000 .
