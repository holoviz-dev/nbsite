from nbsite.shared_conf import *

NAME = 'nbsite'
DESCRIPTION = 'Build a sphinx-based website from notebooks.'

project = NAME
authors = 'HoloViz Developers'
copyright = '2018 ' + authors

import nbsite

version = release = base_version(nbsite.__version__)

html_theme = 'pydata_sphinx_theme'

extensions += [
    # Activate the cell copy button extension
    'sphinx_copybutton',
    # To make the pyodide directive available
    'nbsite.pyodide',
    # To build a gallery
    'nbsite.gallery',
    # To setup GoatCounter
    'nbsite.analytics',
    # To add an interactive warning on pages built from a notebook.
    'nbsite.nb_interactivity_warning',
    # Activate the docstring extension for Numpy: https://www.sphinx-doc.org/en/master/usage/extensions/napoleon.html
    'sphinx.ext.napoleon',
    # See https://github.com/ipython/ipython/issues/13845
    'IPython.sphinxext.ipython_console_highlighting'
]

# Configure sphinx.ext.napoleon
napoleon_numpy_docstring = True
napoleon_google_docstring = False

# Configure nbsite.gallery
nbsite_gallery_conf = {
    'github_org': 'holoviz',
    'github_project': 'nbsite',
    'galleries': {
        'playground/example_gallery': {
            'title': 'Gallery Title',
            'intro': 'This is an example intro.',
            'sections': [
                'section1',
                'section2',
            ]
        },
        'playground/gallery_backends': {
            'title': 'Gallery with backends',
            'intro': 'This is a gallery with "backends:',
            'backends': ['option1', 'option2'],
        },
    },
}

nbsite_analytics = {
    'goatcounter_holoviz': True,
}

# Configure the theme
html_theme_options.update({
    "github_url": "https://github.com/holoviz-dev/nbsite",
    "icon_links": [
        {
            "name": "Discourse",
            "url": "https://discourse.holoviz.org/",
            "icon": "fab fa-discourse",
        },
    ],
    "pygments_light_style": "material",
    "pygments_dark_style": "material",
    'secondary_sidebar_items': [
        "github-stars-button"
    ],
})

# Extra config for the theme
html_context.update({
    # Used to add binder links to the latest released tag.
    "last_release": f"v{release}",
    'github_user': 'holoviz',
    'github_repo': 'holoviews',
    "default_mode": "light"
})

# Static assets
html_static_path += ['_static']

html_logo = "_static/nbsite-logo.png"
html_favicon = "_static/favicon.ico"

# Add custom templates
templates_path += [
    '_templates'
]

# Add custom css
html_css_files += [
    # Custom to this site
    'css/custom.css',
]

# Override the Sphinx default title that appends `documentation`
html_title = f'{project} v{version}'

nb_interactivity_warning_per_file = True
