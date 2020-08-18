
.. role:: py(code)
   :language: python



.. raw:: html

    <img align="right" width="150" height="150" src="assets/logo_border.png" alt="omni-fig">

--------
omni-fig
--------

.. image:: https://readthedocs.org/projects/omnifig/badge/?version=latest
    :target: https://omnifig.readthedocs.io/en/latest/?badge=latest
    :alt: Documentation Status

.. image:: https://travis-ci.com/felixludos/omni-fig.svg?branch=master
    :target: https://travis-ci.com/felixludos/omni-fig
    :alt: Test Status

.. setup-marker-do-not-remove

.. role:: py(code)
   :language: python

Visit the project page_.

.. _page: https://www.notion.so/felixleeb/omni-fig-c5223f0ca9e54eb4b8d9749aade4a9d3

This package helps you keep your code organized, allows you to use your code in a variety of execution environments (from the terminal, in a jupyter notebook, through an IDE debugger, etc.), and provides a powerful config system for you to provide arguments/information to your scripts (as python objects, separate yaml files, or from the terminal directly).

The primary way to use this package is to create *projects* containing python source files and yaml (info and config) files (an example of which is discussed below). Each project uses ``Component``, ``Modifier``, and ``Script`` to register any

For lots of detailed examples in how the config system works, see the unit tests in ``tests/test_config.py`` and the documentation_, which also includes some examples.

Install
=======

.. install-marker-do-not-remove

Everything is tested with Python 3.7 on Ubuntu 18.04 and Windows 10, but in principle it should work on any system than can handle the dependencies.

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

A project only requires a yaml file called ``.fig.yml`` or similar (see documentation_), however, it is also suggested to create a directory called ``config`` to contain any config yaml files that should automatically be registered when the project is loaded. Usually, when loading a project, that requires running some python files, relative path to the top level source file to run should be specified in the project info file (``.fig.yml``) under the key ``src``. Below is an example of a simple ``omni-fig`` project with all the suggested bells and whistles:

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
    │   ├── __init__.py
    │   └── ...
    │
    ├── .fig.yml - project info file
    ├── startup.py - python file to be called to load project (must be specified in project info file)
    ├── script1.py - any additional source files (usually executable)
    └── ...

For the example above, ``.fig.yml`` should contain something like:

.. code-block:: yaml

    name: myproject
    src: startup.py

To specify that ``startup.py`` should be run to load the project. ``startup.py`` might include something like:

.. code-block:: python

    import src
    import script1

    print('Loaded myproject!') # optional message to see when the project has been loaded

The ``startup.py`` file imports any necessary source files (registering any ``Components``, ``Modifiers``, ``Scripts``, or configs specfied therein). For example, ``script1.py`` might look like:

.. code-block:: python

    import omnifig as fig

    @fig.Component('myconverter') # registers a new component (any class or function to be specified in the config)
    class Converter:
        def __init__(self, A): # when creating a component, the input is the config object at the corresponding node
            self.rates = A.pull('rates', {})

        def to_usd(self, value, currency):
            if currency in self.rates:
                return value / self.rates[currency]
            return value

    @fig.AutoModifier('sketchy') # registers a new automodifier (used to dynamically modify components)
    class Sketchy:
        def __init__(self, A):
            super().__init__(A) # AutoModifiers become subclasses of the Component they modify

            self.fudge_the_numbers = A.pull('fudge_the_numbers', True)

        def to_usd(self, value, currency):
            value = super().to_usd(value, currency)
            if self.fudge_the_numbers:
                return value * 0.9
            return value


    @fig.Script('myscript', description='Does something awesome') # registers a new script called "myscript"
    def run_train_model(A): # config object containing all necessary config info
        print('Running myscript!')

        arg1 = A.pull('arg1') # gets the value corresponding to "arg1" in the config

        # pull the value corresponding to the key "arg2" starting from the node at "some.deep"
        # defaults to "[default value]" if that fails
        arg2 = A.pull('some.deep.arg2', '[default value]')

        # set (and get) arg2 to "myvalue", unless it already exists
        # also this will automatically create the node "other_branch" if it doesn't already exist
        arg3 = A.push('other_branch.arg3', 'myvalue', overwrite=False)

        # when a node (eg. "converter") contains the key "_type" (and optionally "_mod") it is treated as a component
        A.push('converter._type', 'myconverter', overwrite=False)

        # values can be lists/dicts (even nested)

        budget, unit = A.pull('mymoney', [1000000000, 'Zimbabwe-dollars'])

        converter = A.pull('converter', None) # when pulling components, they objects are automatically created

        if converter is not None:
            budget = converter.to_usd(budget, unit)
        else:
            raise Exception('No converter to confirm budget')

        # ... maybe do something interesting with all that money

        msg = "I'm {}a millionaire".format('' if budget > 1e6 else 'not ')
        print(msg)

        return msg # anything this script should return

    if __name__ == '__main__':
        fig.entry('myscript') # automatically runs "myscript" script when called directly
        # fig.entry() alone has the same effect as executing the "fig" command from the terminal

