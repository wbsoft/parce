Anatomy of a Language
=====================

In this chapter we'll cover all the details of how a language can be defined.

To ``parce``, a :class:`~parce.language.Language` is simply a grouping
container for lexicons, which group rules, and rules consist of a pattern, an
action and zero or more targets.

Let's look closer again at the example from the :doc:`gettingstarted` section::


    import re
    from parce import *

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


The :attr:`@lexicon <parce.lexicon>` decorated methods behave like
classmethods, i.e. when you call the method through the class definition, it
yields the rules, and the code yielding the rules knows the current Language
class via the ``cls`` argument. So the rules are able to in their target point
to other lexicons of the same class. This makes inheriting and re-implementing
just one or a few lexicons very easy. Of course a target may also point to a
lexicon from a *different* language class, in case you need to switch
languages.


The pattern
-----------

The first item in a normal rule is the pattern, which is either a string
containing a regular expression, or an object inheriting from
:class:`~parce.pattern.Pattern`. Some simple regular expressions can be seen
in the ``root`` lexicon of the above example:

    :regexp:`\d+`
        matches one or more decimal digits (0 - 9)
    :regexp:`\w+`
        matches one or more "word" characters (i.e. non-whitespace,
        non-puctuation)

It is a good convention to wrap a regular expressions in a raw (``r`` prefixed)
string. See for more information about regular expressions the documentation of
the Python :mod:`re` module.

Python's regular expression engine picks the first pattern that matches, even
if a later rule would produce a longer match. So if you for example want to
look for keywords such as ``else`` and ``elseif``, be sure to either put the
longer one first, or use a boundary matching sequence such as ``\b``.

When using a Pattern instance, `parce` obtains the regular expression by
calling its :meth:`~parce.pattern.Pattern.build` method, which only happens one
time, when the lexicon is first used for parsing. You can use a Pattern object
where manually writing a regular expression is too tedious. More information
below under `Dynamic patterns`_.


The action
----------

The second item in a normal rule is the action. This can be any object, as
``parce`` does not do anything special with it. You can provide a number,
a string, a method, whatever.

There are, however, two action types provided by `parce`:

1. a standard action type. A standard action looks like ``String``, etc. and
   is a singleton object that is either created using the
   :class:`~parce.action.StandardAction` class or by accessing a nonexistent
   attribute of an existing standard action. This concept is borrowed from the
   `pygments` module. A standard action defined in the latter way can be seen as
   a "child" of the action it was created from.

   A standard action always creates one Token from the pattern's match (if the
   match contained text).

   Language definitions included in `parce` use these standard actions.
   For a list of pre-defined standard actions see :doc:`stdactions`.

2. Dynamic actions. These actions are created dynamically when a rule's
   pattern has matched, and they can create zero or more Token instances with
   action based on the match object or text. See for more information below under
   `Dynamic actions and targets`_.


The target
----------

Third and following items in a normal rule are zero or more targets. A target
causes the parser to switch to another lexicon, thereby creating a new Context
for that lexicon.

When a target list is non-empty, the target items contained therein are
processed as follows:

* if a target is a lexicon, that lexicon is pushed on the stack
  and parsing continues there.

* if a target is a positive integer, the current lexicon is pushed
  that many times onto the stack, and parsing continues.

* if a target is a negative integer, that many lexicons are popped
  off the stack, and parsing continues in a previous lexicon, adding tokens
  to a Context that already exists. The root context is never popped of the
  stack.

Actions and targets share a mechanism to choose them dynamically based on the
matched text. See for more information below under `Dynamic actions and
targets`_.

A target is always executed after adding the token(s) that were generated to
the current context. The newly created context can be seen as the "target" of
the token that switched to it. If the match object did not contain actual
text, no token is generated, but the target *is* handled of course.


Special rules
-------------

There are currently two special rules, i.e. that do not provide a pattern
to match, but induce other behaviour:

1.  The ``default_action`` rule, which causes a token to be generated using
    the specified action for text that would otherwise not be matched by
    any of the lexicon's rules. It can be seen in action in the above
    example. The default action can also be a dynamic action that chooses
    the action based on the text (see below).

