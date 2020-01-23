Accessing the Tree Structure
============================

When you have parsed text, the result is a tree structure of Tokens,
nested in Contexts, which may be nested in other Contexts.

Let's look at the generated token tree of the simple example of the Getting
started section::

    >>> tree.dump()
    <Context Nonsense.root at 1-108 (19 children)>
     ├╴<Token 'Some' at 1:5 (Text)>
     ├╴<Token 'text' at 6:10 (Text)>
     ├╴<Token 'with' at 11:15 (Text)>
     ├╴<Token '3' at 16:17 (Literal.Number)>
     ├╴<Token 'numbers' at 18:25 (Text)>
     ├╴<Token 'and' at 26:29 (Text)>
     ├╴<Token '1' at 30:31 (Literal.Number)>
     ├╴<Token '"' at 32:33 (Literal.String)>
     ├╴<Context Nonsense.string at 33-67 (2 children)>
     │  ├╴<Token 'string inside\nover multiple '... at 33:66 (Literal.String)>
     │  ╰╴<Token '"' at 66:67 (Literal.String)>
     ├╴<Token ',' at 67:68 (Delimiter)>
     ├╴<Token 'and' at 69:72 (Text)>
     ├╴<Token '1' at 73:74 (Literal.Number)>
     ├╴<Token '%' at 75:76 (Comment)>
     ├╴<Context Nonsense.comment at 76-89 (1 children)>
     │  ╰╴<Token ' comment that' at 76:89 (Comment)>
     ├╴<Token 'ends' at 90:94 (Text)>
     ├╴<Token 'on' at 95:97 (Text)>
     ├╴<Token 'a' at 98:99 (Text)>
     ├╴<Token 'newline' at 100:107 (Text)>
     ╰╴<Token '.' at 107:108 (Delimiter)>

Token
-----

We see that the Token instances represent the matched text. Every Token has
the matched text in the ``text`` attribute, the position where it is in the
source text in the ``pos`` attribute, and the action it was given in the
``action`` attribute.  Besides that, Tokens also have an ``end`` attribute,
which is actually a property and basically returns ``self.pos +
len(self.text)``.

Although a Token is not a string, you can test for equality::

    if token == "bla":
        # do something

Also, you can check if some text is in some Context::

    if 'and' in tree:
        # do some_thing if 'and' is in the root context.

Context
-------

A Context is basically a Python list, and it has the lexicon that created it
in the ``lexicon`` attribute. The root of the tree is called the root
context, it carries the root lexicon. You can access its
child contexts and tokens with item or slice notation::

    >>> print(tree[2])
    <Token 'with' at 11:15 (Text)>

Besides that, Context has a ``pos`` and ``end`` attribute, which
refer to the ``pos`` value of the first Token in the context, and the ``end``
value of the last Token in the context (or a sub-context).

Node — traversing the tree structure
------------------------------------

Both Token and Context have a ``parent`` atribute that points to its parent
Context. Only for the root context, ``parent`` is ``None``.

Token and Context both inherit from ``NodeMixin``, which defines a lot of
useful methods to traverse tree structure.



Finding Tokens based on position
--------------------------------



Querying the tree structure
---------------------------


