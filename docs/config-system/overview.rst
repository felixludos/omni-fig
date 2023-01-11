.. _config-overview:

Overview
================================================================================

The original motivation for this package was to design a system that would read arguments from files, the terminal, or directly as python objects (eg. in a jupyter notebook) and would structure so that the arguments are always used in the code where they need to be. This is accomplished chiefly by a hierarchical tree-like structure in the config much like a tree where each branch corresponds to the a :code:`dict` or :code:`list` of arguments.

This section discusses different ways to create and use the config object. You can create config objects using the :func:`fig.create_config <omnifig.top.create_config>` by directly passing keyword arguments. However, usually, you will want to populate the config object with parameters in config files, which you can do either by passing in the path to a yaml file to :func:`fig.create_config <omnifig.top.create_config>` as a positional argument, or the recommended way: by the name of the registered config file. All yaml files in the ``config/`` directory are automatically registered as long as you create a :ref:`project info file <highlight-file-structure>`. Note that you can pass in any number of positional arguments to :ref:`compose multiple config files <Composing Config Files>`. From the :ref:`command-line interface <Command Line Interface>`, you can also specify multiple config files and keyword arguments.

The easiest way to access parameters in the config object is using :meth:`pull() <omnifig.abstract.AbstractConfig.pull>`, but there's more information on :ref:`accessing values here <Accessing Config Values>`.

.. code-block:: python

    import omnifig as fig

    cfg = fig.create_config(arg1=True, arg2='hello', arg3=[1,2,3])

    assert cfg.pull('arg1') is True
    assert cfg.pull('arg2') == 'hello'
    assert cfg.pull('arg3') == [1,2,3]

    # specify a default when the query is not found
    assert cfg.pull('arg4', 'default') == 'default'

    # specify multiple queries to check in order with `pulls`
    assert cfg.pulls('arg5', 'arg2') == 'hello'
    assert cfg.pulls('arg6', 'arg7', 'arg8', default='not-found') == 'not-found'


