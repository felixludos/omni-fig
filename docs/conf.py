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
    "sphinx.ext.doctest",
    "sphinx.ext.napoleon",
    'sphinx.ext.githubpages',
    "sphinx.ext.intersphinx",
    "sphinx.ext.githubpages",
    'sphinx_autodoc_typehints',
    "myst_parser",
    'sphinx.ext.autosectionlabel',
    'sphinx_rtd_dark_mode',
]
templates_path = []
source_suffix = {".rst": "restructuredtext", ".md": "markdown"}
master_doc = "index"
exclude_trees = ["build"]
pygments_style = "sphinx"

default_dark_mode = False


##############
# html theme #
##############

html_theme = "sphinx_rtd_theme"
html_theme_options = {}
html_static_path = []
htmlhelp_basename = "roboball2ddoc"


#####################
# api documentation #
#####################


# def skip(app, what, name, obj, would_skip, options):
#     if name == "__init__":
#         return False
#     return would_skip
#
#
# def setup(app):
#     app.connect("autodoc-skip-member", skip)
#
#
# autoclass_content = "both"




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





