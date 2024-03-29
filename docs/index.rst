Unleashing Project Configuration and Organization!
==================================================


``omni-fig`` is a lightweight package to help you organize your python projects to make everything clear and easy to understand to collaborators and prospective users, while also offering unparalleled features to accelerate development.

The general-purpose project structure is well suited for both small and large projects, and is designed to be easily extensible to fit your needs. Most importantly, with the powerful configuration system, you never have to worry about any boilerplate code to parse command line arguments, read config files again, or even import the desired project components ever again!

User Guide
----------

There are two main parts of the user guide are the project organization and project configuration. The project organization chiefly concerns the expected file structure for ``omni-fig`` to correctly recognize and load your project, and a variety of different ways you can run your scripts. Keep in mind that most of project structure suggested here is not strictly required, and can easily be adapted to your specific workflow.
The project configuration covers all the powerful features the configuration system of ``omni-fig`` offers.


.. TODO: link to paper



.. toctree::
    :maxdepth: 2
    :caption: Introduction
    :hidden:

    installation
    highlights
    philosophy


.. toctree::
    :maxdepth: 2
    :caption: Project Structure
    :hidden:

    project-structure/projects
    project-structure/cli
    project-structure/interactive
    project-structure/registration
    project-structure/profiles
    project-structure/behavior


.. toctree::
    :maxdepth: 2
    :caption: Configuration System
    :hidden:

    config-system/overview
    config-system/composition
    config-system/access
    config-system/instantiation
    config-system/traversal
    config-system/settings
    config-system/exporting
    config-system/creators



.. toctree::
    :maxdepth: 1
    :caption: API Documentation
    :glob:
    :hidden:

    code/*


Citations
---------

.. include:: ../README.rst
    :start-after: citation-marker-do-not-remove
    :end-before: end-citation-marker-do-not-remove



.. Indices and tables
  ==================
  * :ref:`genindex`
  * :ref:`modindex`
  * :ref:`search`

