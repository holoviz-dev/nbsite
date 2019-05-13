from setuptools import setup

setup_args = {}
install_requires = []
extras_require={}

setup_args.update(dict(
    name='holoviews',
    version="99.8.2",
    install_requires = install_requires,
    extras_require = extras_require,
    packages = ["holoviews",
                "holoviews.core",
                "holoviews.core.data",
                "holoviews.element",
                "holoviews.interface",
                "holoviews.ipython",
                "holoviews.util",
                "holoviews.operation",
                "holoviews.plotting",
                "holoviews.plotting.mpl",
                "holoviews.plotting.bokeh",
                "holoviews.plotting.plotly",
                "holoviews.plotting.widgets"]
))


if __name__=="__main__":
    setup(**setup_args)
