# -*- coding: utf-8 -*-
#

import sys, os, pathlib

###########################
# adding the isensus code #
###########################

root_source_folder = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(root_source_folder))


#######################
# project information #
#######################

from omnifig import __version__, __author__

project = 'omnifig'
author = __author__
copyright = '2023, {}'.format(author)


###################
# project version #
###################

version = "v{}".format(__version__)


##################
# sphinx modules #
##################

extensions = [
    "sphinx.ext.autodoc",
    'sphinx.ext.autosummary',
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    'sphinx.ext.githubpages',
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    'sphinx_autodoc_typehints',
    "myst_parser",
    # 'sphinx.ext.autosectionlabel',
    'sphinx_rtd_dark_mode',
]
templates_path = []
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
exclude_trees = ["build", 'old']

pygments_style = 'default' # "github-dark" # 'one-dark'
# pygments_style = "sphinx"

default_dark_mode = False

autodoc_default_options = {
    'member-order': 'bysource',
    'show-inheritance': True,
    'no-inherited-members': True,
    'special-members': '__init__',
    'undoc-members': True,
    'exclude-members': '__module__,_getref,__new__,__weakref__,__dict__,__repr__,__str__,__hash__,__eq__,__ne__,__lt__,__le__,__gt__,__ge__'
}


##############
# html theme #
##############



#####################
# api documentation #
#####################


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#

import sphinx_rtd_theme

# logo
# html_logo = '_static/img/logo_border.png' # should be wide
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
htmlhelp_basename = 'omnifigDoc'


# -- Extension configuration -------------------------------------------------

# -- Options for todo extension ----------------------------------------------

# If true, `todo` and `todoList` produce output, else they produce nothing.
todo_include_todos = True

# intersphinx_mapping = {
#     'python': ('https://docs.python.org/3/', None),
#     'torch': ('http://pytorch.org/docs/master/', None),
#     'opt_einsum': ('https://optimized-einsum.readthedocs.io/en/stable/', None)
# }





