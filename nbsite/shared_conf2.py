def hack(project,ioam_module,authors,description,html_static_path=None):

    exclude_patterns = ['_build', 'builder']
    html_title = project
    if html_static_path is None:
        html_static_path = []
    html_static_path += ['builder/_shared_static']
    htmlhelp_basename = ioam_module+'doc'
    latex_documents = [
      ('index', ioam_module+'.tex', project+u' Documentation', authors, 'manual'),
    ]
    man_pages = [
        ('index', ioam_module, project+u' Documentation', [authors], 1)
    ]
    texinfo_documents = [
      ('index', project, project+u' Documentation', authors, project, description,
       'Miscellaneous'),
    ]
    intersphinx_mapping = {'http://docs.python.org/': None,
                           'http://ipython.org/ipython-doc/2/': None,
                           'http://ioam.github.io/param/': None}

    from builder.paramdoc import param_formatter
    from builder import nbbuild


    def setup(app):
        app.connect('autodoc-process-docstring', param_formatter)
        try:
            import runipy # noqa (Warning import)
            nbbuild.setup(app)
        except:
            print('RunIPy could not be imported; pages including the '
                  'Notebook directive will not build correctly')

    return setup, intersphinx_mapping, texinfo_documents, man_pages, latex_documents, htmlhelp_basename, html_static_path, html_title, exclude_patterns
