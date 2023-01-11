Traversing Configs
================================================================================

.. TODO: vignette B9 traversing config

The config object is always a node in a tree. The root node is what is returned when creating the config node, but when :ref:`instantiating <Automatic Instantiation>` a :ref:`component` the corresponding child node is passed in. You can also traverse the config tree using by iteration or using :meth:`peek() <omnifig.abstract.AbstractConfig.peek>`. :meth:`peek() <omnifig.abstract.AbstractConfig.peek>` is given a query (usually a key) and then traverses the config object to find the node corresponding to that query.

.. code-block:: python

    cfg = fig.create_config(x='hello',
        l = [1, 2, 3]
        d = dict(a=1, b=2, c=dict(x=1, y=2))
    )

    print(cfg) # prints out:
    # x: hello
    # l: [1, 2, 3]
    # d:
    #   a: 1
    #   b: 2
    #   c:
    #     x: 1
    #     y: 2

    assert cfg.parent is None

    node = cfg.peek('x')
    assert node.parent is cfg
    assert node.pull() == 'hello'

    node2 = cfg.peek('l')
    assert node2.parent is cfg
    assert node2.pull() == [1, 2, 3]
    assert cfg.peek('x.l') is node2

    assert node2.peek('0') is cfg.peek('l.0')
    assert node2.peek('1').pull() == 2

    d = cfg.peek('d')
    assert d.pull('a') == 1
    assert d.pull('x') == 'hello'
    assert d.pull('c.x') == 1

    c = d.peek('c')
    assert c.pull('x') == 1
    assert c.pull() == dict(x=1, y=2)
    assert c.parent is d

    assert c.root is cfg
    assert cfg.root is cfg

    assert not cfg.is_leaf
    assert not d.is_leaf
    assert c.is_leaf


Similar to :meth:`pull() <omnifig.abstract.AbstractConfig.pull>` (used to :ref:`access <Accessing Config Values>` config values), :meth:`peek() <omnifig.abstract.AbstractConfig.peek>` also has a variant which allows for multiple queries :meth:`peeks() <omnifig.abstract.AbstractConfig.peeks>`.

Iteration
---------

You can iterate over the child nodes of a config nodes either using :meth:`peek_children <omnifig.abstract.AbstractConfig.peek_children>` or :meth:`pull_children <omnifig.abstract.AbstractConfig.pull_children>` (to iterate over the values).

There are variants to include the keys when iterating :meth:`pull_named_children <omnifig.abstract.AbstractConfig.pull_named_children>` and :meth:`peek_named_children <omnifig.abstract.AbstractConfig.peek_named_children>`.


