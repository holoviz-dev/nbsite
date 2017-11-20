============
IOAM builder
============

WIP!

Installation
============

0. Assumptions:

  * You have getting started guide notebooks in
    examples/getting_started
    
  * You have user guide notebooks in examples/user_guide
    
  * You have gallery notebooks in examples/gallery
  
1. Add ioam-builder as submodule of your project at `doc/builder`::

    git submodule add -b tmphvdocs git@github.com:ioam/ioam-builder doc/builder

2. TODO ``conda env create --file doc/builder/docenv.yml`` (TODO: conda package coming
   instead)

3. To get template pages to start from/if you don't already have rst to start from, ``cp doc/builder/tmplate/*.rst doc/`` and ``cp doc/builder/tmplate/*.html doc/``

4. If you don't already have sphinx Makefile, ``cp doc/builder/tmplate/Makefile doc/`` and edit PROJECT and MODULE in doc/Makefile

5. If you don't already have sphinx conf.py, ``cp doc/builder/tmplate/conf.py doc/`` and edit stuff in it.

6. Edit doc/index.rst toctree to match pages in conf.py

7. git add FAQ.rst Makefile about.rst conf.py index.rst latest_news.html
   
6. Install theme: ``cd doc/builder/ioam_theme && python setup.py install && cd ../../..``
   
7. TODO ``export PYTHONPATH=$PWD/doc``

8. ``cd doc``, then::

    TODO don't try this at home yet: make gallery
    TODO don't try this at home yet: make refmanual
    make ipynb-rst

9. Now ``cp doc/builder/tmplate/user_guide/index.rst user_guide`` and edit, or make your own
   Then commit to repo

10. Now ``cp doc/builder/tmplate/getting_started/index.rst getting_started`` and edit, or make your own
    Then commit to repo

11. grep for holoviews and project, replace as appropriate

9.    
    make html
    make fix-links

9. pushd _build/html && python -m http.server

3. grep for holoviews

3. grep for project
   
3. FAQ.rst
   getting_started/index.rst
   user_guide/index.rst
   index.rst
   about.rst
   latest_news.html
   Reference_Manual/index.rst

   
3. At this point you should be able to build site (see usage, below).

0. Add .travis gh pages chunk
   

Extras
------
   
1. Either edit these files or comment out references to them in conf.py

  * about.rst: 
  * latest_news.html: twitter account
  * Reference_Manual/index.rst
  * holoviews_theme/includes/ga.html: google analytics


Usage
=====

1. export PYTHONPATH=$PWD/doc
2. cd doc
3. make ipynb-rst (optional: commit result and skip step in future)
3. (optional) make gallery
4. (optional) make refmanual
5. make html
6. make fix-links
7. pushd _build/html && python -m http.server


Contents
========

Config
------

shared_conf.py
______________


Commands
--------

make clean
make ...


Code
----

fix_links.py
____________

something


gallery.py
__________

something


thumbnailer.py
______________


nbbuild.py
__________

something

nbpagebuild.py
______________

Generates rst containers for all notebooks in examples/


generate_modules.py
___________________

something


paramdoc.py
___________

The ioam-builder docextensions branch provides extensions for Sphinx
to document Parameterized classes and generate autodocs for the
modules and submodules in each project.
