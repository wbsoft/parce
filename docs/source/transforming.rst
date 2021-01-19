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

It works! Note that the stray `x` is ignored, because it is not matched by any
rule. The above function call is equivalent to::

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

.. note::

   Note that the :func:`transform_tree` gets the root lexicon from the root
   element, and then automatically finds the corresponding Transform class, if
   you didn't specify one yourself.

   This is done by looking in the same module as the root lexicon's language,
   and finding there a Transform subclass with the same name with
   ``"Transform"`` appended (see :meth:`Transformer.find_transform`).

Examples of Transform classes can be found in the :mod:`~parce.lang.css` and
the :mod:`~parce.lang.json` modules.

Calculator example
------------------

As a proof of concept, below is a simplistic calculator, it can be
found in :file:`tests/calc.py`:

.. literalinclude:: ../../tests/calc.py

Test it with::

    >>> from parce.transform import transform_text
    >>> from tests.calc import Calculator   # (from source directory)
    >>> transform_text(Calculator.root, " 1 + 1 ")
    2
    >>> transform_text(Calculator.root, " 1 + 2 * 3 ")
    7
    >>> transform_text(Calculator.root, " 1 * 2 + 3 ")
    5
    >>> transform_text(Calculator.root, " (1 + 2) * 3 ")
    9


Integration with TreeBuilder and Document
-----------------------------------------

It is very easy to keep a transformed structure up-to-date when a tree changes.
The Transformer caches the result of every transform method using a weak
reference to the Context that yielded that result.

When the TreeBuilder changes the tree, it emits the event ``"invalidate"``
with the youngest node that has its children changed (i.e. tokens or contexts
were added or removed).

The Transformer then knows that that context and all its ancestors need to be
recomputed. In the process all newly added contexts are evaluated as well,
because their transformations can't be found in the cache. Contexts that only
changed position are not recomputed. If you want your transformed structure to
know the position in the text, you should store references to the corresponding
tokens in your structure. The ``pos`` attribute of the Tokens that move is
adjusted by the tree builder, so they still point to the right position after
an update of the tree.

Here is an example::

    >>> from parce.lang.json import Json
    >>> from parce import Document
    >>> from parce.transform import Transformer
    >>>
    >>> d = Document(Json.root)
    >>> t = Transformer()
    >>> t.connect_treebuilder(d.builder())
    >>>
    >>> d.set_text('{"key": [1, 2, 3, 4, 5]}')
    >>> t.result(d.get_root())
    {'key': [1, 2, 3, 4, 5]}
    >>> d.insert(22, ", 6, 7, 8")
    >>> t.result(d.get_root())
    {'key': [1, 2, 3, 4, 5, 6, 7, 8]}

Note that after inserting some text the transformed result automatically gets
updated, because we called the :meth:`~Transformer.connect_treebuilder`
method.

When the tree builder is about to inject the modified tree part in the
Document's tree, it emits the ``"replace"`` event. The transformer reacts by
interrupting any current job that might be busy computing the transformed
result. When the tree builder is replacing, it emits the ``"invalidate"``
event, so the transformer knows which contexts need to be deleted from the
cache. Finally, when the tree builder emits ``"finished"`` the transformer
rebuilds our transformed result, using as much as possible the previously
cached transform results for Contexts that did not change.

A single Transformer can be used for multiple transformation jobs for multiple
documents or tree builders, even at the same time. It shares the added
Transform instances between multiple jobs and documents. If your Transform
classes keep internal state that might not be desirable; in that case you can
use a Transformer for every document or tree.

If you were using a :class:`~parce.treebuilder.BackgroundTreeBuilder`, the
transformed result is automatically computed in a background thread as well
(during the ``self.emit("finished")`` call in the tree builder's method
:meth:`~parce.treebuilder.TreeBuilder.process_finished`). But you can also use
a :class:`BackgroundTransformer` or inherit from Transformer to add your own
implementation for running in the background.
