
.. role:: py(code)
   :language: python

.. raw:: html

    <img align="right" width="150" height="150" src="assets/logo_border.png" alt="omni-fig">


--------
omni-fig
--------

Configuration and project organization without compromises

.. image:: https://readthedocs.org/projects/omnifig/badge/?version=latest
    :target: https://omnifig.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status


.. image:: https://github.com/felixludos/omni-fig/actions/workflows/tests.yaml/badge.svg
    :target: https://github.com/felixludos/omni-fig/actions/workflows/tests.yaml
    :alt: Unit-Tests

.. setup-marker-do-not-remove

.. role:: py(code)
   :language: python

.. Visit the project page_.

.. _page: https://www.notion.so/felixleeb/omni-fig-c5223f0ca9e54eb4b8d9749aade4a9d3

This package contains a powerful config system for you to provide arguments/information to your scripts (as separate yaml files, from the terminal, or directly in python) to enable your code to be conveniently run in a variety of execution environments (from the terminal, in a jupyter notebook, through an IDE debugger, etc.).


The primary way to use this package is to create *projects* containing python source files and yaml (info and config) files (an example of which is discussed below). Each project uses ``component``, ``modifier``, and ``script`` to register artifacts which can then be referenced in the config.

For lots of detailed examples in how the config system works, see the unit tests in ``tests/test_config.py`` and the documentation_, which also includes some examples.

Install
=======

.. install-marker-do-not-remove

Everything is tested with Python 3.7 on Ubuntu 18.04 and Windows 10, but in principle it should work on any system that can handle the dependencies.

You can install this package through pip:

.. code-block:: bash

    pip install omnifig

You can clone this repo and install the local version for development:

.. code-block:: bash

    git clone https://github.com/felixludos/omni-fig
    pip install -e ./omni-fig

.. end-install-marker-do-not-remove

Quickstart
==========

.. quickstart-marker-do-not-remove

A project only requires a yaml file called ``.fig.yml`` (see documentation_), however, it is also suggested to create a directory called ``config/`` to contain any config yaml files that should automatically be registered when the project is loaded. Usually, when loading a project, that requires running/importing some python files, relative path to the top level source file to run should be specified in the project info file (``.fig.yml``) under the key ``src`` and any modules should be specified with ``module``. Below is an example of a simple ``omni-fig`` project with all the suggested bells and whistles:

.. code-block::

    project/ - project root name (can be anything)
    │
    ├── config/ - any yaml config files that should automatically be registered
    │   ├── dir1/
    │   │   ├── myconfig2.yaml
    │   │   └── ... - any configs will be registered with the relative path as prefix ("dir1/")
    │   │
    │   ├── myconfig1.yaml
    │   └── debug.yaml - config to be automatically used in debug mode
    │
    ├── src/ - any python source files
    │   ├── __init__.py - python file to be called to load project as a module into omnifig.projects
    │   ├── script1.py - any additional source files part of the module
    │   └── ...
    │
    ├── .fig.yml - project info file
    └── ...

For the example above, ``.fig.yml`` should contain something like:

.. code-block:: yaml

    name: myproject
    module: src

To specify that ``src/`` contains the code necessary load the project.

Inside the python package ``src/`` you can register any ``component``s, ``modifier``s, ``script``s, or configs needed for the project. For example, ``src/__init__.py`` might look like:

.. code-block:: python

    import omnifig as fig

    @fig.component('myconverter') # registers a new component (any class or function to be specified in the config)
    class Converter(fig.Configurable):
        def __init__(self, rates=None): # when creating a component, the input is the config object at the corresponding node
            if rates is None:
                rates = {}
            self.rates = rates

        def to_usd(self, value, currency):
            return value / self.rates.get(currency, 1.)

    @fig.modifier('sketchy') # registers a new modifier (used to dynamically modify components)
    class Sketchy(fig.Configurable):
        def __init__(self, fudge_the_numbers=True, **kwargs):
            super().__init__(**kwargs) # modifiers become subclasses of the component they modify

            self.fudge_the_numbers = fudge_the_numbers

        def to_usd(self, value, currency):
            value = super().to_usd(value, currency)
            if self.fudge_the_numbers:
                return value * 0.9
            return value

    @fig.script('myscript', description='Does something awesome') # registers a new script called "myscript"
    def run_train_model(A): # config object containing all necessary config info
        print('Running myscript!')

        arg1 = A.pull('arg1') # gets the value corresponding to "arg1" in the config

        # pull the value corresponding to the key "arg2" starting from the node at "some.deep"
        # defaults to "[default value]" if that fails
        arg2 = A.pull('some.deep.arg2', '[default value]')

        # set (and get) arg2 to "myvalue", unless it already exists
        # also this will automatically create the node "other_branch" if it doesn't already exist
        arg3 = A.push('other_branch.arg3', 'myvalue', overwrite=False)

        # using `pulls()`, you can check multiple keys and return a default value if none of them are found
        name = A.pulls('name', 'nickname', default='-unknown-')
        print('Hello', name)

        # when a node (eg. "converter") contains the key "_type" (and optionally "_mod") it is treated as a component
        A.push('converter._type', 'myconverter', overwrite=False)

        # values can be lists/dicts (even nested)
        # you can also use "silent" to suppress messages to stdout when pulling values
        budget, unit = A.pull('mymoney', [1000000000, 'Zimbabwe-dollars'], silent=True)

        converter = A.pull('converter', None) # when pulling components, the objects are automatically created

        if converter is not None:
            budget = converter.to_usd(budget, unit)
        else:
            raise Exception('No converter to confirm budget')

        # ... maybe do something interesting with all that money

        msg = "I'm {}a millionaire".format('' if budget > 1e6 else 'not ')
        print(msg)

        return msg # anything this script should return


