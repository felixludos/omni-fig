Philosophy
==========

.. role:: py(code)
   :language: python

.. TODO: section on extensibility (e.g. including abstract base classes for common use cases)

Python is an incredibly versatile language. The dynamic nature and expansive community allows developers to program with virtually no overhead, developing anything from highly specialized applications that make use of a plethora of packages to general scripts that fit into 100 lines of code.

However, with great power comes great responsibility: in this case that means keeping our many little scripts and packages organized (and ideally documented and with unit tests). There are already some excellent packages that take care of documentation ``sphinx`` (with ``readthedocs``) and a very simple testing framework ``pytest`` (with ``Travis CI``). These tools can ensure the understandability and functionality of our code, but what about keeping the code itself organized?

How can we minimize code duplication while still being able to easily change or add new functionality or run everything in a variety of different execution environments? This is the purpose of `omni-fig`. While there are a variety of organizational tools included in `omni-fig` (such as machine profiles, projects, run modes with customizable meta arguments), the most important components are the registration and the config system. The registration system allows for a fine-grained control to select which code is run and how. Meanwhile the config system keeps all the necessary arguments and parameters organized in an intuitive hierarchical structure enabling easy modification of what the scripts actually do.


Registration: Beyond ``import``
-------------------------------

Python's native ``import`` system is rather convenient (and significantly nicer than some other languages), nevertheless, for highly dynamic projects, it can slow down productivity to constantly make sure all the right code is made available where it is needed.

The registration system in ``omni-fig`` offers a much more fine-grained alternative (much of which is built directly into the config system). The idea is to register different pieces of code as a `Script`, `Component`, or `Modifier` using the corresponding decorators depending on how it is meant to be used. Anything registered as a `Script` (usually a function) can be run in a variety of ways (see "run modes" below) but essentially act as a self contained operation. A `Component` is some piece of code (usually a class) that builds an arbitrarily complex object to be used later (such as in a `Script`). Finally, `Modifiers` allow `Components` to be modified dynamically (however, `Modifiers` are a bit more involved to understand, see below for more info and examples).
The most important distinction between `Scripts` and `Components` is that `Components` are created automatically by the config system, while `Scripts` have to be called/executed manually and that `Components` can be modified with `Modifiers` (for more details see the corresponding sections below).

Once registered, `Scripts`, `Components`, and `Modifiers` can be used anywhere mitigating the need for lots of ``import`` statements in every new file. Additionally, `Scripts` can be run using all of the registered "run modes" (eg. run from the terminal, with a debugger, etc.).

Another major benefit of using a registration system is that the registered objects can be referred to using their registered names (which are strings instead of python classes/objects). This allows config files to explicitly specify complex objects that can be built dynamically (see Config System for more info).


Config System
-------------

The code you write is only as valuable as you are able to use it in the way you want. This means, good code organization necessitates the power to specify exactly what the code should do in the form of arguments and configs. To that end, `omni-fig` provides a flexible config structure that uses a tree-like hierarchy to dynamically provide arguments for all components and subcomponents.

The hierarchical structure not only allows grouping arguments but it also allows for argument "scopes" - ie. when an argument is not found in the current node, it defaults to check the parent. More universal arguments can be set on a higher level of the tree, but then optionally be overridden in subcomponents without affecting other components.



