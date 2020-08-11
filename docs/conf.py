# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
sys.path.insert(0, os.path.abspath('..'))

master_doc = 'index'

# -- Project information -----------------------------------------------------
import omnifig as fig


project = 'omnifig'

author = fig.__author__

copyright = '2020, {}'.format(author)

# The full version, including alpha/beta/rc tags
release = fig.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    'sphinx.ext.autodoc',
    'sphinx.ext.doctest',
    'sphinx.ext.todo',
    'sphinx.ext.coverage',
    'sphinx.ext.imgmath',
    'sphinx.ext.mathjax',
    'sphinx.ext.viewcode',
    'sphinx.ext.githubpages',
    'sphinx_autodoc_typehints',
    
    'sphinx.ext.intersphinx',  #
    # 'sphinx.ext.todo',  #
    # 'sphinx.ext.mathjax',  #
    'sphinx.ext.ifconfig',  #
    # 'sphinx.ext.viewcode',  #
    # 'sphinx.ext.githubpages',  #
    'sphinx.ext.graphviz',  #
    # 'sphinx.ext.autodoc',
    # 'sphinx.ext.doctest',
    
    'sphinx.ext.autosectionlabel',
]

autosectionlabel_prefix_document = True
autodoc_inherit_docstrings = False

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ['_build', 'Thumbs.db', '.DS_Store']

add_module_names = False

# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

import sphinx_rtd_theme

# logo
html_logo = '_static/img/logo_border.png' # should be wide

# logo
# html_favicon = '_static/img/favicon/favicon.ico'

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
html_theme = "sphinx_rtd_theme"
html_theme_path = [sphinx_rtd_theme.get_html_theme_path()]

# Theme options are theme-specific and customize the look and feel of a theme
# further.  For a list of options available for each theme, see the
# documentation.

html_theme_options = {
    'navigation_depth': 3,
    # 'logo_only': True,
}

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['_static']
html_style = 'css/gsm.css'

# -- Options for HTMLHelp output ------------------------------------------

# Output file base name for HTML help builder.
htmlhelp_basename = 'figDoc'


# -- Extension configuration -------------------------------------------------

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# intersphinx_mapping = {
#     'python': ('https://docs.python.org/3/', None),
#     'torch': ('http://pytorch.org/docs/master/', None),
#     'opt_einsum': ('https://optimized-einsum.readthedocs.io/en/stable/', None)
# }