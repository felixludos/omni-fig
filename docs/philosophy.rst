Philosophy
==========

.. role:: py(code)
   :language: python

.. TODO: section on extensibility (e.g. including abstract base classes for common use cases)

Python is an incredibly versatile language. The dynamic nature and expansive community allows developers to program with virtually no overhead, developing anything from highly specialized applications that make use of a plethora of packages to general scripts that fit into 100 lines of code.

However, with great power comes great responsibility: in this case that means keeping our many little scripts and packages organized (and ideally documented and with unit tests). There are already some excellent packages that take care of documentation ``sphinx`` (with ReadTheDocs) and a very simple testing framework ``pytest`` (with Github Actions). These tools can ensure the understandability and functionality of our code, but what about keeping the code itself organized?

How can we minimize code duplication while still being able to easily change or add new functionality or run everything in a variety of different execution environments? This is the purpose of ``omni-fig``. While there are a variety of organizational tools included in ``omni-fig`` (such as :ref:`profiles <Profiles>`, :ref:`projects <File Structure>`, and :ref:`behaviors <behaviors-info>`), the most important components are the :ref:`registration <Registration>` and the :ref:`config system <config-overview>`. The registration system allows for a fine-grained control to select which code is run and how. Meanwhile the config system keeps all the necessary arguments and parameters organized in an intuitive hierarchical structure enabling easy modification of what the scripts actually do.


Registration: Beyond :code:`import`
-------------------------------------

Python's native :code:`import` system is rather convenient (and significantly nicer than some other languages), nevertheless, for highly dynamic projects, it can slow down productivity to constantly make sure all the right code is made available where it is needed.

The registration system in ``omni-fig`` offers a much more fine-grained alternative (much of which is built directly into the config system). The idea is to register different pieces of code as a ``script``, ``component``, or ``modifier`` using the corresponding decorators depending on how it is meant to be used. A registered ``script`` (any callable) can be run in a variety of ways (e.g. from the command-line or a in an interactive environment like jupyter) but essentially act as a self contained operation. A ``component`` is some piece of code (usually a class) that builds an arbitrarily complex object which can be instantiated automatically from the config. Finally, ``modifiers`` allow ``components`` to be modified dynamically (see the :ref:`guide <Modifying Components>`).
The most important distinction between ``scripts`` and ``components`` is that ``components`` are created automatically by the config system, while ``scripts`` have to be called/executed manually and that ``components`` can be modified with ``modifiers`` (for more details see the corresponding sections below).

Once registered, ``scripts``, ``components``, and ``modifiers`` can be used anywhere mitigating the need for lots of :code:`import` statements in every new file. Consequently, as long as all source files are loaded when the project is loaded, all functionality that the developer explicitly wants to make accessible, is accessible by the name at runtime.

Another underrated benefit of using a registration system is that the registered objects can be referred to using their registered names (which are strings instead of python classes/objects). This allows config files to explicitly specify complex objects that can be built dynamically (see Config System for more info). Furthermore, object serialization (both for persistence and multi-processing) is much easier when the objects are referred to by their registered names.

Check out the :ref:`user guide <highlight-registration>`.

Config System
-------------

The code you write is only as valuable as you are able to use it in the way you want. This means, good code organization necessitates the power to specify exactly what the code should do in the form of arguments and configs. To that end, ``omni-fig`` provides a flexible config structure that uses a tree-like hierarchy to dynamically provide arguments for all components and subcomponents.

The hierarchical structure not only allows grouping arguments but it also allows for argument "scopes" - ie. when an argument is not found in the current node, it defaults to check the parent. More universal arguments can be set on a higher level of the tree, but then optionally be overridden in subcomponents without affecting other components.

.. TODO: discuss config merging

Check out the :ref:`user guide <config-overview>`.