Any function or class that should be specified in the config should be registered as a ``Component``. When "pulling" a component (a config node that contains the "_type" key), the config system will automatically get the corresponding class/function and run it (returning the created instance/output). You can also define and register ``Modifiers`` to dynamically specify modifications that you want to make to the components in the config (using the "_mod" key in the same node as "_type").


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

    # execute myscript with "myconfig1" as config updated by command line argument
    fig myscript myconfig1 --arg1 cmdline

    # execute myscript with merged config file and command line arguments
    python script1.py myconfig1 dir1/myconfig2 --some.deep.arg2 10.2

    # execute myscript in debug mode with merged config and command line argument
    python script1.py -d myconfig1 dir1/myconfig2 --converter._mod.sketchy 1 --arg1

It might be worth taking a look at the resulting config object looks like for each of these commands (and depending on what information is saved in the corresponding config files in ``myproject/config/``. Note that you can use ``-d`` to switch to debug mode (see documentation_ for more info).

You might also load and run scripts in this project from a jupyter notebook (or a python console) using:

.. code-block:: python

    import omnifig as fig

    fig.initialize('myproject') # load profile and project

    A = fig.get_config('dir1/myconfig2', 'config1') # positional arguments can be names of registered config files
    out1 = fig.run('myscript', A)

    B = fig.get_config('config1', arg1=[1,2,3]) # keyword arguments are much like command line arguments
    out2 = fig.run('myscript', B, debug=True) # meta arguments (such as "debug") can be set using keyword args in run()

    C = fig.get_config(arg1='something', arg2='another thing')
    C.update(B)
    C.push('arg1', 'something else') # the config object can be modified with push()/update()
    out3 = fig.run('myscript', C)

    # quick_run effectively combines get_config and
    out4 = fig.quick_run('myscript', 'config1', use_gpu=True)

While this example should give you a basic idea for what a project might look like, this only touches on the basics of what you can do with ``omni-fig``. I strongly recommend you check out the documentation_. for more information, additionally there are some examples of real projects that use ``omnifig`` such as foundation_ and No-Nonsense-News_ .

.. _documentation: https://omnifig.readthedocs.io/

.. _foundation: https://github.com/felixludos/foundation/

.. _No-Nonsense-News: https://github.com/felixludos/nnn/

.. end-quickstart-marker-do-not-remove


TODO
====

Features that could be added/improved:

- include convenience scripts (such as creating/changing projects)
- more examples
- enable customizing the print messages when using a config
- full coverage with unit tests
- allow registered "macros" for modifying config behavior
- deep copy of config objects
- integrate ``humpack.adict`` for configs (easier direct access to data)
- use global settings everywhere (especially for logging)

Feedback and contributions are always welcome.

.. end-setup-marker-do-not-remove