.. _highlight-registration:

Registration
================

Aside from config files, ``omni-fig`` primarily keeps track of three different kinds of top-level deliverables: scripts, components, and modifiers. These are all registered using the corresponding decorators :class:`fig.script() <omnifig.registration.script>`, :class:`fig.component() <omnifig.registration.component>`, and :class:`fig.modifier() <omnifig.registration.modifier>`.

.. _script:

* Scripts are functions that should expect the first positional argument to be the config object.

* Components are classes that are recommended to subclass :class:`fig.Configurable <omnifig.configurable.Configurable>` (see :ref:`Configurable`) to extract all the arguments in :code:`__init__` from the config object automatically. If they do not subclass :class:`fig.Configurable <omnifig.configurable.Configurable>`, then they should expect the first positional argument to be the config object.

.. TODO: vignette B8 modifying components

* Modifiers are classes much like components, except that they are used to modify components by dynamically creating a subclass of the modifier and the component at runtime. Consequently, it is also strongly recommended that modifiers subclass :class:`fig.Configurable <omnifig.configurable.Configurable>`, or otherwise they should expect the first positional argument to be the config object.

For simple components and scripts (especially components which are functions), there are two convenience types called :class:`fig.autocomponent <omnifig.registration.autocomponent>` and :class:`fig.autoscript <omnifig.registration.autoscript>` respectively. These variants behave the same as the regular decorators, except that instead of passing the config object during initialization, the arguments of the registered class or function are extracted from the config object automatically (much like :class:`fig.Configurable <omnifig.configurable.Configurable>`).

.. TODO: autocomponents vs configurable

.. _highlight-modifiers:

Configurable
------------

.. TODO: profiles and related projectsd

.. TODO: decorators for aliases and silencing
.. TODO: vignette A7

.. TODO: certify


When registering classes as components and modifiers, it is strongly recommended that the class is a subclass of :class:`fig.Configurable <omnifig.configurable.Configurable>`. This streamlines the :ref:`object instantiation <Automatic Instantiation>` from the config, so that all arguments in the :code:`__init__`, are automatically extracted from the config.

For additional control on how arguments are extracted from the config, checkout the :func:`fig.config_aliases <omnifig.configurable.config_aliases>` and :func:`fig.config_silence <omnifig.configurable.config_silence>` decorators.

.. code-block:: python

    import omnifig as fig

    class Shape(fig.Configurable): # note that does not get registered
        def __init__(self, area, color):
            self.color = color
            self.area = area

    @fig.component('circle')
    class Circle(Shape):
        def __init__(self, radius, **kwargs):
            super().__init__(area=3.14*radius**2, **kwargs)
            self.radius = radius


    @fig.component('rectangle')
    class Rectangle(Shape):
        @fig.config_aliases(width='w', height='h')
        def __init__(self, width, height, **kwargs):
            super().__init__(area=width*height, **kwargs)
            self.width = width
            self.height = height

    @fig.component('square')
    class Square(Rectangle):
        @fig.config_aliases(side=['size', 's'])
        def __init__(self, side, **kwargs):
            super().__init__(width=side, height=side, **kwargs)
            self.side = side

With these components, you can now instantiate them with the config for example:

.. code-block:: python

    cfg = fig.create_config(_type='circle', color='red', radius=5)
    obj1 = cfg.create()

    assert obj1.color == 'red'
    assert obj1.radius == 5
    assert isinstance(obj1, Circle)

    obj2 = cfg.create(color='green')

    assert obj2.color == 'green'
    assert obj2.radius == 5

    obj3 = cfg.create(2)

    assert obj3.color == 'red'
    assert obj3.radius == 2

    cfg = fig.create_config(_type='square', color='blue')

    obj4 = cfg.create(side=5)

    assert obj4.color == 'blue'
    assert obj4.side == 5
    assert isinstance(obj4, Square)
    assert isinstance(obj4, Rectangle)

    obj5 = cfg.create(size=6)

    assert obj5.color == 'blue'
    assert obj5.side == 6

    obj6 = cfg.create(s=7, color='yellow')
    assert obj6.color == 'yellow'
    assert obj6.area == 49




Modifying Components
--------------------

.. TODO: vignette B7 scripts, components, and modifiers

.. TODO: xray

.. TODO: vignette A9

Modifiers are effectively subclasses and mix-ins for which are abstracted from their super classes (registered components). Unlike regular mix-ins, you don't have to define the classes with all the desired mix-ins beforehand, and instead you can create them dynamically at runtime using the config.

To continue the example above, here are two examples of potential modifiers:

.. code-block:: python

    @fig.modifier('named')
    class Named(fig.Configurable):
        def __init__(self, name=None):
            self.name = name

    @fig.modifier('drawable')
    class Drawable(Shape):
        def draw(self):
            ...

    @fig.modifier('dark')
    class Dark(Shape):
        @fig.config_aliases(color='c')
        def __init__(self, area, color):
            color = f'dark-{color}'
            super().__init__(area, color)


Now instead of needing to define every combination of :class:`Named`, :class:`Drawable`, and :class:`Shape` beforehand, you can create only the combinations you need dynamically at runtime using the config:

.. code-block:: python

    cfg = fig.create_config(_type='circle', _mod='named', color='red', radius=5)
    obj1 = cfg.create('my-circle')

    assert obj1.name == 'my-circle'
    assert obj1.color == 'red'
    assert obj1.radius == 5
    assert isinstance(obj1, Circle)
    assert isinstance(obj1, Named)
    assert type(obj1).__name__ == 'Named_Circle'

    cfg = fig.create_config(_type='square', _mod=['named', 'drawable'], color='blue')
    obj2 = cfg.create()

    assert obj2.name is None
    assert obj2.color == 'blue'
    assert type(obj2).__name__ == 'Named_Drawable_Square'

    cfg = fig.create_config(_type='square', _mod=['named', 'dark'], c='green', name='my-square')
    obj3 = cfg.create()

    assert obj3.name == 'my-square'
    assert obj3.color == 'dark-green'
    assert isinstance(obj3, Dark)
    assert type(obj3).__name__ == 'Named_Dark_Square'