2.  The ``default_target`` rule, which defines the target to choose when
    none of the normal rules match. This can be seen as a "fallthrough"
    possibility to check for some text, but just go one somewhere else
    in case the text is not there.

    An example::

        class MyLang(Language):
            @lexicon
            def root(cls):
                yield r"\bnumbers:", Text, cls.numbers

            @lexicon
            def numbers(cls):
                """Collect numbers, skipping white space until something else is
                   encountered.
                """
                yield r"\d+", Number
                yield r"\s+", skip
                yield default_target, -1

    In this example, the text "``numbers:``" causes the parser to switch to the
    ``MyLang.numbers`` lexicon, which collects Number tokens and skips
    whitespace, but pops back to ``root`` on any other text.


Dynamic patterns
----------------

A Pattern instance can be used where manually writing a regular expression is
too difficult or cumbersome. You can also construct the regular expression in
your lexicon code body, just before yielding it, but the advantage of a Pattern
object is that is is only created when the lexicon is used for parsing for the
first time.

There are convenient functions for creating some types of Pattern instances:

.. autofunction:: parce.words
    :noindex:

.. autofunction:: parce.char
    :noindex:

See for more information about Pattern objects the documentation of the
:mod:`~parce.pattern` module.


Dynamic actions and targets
---------------------------

After the pattern, one action and zero or more target items are expected to be
in a normal rule. When you put items in a rule that inherit from
:class:`~parce.rule.DynamicItem`, those are replaced during parsing by the
lexicon, based on the match object or the matched text. This is done
by supplying a predicate function that chooses the replacement(s) from
given itemlists (lists or tuples which can contain zero or more items).

So one dynamic rule item can yield multiple items, for example an action and a
target. Dynamic items can be nested.

There are a few convenient functions to create dynamic actions and/or targets:

.. autofunction:: parce.bymatch
    :noindex:

.. autofunction:: parce.bytext
    :noindex:

