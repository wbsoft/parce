Getting started
===============

We describe how *parce* works by creating a language definition and using it.
Start with::

    import parce

or::

    from parce import *

The first way is recommended;
the latter way of importing is easier to use when defining your own language.

Defining your own language
--------------------------

A language is simply a class with no other behaviour than that it groups
lexicons. A lexicon is a set of rules describing what to look for in text.
We define a simple language to get started::

    import re

    from parce import *
    import parce.action as a    # use the standard actions

    class Nonsense(Language):
        @lexicon
        def root(cls):
            yield r'\d+', a.Number
            yield r'\w+', a.Text
            yield r'"', a.String, cls.string
            yield r'%', a.Comment, cls.comment
            yield r'[.,:?!]', a.Delimiter

        @lexicon
        def string(cls):
            yield r'"', a.String, -1
            yield default_action, a.String

        @lexicon(re_flags=re.MULTILINE)
        def comment(cls):
            yield r'$', a.Comment, -1
            yield default_action, a.Comment

``Language`` and ``lexicon``, are objects imported from *parce*. ``Language``
is the base class for all language definitions. ``Text``, ``Number``,
``String``, ``Delimiter`` and ``Comment`` are so-called standard actions.
Standard actions are simple named objects that identify the type of the matched
text. They have no behaviour and are essentially singleton objects using
virtually no memory.

The ``lexicon`` decorator makes a function into a ``Lexicon`` object, which
encapsulates the parsing of text using the rules supplied in the function.

When parsing starts for the first time, the function is called to get the
rules. Each rule consists of two or more parts: First the *pattern*, then the
*action*, and optionally one or more *targets*. A target is either a reference
to another lexicon, or a number like 1 or -1. Another lexicon is pushed onto
the stack, and a number like -1 is used to pop the lexicon off the stack, so
that the previous lexicon takes over parsing again.

Parsing text using our language
-------------------------------

Now, we use this language definition to parse some text::

    >>> text = '''
    ... Some text with 3 numbers and 1 "string inside
    ... over multiple lines", and 1 % comment that
    ... ends on a newline.
    ... '''

To parse text, we need to give *parce* the lexicon to start with. This is
called the *root lexicon*. To parse the text and get the results, we
call the ``root()`` function of *parce*::

    >>> tree = root(Nonsense.root, text)

The root lexicon in this case is ``Nonsense.root``, although the name of the
lexicon does not matter at all. But naming the root lexicon ``root`` is
probably a good convention. Let's ``dump()`` the tree to look what's inside!

::

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
     │  ├╴<Token 'string insid...ultiple lines' at 33:66 (Literal.String)>
     │  ╰╴<Token '"' at 66:67 (Literal.String)>
     ├╴<Token ',' at 67:68 (Delimiter)>
     ├╴<Token 'and' at 69:72 (Text)>
     ├╴<Token '1' at 73:74 (Literal.Number)>
     ├╴<Token '%' at 75:76 (Comment)>
     ├╴<Context Nonsense.comment at 76-89 (1 child)>
     │  ╰╴<Token ' comment that' at 76:89 (Comment)>
     ├╴<Token 'ends' at 90:94 (Text)>
     ├╴<Token 'on' at 95:97 (Text)>
     ├╴<Token 'a' at 98:99 (Text)>
     ├╴<Token 'newline' at 100:107 (Text)>
     ╰╴<Token '.' at 107:108 (Delimiter)>
    >>>


We see that the returned object is a ``Context`` containing ``Token`` and other
``Context`` instances. A Context is just a Python list, containing the tokens
that a lexicon generated. A Token is a light-weight object knowing its text,
position and the action that was specified in the rule.

Note that anything you do not look for in your lexicons (in this case most
whitespace for example) is simply ignored. But the special rule with
``default_action`` matches everything not captured by another rule.

This tree structure is what *parce* provides. You can find tokens on position::

    >>> tree.find_token(27)     # finds token at position 27
    <Token 'and' at 26:29 (Text)>

You can also search for text, or certain actions or lexicons. Both Token and
Context have a ``query`` property that unleashes these powers::

    >>> tree.query.all("and").list()
    [<Token 'and' at 26:29 (Text)>, <Token 'and' at 69:72 (Text)>]
    >>> tree.query.all.action(Comment).list()
    [<Token '%' at 75:76 (Comment)>, <Token ' comment that' at 76:89 (Comment)>]
    >>> tree.query.all.action(Number).count()
    3
    >>> tree.query.all(Nonsense.string).dump()
    <Context Nonsense.string at 33-67 (2 children)>
     ├╴<Token 'string insid...ultiple lines' at 33:66 (Literal.String)>
     ╰╴<Token '"' at 66:67 (Literal.String)>

See the :mod:`~parce.query` module for more information.

.. note::

    Is is not needed at all to use the predefined actions of parce in your
    language definition; you can specify any object you want, including strings
    or methods.

If you want, you can also get a flat stream of events describing the parsing
process. Events are simply named tuples consisting of a ``target`` and
``lexemes`` tuples. It is what *parce* internally uses to build the tree
structure::

    >>> for e in events(Nonsense.root, text):
    ...     print(e)
    ...
    Event(target=None, lexemes=((1, 'Some', Text),))
    Event(target=None, lexemes=((6, 'text', Text),))
    Event(target=None, lexemes=((11, 'with', Text),))
    Event(target=None, lexemes=((16, '3', Literal.Number),))
    Event(target=None, lexemes=((18, 'numbers', Text),))
    Event(target=None, lexemes=((26, 'and', Text),))
    Event(target=None, lexemes=((30, '1', Literal.Number),))
    Event(target=None, lexemes=((32, '"', Literal.String),))
    Event(target=Target(pop=0, push=[Nonsense.string]), lexemes=((33, 'string inside\nover multiple lines', Literal.String),))
    Event(target=None, lexemes=((66, '"', Literal.String),))
    Event(target=Target(pop=-1, push=[]), lexemes=((67, ',', Delimiter),))
    Event(target=None, lexemes=((69, 'and', Text),))
    Event(target=None, lexemes=((73, '1', Literal.Number),))
    Event(target=None, lexemes=((75, '%', Comment),))
    Event(target=Target(pop=0, push=[Nonsense.comment]), lexemes=((76, ' comment that', Comment),))
    Event(target=Target(pop=-1, push=[]), lexemes=((90, 'ends', Text),))
    Event(target=None, lexemes=((95, 'on', Text),))
    Event(target=None, lexemes=((98, 'a', Text),))
    Event(target=None, lexemes=((100, 'newline', Text),))
    Event(target=None, lexemes=((107, '.', Delimiter),))

More information about the events stream can be found in the documentation
of the :mod:`~parce.lexer` module.
