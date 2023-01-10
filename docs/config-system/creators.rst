Creators
================================================================================

.. TODO: vignette A8 - custom creators

By default, :ref:`pulling values <Accessing Config Values>` from the config object will :ref:`instantiate <Automatic Instantiation>` components including :ref:`modifiers <Modifying Components>`. However, you can easily customize how exactly any values are processed by creating custom :class:`creators <omnifig.abstract.AbstractCreator>`.

Creators must be :ref:`registered <Registration>` just like components and modifiers. Then if you want certain components to always use such a custom creator, then you can include that creator name when registering the component.

.. code-block:: python

    import omnifig as fig

    @fig.creator('custom-creator')
    class SpecialCreator(fig.Node.DefaultCreator):
        def create_product(self, config, args, kwargs, silent=None):
            # do something special
            print('creating something special')
            return super().create_product(config, args, kwargs, silent=None)

    @fig.component('some-component', creator='custom-creator')
    class Something(fig.Configurable):
        def __init__(self, x=1):
            self.x = x

    # then in a REPL:

    >>> cfg = fig.create_config(_type='some-component', x=2)

    >>> assert cfg.pull('x') == 2
    creating something special

    >>> obj = cfg.create()
    creating something special
    >>> assert obj.x == 2
    >>> assert isinstance(obj, Something)

Alternatively, you can specify the creator that should be used directly in the config under the key ``_creator``.

.. code-block:: python

    >>> cfg = fig.create_config(_type='some-component', x=2, _creator='custom-creator')

    >>> assert cfg.pull('x') == 2
    creating something special
    >>> assert obj.x == 2
    >>> assert isinstance(obj, Something)

Lastly, you can specify the creator as a :ref:`setting <Config Settings>` of the config object.

.. code-block:: python

    @fig.component('another-component') # without specifying a creator
    class Simple(fig.Configurable):
        def __init__(self, y=1):
            self.y = y

    # then in a REPL:

    >>> cfg = fig.create_config(_type='another-component', y=5)

    >>> obj1 = cfg.create() # uses default creator
    >>> assert obj1.y == 5
    >>> assert isinstance(obj1, Simple)

    >>> with cfg.context(creator='custom-creator'):
    ...     obj2 = cfg.create() # now uses the custom creator
    creating something special
    >>> assert obj2.y == 5
    >>> assert isinstance(obj2, Simple)

    >>> obj3 = cfg.create() # outside of the context, using default creator
    >>> assert obj3.y == 5
    >>> assert isinstance(obj3, Simple)

    >>> cfg.settings['creator'] = 'custom-creator'

    >>> obj4 = cfg.create() # now back to custom-creator
    creating something special
    >>> assert obj4.y == 5
    >>> assert isinstance(obj4, Simple)



