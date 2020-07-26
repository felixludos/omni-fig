Philosophy
==========

.. role:: py(code)
   :language: python

[todo]

Topics
------

- general philosophy: flexible power!
    - the programmer is king -> compilers hinder fast development
        - programmer centric development vs program centric development
    - write lots of small, modular functions/classes
    - register them as scripts/components or modifiers
    - use a hierarchical config system to easily specific arbitrarily complex arguments/parameters
    - at runtime the config object combines the simple modular objects to offer high flexibility and lots of power
- why `import` is not enough
- package vs leaf projects
- profiles and projects
    - related projects
- config object (push, pull, export)
    - features:
        - Keys:
            - '_{}' = protected - not visible to children
            - ({1}, {2}, ...) = [{1}][{2}]...
            - '{1}.{2}' = ['{1}']['{2}']
            - '{1}.{2}' = ['{1}'][{2}] (where {2} is an int and self['{1}'] is a list)
            - if {} not found: first check parent (if exists) otherwise create self[{}] = Config(parent=self)

        - Values:
            - '<>{}' = alias to key '{}'
            - '_x_' = (only when merging) remove this key locally, if exists
            - '__x__' = dont default this key and behaves as though it doesnt exist (except on iteration)
              (for values of "appendable" keys)
            - "+{}" = '{}' gets appended to preexisting value if if it exists
                (otherwise, the "+" is removed and the value is turned into a list with itself as the only element)

        - Also, this is Transactionable, so when creating subcomponents, the same instance is returned when pulling the same
        sub component again.

- config files (hierarchy/inheritance)
- scripts
    - meta args
    - execution modes
- components (registration and creation)
- modifiers (auto-modifiers, modifications)
    - auto-modifiers - dynamic type declarations, dynamically injecting behavior (mixins by config)
- lightweight alternatives (autocomponents, autoscripts)
