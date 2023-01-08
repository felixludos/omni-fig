Registration
================

Aside from config files, ``omni-fig`` primarily keeps track of three different kinds of top-level deliverables: scripts, components, and modifiers. These are all registered using the corresponding decorators :func:`fig.script() <omnifig.registration.script>`, :func:`fig.component() <omnifig.registration.component>`, and :func:`fig.modifier() <omnifig.registration.modifier>`.

.. _script:

* Scripts are functions that should expect the first positional argument to be the config object.

* Components are classes that are recommended to subclass :class:`fig.Configurable <omnifig.configurable.Configurable>` (see :ref:`Configurable`) to extract all the arguments in :code:`__init__` from the config object automatically. If they do not subclass :class:`fig.Configurable <omnifig.configurable.Configurable>`, then they should expect the first positional argument to be the config object.

.. TODO: vignette B8 modifying components

* Modifiers are classes much like components, except that they are used to modify components by dynamically creating a subclass of the modifier and the component at runtime. Consequently, it is also strongly recommended that modifiers subclass :class:`fig.Configurable <omnifig.configurable.Configurable>`, or otherwise they should expect the first positional argument to be the config object.

.. TODO: discuss autocomponents and autoscripts

.. TODO: autocomponents vs configurable


[missing]

.. TODO: vignette B7 scripts, components, and modifiers

.. TODO: xray

.. TODO: vignette A9

Configurable
------------

[missing]

.. TODO: profiles and related projectsd

.. TODO: decorators for aliases and silencing
.. TODO: vignette A7

.. TODO: certify

