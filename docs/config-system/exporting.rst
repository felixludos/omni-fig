Saving/Loading Configs
================================================================================

.. TODO: vignette A6 - exporting

Despite the hierarchical structure of the config object, it can ultimately always be exported as a simple yaml file - so it should not contain any values that are primitives (:code:`str`, :code:`bool`, :code:`int`, :code:`float`, :code:`None`) aside from the branches that behave either as a :code:`dict` or :code:`list`. Using the registries, the config can implicitly contain specifications for arbitrarily complex components such as objects and functions (see :ref:`automatic instantiation <Automatic Instantiation>` for more details and examples). Consequently, any instantiated objects are **not** included when exporting or saving the config.

To export the config object as a :code:`str`, use :meth:`to_yaml() <omnifig.config.ConfigNode.to_yaml>`.

.. code-block:: python

    import omnifig as fig

    cfg = fig.create_config(x=1, y='hello')

    print(cfg.to_yaml())

    # prints out:
    # x: 1
    # y: hello

Meanwhile, you can save the config file to a file using :meth:`export() <omnifig.config.ConfigNode.export>`.

.. code-block:: python

    import omnifig as fig

    cfg = fig.create_config(x=1, y='hello')

    path = cfg.export('my_config', root='/some/path/')

    # path is now '/some/path/my_config.yaml'

Then the file can be loaded using :meth:`create_config() <omnifig.top.create_config>` by passing the path to the file in.

.. code-block:: python

    import omnifig as fig

    cfg = fig.create_config('/some/path/my_config.yaml')

    print(cfg)

    # prints out:
    # x: 1
    # y: hello


