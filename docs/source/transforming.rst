Transforming
============

.. currentmodule:: parce.transform

The :mod:`~parce.transform` module provides infrastructure to *transform* a
tree structure or a text to any datastructure you wish to create.

The basic idea of transformation is simple: for every Context in a tree
structure, a method of a Transform instance is called. The method has the same
name as the context's lexicon, and is called with an :class:`Items` instance
containing the list of children of that context.

Sub-contexts in that list already have been replaced with the result of that
context's lexicon's transformation method, wrapped in an :class:`Item`, so the
Items list consists of instances of either :class:`~parce.tree.Token` or
:class:`Item`. To make it easier to distinguish between the two, the Item class
has an :attr:`~Item.is_token` class attribute, set to False.

Thus, a Transform class can closely mimic a corresponding Language class. If
you want to ignore the output of a particular lexicon, don't define a method
with that name, but set its name to ``None`` in the Transform class definition.

How it works
------------

The actual task of transformation (evaluation) is performed by a
:class:`Transformer`. The Transformer has infrastructure to choose the
Transform class based on the current Language. Using the
:meth:`~Transformer.add_transform` method, you can assign a Transform instance
to a Language class.

There are two convenience functions :func:`transform_text` and
:func:`transform_tree`.

For example::

    from parce import root, Language, lexicon, default_action
    from parce.action import Delimiter, Number, String
    from parce.transform import Transform, transform_text

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r'\[', Delimiter, cls.list
            yield r'\d+', Number
            yield r'"', String, cls.string

        @lexicon
        def list(cls):
            yield r'\]', Delimiter, -1
            yield from cls.root

        @lexicon
        def string(cls):
            yield r'"', String, -1
            yield default_action, String


This language definition finds numbers, strings, and lists of those. We want to
convert those to their Python equivalents. So, we create a corresponding
Transform class, with methods having the same name as the lexicons in the
Language definition::

    class MyLangTransform(Transform):
        def root(self, items):
            result = []
            for i in items:
                if i.is_token:
                    if i.action is Number:
                        result.append(int(i.text))  # a Number
                else:
                    result.append(i.obj)            # a list or string
            return result

        def list(self, items):
            return self.root(items)

        def string(self, items):
            return items[0].text     # not the closing quote

Now let's test our Transform!

    >>> transform_text(MyLang.root, '1 2 3 [4 "Q" 6] x 7 8 9')
    [1, 2, 3, [4, 'Q', 6], 7, 8, 9]

It works! The above function call is equivalent to::

    >>> from parce.transform import Transformer
    >>> t = Transformer()
    >>> t.add_transform(MyLang, MyLangTransform())
    >>> t.transform_text(MyLang.root, '1 2 3 [4 "Q" 6] x 7 8 9')
    [1, 2, 3, [4, 'Q', 6], 7, 8, 9]


Transforming a tree structure
-----------------------------

Using the same Transform class, you can also transform a tree structure::

    >>> from parce.transform import transform_tree
    >>> tree = root(MyLang.root, '1 2 3 [4 "Q" 6] x 7 8 9')
    >>> tree.dump()
    <Context MyLang.root at 0-23 (8 children)>
     ├╴<Token '1' at 0:1 (Literal.Number)>
     ├╴<Token '2' at 2:3 (Literal.Number)>
     ├╴<Token '3' at 4:5 (Literal.Number)>
     ├╴<Token '[' at 6:7 (Delimiter)>
     ├╴<Context MyLang.list at 7-15 (5 children)>
     │  ├╴<Token '4' at 7:8 (Literal.Number)>
     │  ├╴<Token '"' at 9:10 (Literal.String)>
     │  ├╴<Context MyLang.string at 10-12 (2 children)>
     │  │  ├╴<Token 'Q' at 10:11 (Literal.String)>
     │  │  ╰╴<Token '"' at 11:12 (Literal.String)>
     │  ├╴<Token '6' at 13:14 (Literal.Number)>
     │  ╰╴<Token ']' at 14:15 (Delimiter)>
     ├╴<Token '7' at 18:19 (Literal.Number)>
     ├╴<Token '8' at 20:21 (Literal.Number)>
     ╰╴<Token '9' at 22:23 (Literal.Number)>
    >>> transform_tree(tree)
    [1, 2, 3, [4, 'Q', 6], 7, 8, 9]

Note that the :func:`transform_tree` gets the root lexicon from the root
element, and then automatically finds the corresponding Transform class, if you
didn't specify one yourself.

This is done by looking in the same module as the root lexicon's language,
and finding there a Transform subclass with the same name with ``"Transform"``
appended (see :meth:`Transformer.find_transform`).

Examples of Transform classes can be found in the :mod:`~parce.lang.css` and
the :mod:`~parce.lang.json` modules.

Calculator example
------------------

As a proof of concept, below is a simplistic calculator, it can be
found in :file:`tests/calc.py`:

.. literalinclude:: ../../tests/calc.py

Test it with::

    >>> from parce.transform import *
    >>> transform_text(Calculator.root, " 1 + 1 ")
    2
    >>> transform_text(Calculator.root, " 1 + 2 * 3 ")
    7
    >>> transform_text(Calculator.root, " 1 * 2 + 3 ")
    5
    >>> transform_text(Calculator.root, " (1 + 2) * 3 ")
    9


Integration with TreeBuilder
----------------------------

Integration with :class:`~parce.treebuilder.TreeBuilder` is still in the works.
The idea is that every Context can cache the transformed result, and that when
updating the tree only the contexts that were modified need to update their
transformation.