(You might wonder why the predicate functions used by :func:`~parce.bymatch`
and :func:`~parce.bytext` would not directly return the action or target(s).
This is done to be able to know all actions and/or targets beforehand, and to
be able to translate actions using a mapping before parsing, and not each time
when parsing a document. So the actions are not hardwired even if they appear
verbatim in the lexicon's rules.)

The following functions all use the same mechanism under the hood, but they
also create the predicate function for you:

.. autofunction:: parce.ifgroup
    :noindex:

.. autofunction:: parce.ifmember
    :noindex:

.. autofunction:: parce.ifgroupmember
    :noindex:

.. autofunction:: parce.maptext
    :noindex:

.. autofunction:: parce.mapgroup
    :noindex:

.. autofunction:: parce.mapmember
    :noindex:

.. autofunction:: parce.mapgroupmember
    :noindex:

Instead of a list or tuple of items, a single action or target item can also be
given. These functions can also be used for mapping an action *and* target
based on the text or match object at the same time. So instead of::

    predicate = lambda m: m.group() in some_list
    yield "pattern", bymatch(predicate, action1, action2), bymatch(predicate, target1, target2)

you can write::

    predicate = lambda m: m.group() in some_list
    yield "pattern", bymatch(predicate, (action1, target1), (action2, target2))

which is more efficient, because the predicate is evaluated only once. See for
more information the documentation of the :mod:`~parce.rule` module.


Dynamic actions
---------------

Besides the general dynamic rule items, there is a special category of dynamic
actions, which only create actions, and in this way influence the number of
tokens generated from a single regular expression match.

The function :func:`~parce.bygroup` can be used to yield zero or more actions,
yielding a token for every non-empty match in a group:

.. autofunction:: parce.bygroup
    :noindex:

The function :func:`~parce.using` can be used to lex the matched text with
another lexicon:

.. autofunction:: parce.using
    :noindex:

Finally, there exists a special :class:`~parce.action.DynamicAction` in the
``skip`` object, it's an instance of :class:`~parce.action.SkipAction` and it
yields no actions, so in effect creating no tokens. Use it if you want to match
text, but do not need the tokens. See for more information the documentation of
the :mod:`~parce.action` module.


Lexicon parameters
------------------

The :attr:`@lexicon <parce.lexicon>` decorator optionally accepts arguments.
Currently one argument is supported:

    ``re_flags``, to set the regular expression flags for the pattern
        the lexicon will create.

See for more information the documentation of the :mod:`~parce.lexicon`
module.


Lexicon arguments, derived Lexicon
----------------------------------

Although the lexicon function itself never uses any more arguments than
the first ``cls`` argument, it is possible to call an existing Lexicon with
an argument, which then must be a simple hashable item like an integer, string
or standard action. In most use cases it will be a string value.

Calling a Lexicon with such an argument creates a derived Lexicon, which behaves
just as the normal Lexicon, but which has the specified argument in the ``arg``
attribute. The derived Lexicon is cached as well.

It is then possible to access the argument using :class:`~parce.rule.ArgItem`
objects. This way it is possible to change anything in a rule based on the
argument of the derived lexicon. An example, taken from the tests directory::

    from parce import *

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r"@([a-z]+)@", Name, withgroup(1, cls.here)
            yield r"\w+", Text

        @lexicon
        def here(cls):
            yield arg(prefix=r"\b", suffix=r"\b"), Name, -1
            yield r"\w+", Text


    text = """ text @mark@ bla bla mark bla bla """

    >>> tree = root(MyLang.root, text)
    >>> tree.dump()
    <Context MyLang.root at 1-33 (5 children)>
     ├╴<Token 'text' at 1:5 (Text)>
     ├╴<Token '@mark@' at 6:12 (Name)>
     ├╴<Context MyLang.here* at 13-25 (3 children)>
     │  ├╴<Token 'bla' at 13:16 (Text)>
     │  ├╴<Token 'bla' at 17:20 (Text)>
     │  ╰╴<Token 'mark' at 21:25 (Name)>
     ├╴<Token 'bla' at 26:29 (Text)>
     ╰╴<Token 'bla' at 30:33 (Text)>

What happens: the :func:`~parce.withgroup` helper switches to the ``here``
lexicon when the text ``@mark@`` is encountered. The part ``mark`` is captured
in the match group 1, and given as argument to the ``here`` lexicon. The
:func:`~parce.arg` parce built-in yields the argument (``"mark"``) as a regular
expression pattern, with word boundaries, which causes the lexer to pop back to
the root context.

Note that the asterisk after the ``here`` lexicon name in the dump reveals that
it is a derived Lexicon.

(Why didn't we simply use arguments to the Lexicon function itself? This isn't
done because then we could simply hide rules with ``if``-constructs, but that
would obfuscate the possibility to access all rule items, actions and targets
etcetera beforehand, before parsing, which would break all language validation
possibilities and future logic to replace items in rules before parsing.)

There are two helper functions that create the Pattern based on the contents
of the lexicon argument:

.. autofunction:: parce.arg
    :noindex:

.. autofunction:: parce.ifarg
    :noindex:

There are three helper functions that create a target lexicon using an
argument:

.. autofunction:: parce.withgroup
    :noindex:

.. autofunction:: parce.withtext
    :noindex:

.. autofunction:: parce.witharg
    :noindex:

And there is a helper function that calls a predicate with the lexicon argument
to choose rule items:

.. autofunction:: parce.byarg
    :noindex:

And a function that chooses rule items from a dictionary the lexicon argument
is looked up in:

.. autofunction:: parce.maparg
    :noindex:


Of course it is also possible to target a lexicon with an argument directly::

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r"\{", Delimiter, cls.nested("}")
            yield r"\[", Delimiter, cls.nested("]")
            yield r"\w+", Text

        @lexicon
        def nested(cls):
            yield arg(), Delimiter, -1
            yield from cls.root


Validating a Language
---------------------

If you are writing you own language definition, the `validate` module
provides a tool to check whether the definition should work correctly.
By calling::

    from parce.validate import validate_language
    validate_language(MyLang)

it checks all the lexicons in the language. The following checks are
performed:

* A lexicon may only have one special rule, i.e. ``default_action`` or
  ``default_target``, not both or more than one of them

* The regular expression pattern should be valid and compilable

* Targets should be valid, either integers or lexicons

* Circular default targets are detected.

  If the parser follows a default target multiple times without advancing the
  current position in the text, and then comes back in a lexicon we were
  before, there is a circular default target. (Circular targets can also
  happen with patterns that have an empty match).

  When the parser comes back in a lexicon context that already exists, the
  circular target is handled gracefully, and the parser just advances to the
  next position in the text::

    class MyLang(Language):
        @lexicon
        def lexicon1(cls):
            ...
            yield default_target, cls.lexicon2

        @lexicon
        def lexicon2(cls):
            ...
            yield default_target, -1    # pops back to lexicon1

  But the parser would run away when each target would create a *new* lexicon
  context, e.g. in the case of::

    # invalid circular default target example
    class MyLang(Language):
        @lexicon
        def lexicon1(cls):
            ...
            yield default_target, cls.lexicon2

        @lexicon
        def lexicon2(cls):
            ...
            yield default_target, cls.lexicon1 # creates a new context

  The validator recognizes this case and marks the error, so you can fix it.

