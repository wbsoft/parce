Getting started
===============

We describe how ``parce`` works by creating a language definition and using it.
Start with::

    import parce

or::

    from parce import *

The latter way of importing is easier to use when defining your own language.

Defining your own language
--------------------------

A language is simply a class with no other behaviour than that it groups
lexicons. A lexicon is a set of rules describing what to look for in text.
We define a simple language to get started::

    import re

    class Nonsense(Language):
        @lexicon
        def root(cls):
            yield r'\d+', Number
            yield r'\w+', Text
            yield r'"', String, cls.string
            yield r'%', Comment, cls.comment
            yield r'[.,:?!]', Delimiter

        @lexicon
        def string(cls):
            yield r'"', String, -1
            yield default_action, String

        @lexicon(re_flags=re.MULTILINE)
        def comment(cls):
            yield r'$', Comment, -1
            yield default_action, Comment

``Language``, ``Text``, ``Number``, ``String``, ``Comment`` and ``lexicon`` are
objects imported from parce. ``Language`` is a class currently doing nothing
but may get some behaviour in the future. ``Text``, ``Number``, ``String``, and
``Comment`` are so-called standard actions. Just objects that describe the type
of the matched text. Standard actions have no behaviour and are essentially
singleton objects using virtually no memory.

The ``lexicon`` decorator makes a function into a ``BoundLexicon`` object, which
encapsulates the parsing of text using the rules supplied in the function.

When parsing starts for the first time, the function is called to get the
rules. Each rule consists of two or more parts: First the *pattern*, then the
*action*, and optionally one or more *targets*. A target is either a reference
to another lexicon, or a number like 1 or -1. Another lexicon is pushed onto
the stack, and a number like -1 is used to pop the lexicon off the stack, so
that the previous lexicon takes over parsing again.

Parsing text using our language
-------------------------------

Now, we use this language to parse some text::

    >>> text = '''
    ... Some text with 3 numbers and 1 "string inside
    ... over multiple lines", and 1 % comment that
    ... ends on a newline.
    ... '''

To parse text, we need to give ``parce`` the lexicon to start with. This is
called the *root lexicon*. To parse the text and get the results, we
call the ``root()`` function of ``parce``::

    >>> tree = root(Nonsense.root, text)

The root lexicon in this case is ``Nonsense.root``, although the name of the
lexicon does not matter at all. But naming the root lexicon ``root`` is
probably a good convention. Let's ``dump()`` the tree to look what's inside!::

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
    >>>

We see that the returned object is a ``Context`` containing ``Token`` and other
``Context`` instances. A Context is just a Python list, containing the tokens
that a lexicon generated. A Token is a light-weight object knowing its text,
position and the action that was specified in the rule.

Note that is is not needed at all to use the predefined actions of parce in
your language definition; you can specify any object you want, including
strings or methods!

This tree structure is what ``parce`` provides. You can find tokens on position::

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
     ├╴<Token 'string inside\nover multiple '... at 33:66 (Literal.String)>
     ╰╴<Token '"' at 66:67 (Literal.String)>

Note that anything you do not look for in your lexicon is simply ignored.
But the special rule with ``default_action`` matches everything not captured
by another rule.

