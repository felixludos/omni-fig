.. _highlight-instantiation:

Automatic Instantiation
================================================================================

.. TODO: vignette A4 - create vs process


Beyond :ref:`accessing <Accessing Config Values>` primitives or simple containers like lists and dicts, you can also create arbitrarily complex :ref:`components <component>` automatically with the config object.

All you need is to include the key ``_type`` which specifies the name of the component that should be instantiated. The config object will then automatically instantiate the component and pass the config node to the component's constructor (unless the component is :ref:`configurable <Configurable>`).

See the feature slide :ref:`B7 <vignette-instantiation>`.

Here's an example:

.. code-block:: python

    import omnifig as fig

    @fig.component('cmp1')
    class Component1():
        def __init__(self, config):
            self.x = config.pull('x') # will raise an error if 'x' is not found
            self.y = config.pull('y', 10)

    @fig.component('cmp2')
    class Component2(fig.Configurable):
        def __init__(self, x, y=20):
            self.x = x
            self.y = y

    cfg = fig.create_config(
              b1={'_type': 'cmp1', 'x': 'value'},
              b2={'_type': 'cmp2', 'x': 'value2', 'y': 1},
    )

    print(cfg) # prints out:
    # obj1:
    #   _type: cmp1
    #   x: value
    # obj2:
    #   _type: cmp2
    #   x: value2
    #   y: 1

    obj1 = cfg.pull('b1') # instantiates a Component1 object

    assert obj1.x == 'value'
    assert obj1.y == 10
    assert isinstance(obj1, Component1)

    obj2 = cfg.pull('b2') # instantiates a Component2 object

    assert obj2.x == 'value2'
    assert obj2.y == 1
    assert isinstance(obj2, Component2)


Additionally, you can specify :ref:`modifiers <Modifying Components>` with the ``_mod`` key, and a custom :ref:`creator <Creators>` with the``_creator`` key for more control over what gets instantiated and how.


Creating/Processing Values
--------------------------

By default, only one instance of each component is created, so when pulling repeatedly, you will get the same instance of the component. However, this behavior can be adjusted by changing the :ref:`settings <Config Settings>` or by creating instances explicitly using :meth:`create <omnifig.abstract.AbstractConfig.create>`. In contrast, you can explicitly access the value of a node including passing in positional and keyword arguments using :meth:`process <omnifig.abstract.AbstractConfig.process>`.
For convenience, there are a few methods that combine the two: :meth:`peek_create <omnifig.abstract.AbstractConfig.peek_create>`, :meth:`peek_process <omnifig.abstract.AbstractConfig.peek_process>` (see for more info about :ref:`peeking <Traversing Configs>`).
Lastly, you can clear all instantiated components for the whole config tree using :meth:`clear_product <omnifig.config.nodes.ConfigNode.clear_product>`.

Continuing the example above:

.. code-block:: python

    obj3 = cfg.pull('b1') # returns the same object as obj1

    assert obj1 is obj3

    assert obj2 is cfg.peek_process('b2') # returns the same object as obj2

    obj4 = cfg.peek_create('b2') # returns a new object

    assert obj2 is not obj4

    cfg.clear_product() # clears all instantiated components

    assert obj1 is not cfg.pull('b1') # returns a new object

    cfg2 = fig.create_config(_type='cmp2', x='value3', y=0)

    obj5 = cfg2.process(y=100)

    assert obj5.x == 'value3'
    assert obj5.y == 100

    obj6 = cfg2.process(y=200)

    assert obj6.x == 'value3'
    assert obj6.y == 100 # not 200 because the component was already instantiated
    assert obj5 is obj6

    obj7 = cfg2.create('value4', y=200)

    assert obj7.x == 'value4'
    assert obj7.y == 200 # because the component was created explicitly
    assert obj7 is not obj6