Any function or class that should be specified in the config should be registered as a ``component``. When "pulling" a component (a config node that contains the ``_type`` key), the config system will automatically get the corresponding class/function and call it (returning the created instance/output). You can also define and register ``modifier``s to dynamically specify mix-ins that you want to make to the components in the config (using the ``_mod`` key in the same node as ``_type``).


It is highly recommended that you create a profile info yaml file and set the environment variable ``FIG_PROFILE`` to the full path to that profile info file. For example, the profile might contain:

.. code-block:: yaml

    name: mycomputer

    projects:
        myproject: /path/to/myproject # path to the "myproject" directory mentioned above

As you create new projects, you can add those to the profile info file so they can loaded from anywhere. By default, only the project in the current working direcory is loaded (and any "related" projects thereof), however that can also be changed in the profile info file (see the documentation_).

With this setup, you should be able to run all of the below (from the terminal inside ``myproject/``):

.. code-block:: bash

    # execute myscript without any config files or arguments
    fig myscript

    # execute myscript in debug mode ("-d") and with config file "dir1/myconfig2"
    fig -d myscript dir1/myconfig2

    # execute myscript with "myconfig1" as config updated by command line argument "arg1"
    fig myscript myconfig1 --arg1 cmdline

    # execute myscript with merged config file and command line arguments
    python script1.py myconfig1 dir1/myconfig2 --some.deep.arg2 10.2

    # execute myscript in debug mode with merged config and command line argument
    python script1.py -d myconfig1 dir1/myconfig2 --converter._mod.sketchy 1 --arg1

It might be worth taking a look at the resulting config object looks like for each of these commands (and depending on what information is saved in the corresponding config files in ``myproject/config/``. Note that you can use ``-d`` to switch to debug mode (see documentation_ for more info).

You might also load and run scripts in this project from a jupyter notebook (or a python console) using:

.. code-block:: python

    import omnifig as fig

    fig.initialize('myproject') # load all source files and configs associated with the project

    A = fig.create_config('dir1/myconfig2', 'config1') # positional arguments should be names of registered config files
    out1 = fig.run('myscript', A)

    B = fig.create_config('config1', arg1=[1,2,3]) # keyword arguments are much like command line arguments
    out2 = fig.run('myscript', B, debug=True) # meta arguments (such as "debug") can be set using keyword args in run()

    C = fig.create_config(arg1='something', arg2='another thing')
    C.update(B)
    C.push('arg1', 'something else') # the config object can be modified with push()/update()
    out3 = fig.run('myscript', C)

    # quick_run effectively combines create_config() and run()
    out4 = fig.quick_run('myscript', 'config1', use_gpu=True)


While this example should give you a basic idea for what a project might look like, this only touches on the basics of what you can do with ``omni-fig``. I strongly recommend you check out the documentation_ for more information and examples.

.. _documentation: https://omnifig.readthedocs.io/

.. _omnilearn: https://github.com/felixludos/omni-learn/

.. _No-Nonsense-News: https://github.com/felixludos/nnn/

.. end-quickstart-marker-do-not-remove

Citation
========

If you used `omnifig` in your work, please cite it using:


.. code-block:: tex

   @misc{leeb2022omnifig,
     title = {Omni-fig: Configuration and Project Management for Python},
     author = {Leeb, Felix},
     publisher = {GitHub},
     year = {2022}
   }



.. Road to 1.0
	===========

	Major features to be added in the near future:

	- configuration macros for modifying every part of the config behavior
	- customized the print messages or logging when using a config
	- enable multi-processing with registered artifacts
	- server run mode to submit, monitor, and schedule commands
	- full coverage with unit tests
	- clean up global settings and env variables

	Feedback and contributions are always welcome.

.. end-setup-marker-do-not-remove