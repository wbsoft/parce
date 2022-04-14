Anatomy of a Language
=====================

In this chapter we'll cover all the details of how a language can be defined.

A language definition is a class definition that inherits the
:class:`~parce.language.Language` class. Such a language class is never used to
instantiate objects, but rather the class itself is the language definition,
and acts like a grouping container for lexicons, which group rules, and rules
consist of a pattern, an action and zero or more targets.

New language definitions can be created by inheriting from existing ones, see
for example the bundled :class:`~parce.lang.html.Html` language class, which
extends :class:`~parce.lang.html.XHtml`, which builds upon
:class:`~parce.lang.xml.Xml`.

Let's look closer again at the example from the :doc:`gettingstarted` section::


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


The :attr:`@lexicon <parce.lexicon.lexicon>` decorated methods behave like
classmethods, i.e. when the lexicon is accessed for the first time, it calls
the method with the current Language class as the ``cls`` argument. So the
rules are able to in their target point to other lexicons of the same class.
This makes inheriting and re-implementing just one or a few lexicons very easy.
Of course a target may also point to a lexicon from a *different* language
class, in case you need to switch languages.

It is a convention that the lexicon method returns a generator yielding the
rules, but you can return any iterable containing the rules.


The pattern
-----------

The first item in a normal rule is the pattern, which is a string containing a
regular expression, or a function call or dynamic rule item that creates a
regular expression. Some simple regular expressions can be seen in the ``root``
lexicon of the above example:

:regexp:`\\d+`
    matches one or more decimal digits (0 - 9)
:regexp:`\\w+`
    matches one or more "word" characters (i.e. non-whitespace,
    non-puctuation)

It is a good convention to wrap regular expressions in a raw (``r`` prefixed)
string. See for more information about regular expressions the documentation of
the Python :mod:`re` module.

Python's regular expression engine picks the first pattern that matches, even
if a later rule would produce a longer match. So if you for example want to
look for keywords such as ``else`` and ``elseif``, be sure to either put the
longer one first, or use a boundary matching sequence such as ``\b``.

See below for more information about helper functions and dynamic rule items
that create a regular expression.


The action
----------

The second item in a normal rule is the action. This can be any object, as
*parce* does not do anything special with it. You can provide a number,
a string, a method, whatever.

There are, however, two action types provided by *parce*:

1. a standard action type. A standard action looks like ``String``, etc. and
   is a singleton object that is either created using the
   :class:`~parce.standardaction.StandardAction` class or by accessing a
   nonexistent attribute of an existing standard action. This concept is
   borrowed from the `pygments` module. A standard action defined in the latter
   way can be seen as a "child" of the action it was created from.

   A standard action always creates one Token from the pattern's match (if the
   match contained text).

   Language definitions included in *parce* use these standard actions.
   For the list of pre-defined standard actions see :doc:`action`.

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
  to a Context that already exists. The root context is never popped off the
  stack.

* an integer target ``0`` is allowed and is essentially a no-op, it does
  nothing.

Actions and targets share a mechanism to choose them dynamically based on the
matched text. See for more information below under `Dynamic actions and
targets`_.

A target is normally executed after adding the token(s) that were generated to
the current context. Only if the target lexicon has the ``consume`` attribute
set to True, the generated tokens are added to the newly generated context, see
`Lexicon parameters`_.

The newly created context can be seen as the "target" of the token that
switched to it. If the match object did not contain actual text, no token is
generated, but the target *is* handled of course.


Special rules
-------------

There are two special rules, i.e. that do not provide a pattern to match, but
induce other behaviour:

1.  The ``default_action`` rule, which causes a token to be generated using
    the specified action for text that would otherwise not be matched by
    any of the lexicon's rules. It can be seen in action in the above
    example. The default action can also be a dynamic action that chooses
    the action based on the text (see below).

2.  The ``default_target`` rule, which defines the target to choose when
    none of the normal rules match. This can be seen as a "fallthrough"
    possibility to check for some text, but just go on somewhere else in case
    the text is not there.

    An example::

        from parce import *
        from parce.action import Number, Text

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
    whitespace (see below for more information about the ``'skip'`` action),
    but pops back to ``root`` on any other text.


Dynamic patterns
----------------

When manually writing a regular expression is too difficult or cumbersome, you
can use a helper function or a dynamic rule item to construct it.

All dynamic helper functions and rule items are in the :mod:`~parce.rule`
module. If you want to use those, you can safely::

    from parce.rule import *    # or specify the names you want to use

There are two convenient functions for creating some types of regular
expressions:

.. autofunction:: parce.rule.words
    :noindex:

.. autofunction:: parce.rule.chars
    :noindex:

It is also possible to use dynamic rule items to create a regular expression
pattern, see below.

.. note::
    When a dynamic pattern evaluates to None, the rule is ignored.


Dynamic actions and targets
---------------------------

After the pattern, one action and zero or more target items are expected to be
in a normal rule. When you put items in a rule that inherit from
:class:`~parce.ruleitem.RuleItem`, those are evaluated when the rule's pattern
matches. Dynamic rule items enable you to take decisions based on the match
object or the matched text. Most rule items do this by choosing the replacement
from a list, based on the output of a predicate function.

The replacement can be an action or a target. When the replacement is a list or
tuple, it is unrolled, so one dynamic rule item can yield multiple items, for
example an action and a target. Dynamic items can be nested.

The building blocks for dynamic rule items are explained in the documentation
of the :mod:`~parce.rule` module. Often you'll use a combination of the
:func:`~parce.rule.call` and :func:`~parce.rule.select` items, and the variable
placeholders :obj:`~parce.rule.TEXT` and :obj:`~parce.rule.MATCH`.

Using ``call(predicate, TEXT)`` you can arrange for a predicate to be called
with the matched text, and using ``select(value, *items)`` you can use an
integer value to select one of the supplied items.

(You might wonder why the predicate function cannot directly return the action
or target(s). This is done to be able to know all actions and/or targets
beforehand, and to be able to translate actions using a mapping before parsing,
and not each time when parsing a document. So the actions are not hardwired
even if they appear verbatim in the lexicon's rules.)

These are the basic four building block items:

.. autodata:: parce.rule.TEXT
    :noindex:

.. autodata:: parce.rule.MATCH
    :noindex:

.. autofunction:: parce.rule.call
    :noindex:

.. autofunction:: parce.rule.select
    :noindex:

Of these four, only ``select`` can be used directly in a rule. There are many
helper functions that build on this base, see the documentation of the
:mod:`~parce.rule` module.


Dynamic actions
---------------

Besides the general dynamic rule items, there is a special category of dynamic
actions, which only create actions, and in this way influence the number of
tokens generated from a single regular expression match.

The function :func:`~parce.rule.bygroup` can be used to yield zero or more actions,
yielding a token for every non-empty match in a group:

.. autofunction:: parce.rule.bygroup
    :noindex:

The function :func:`~parce.rule.using` can be used to lex the matched text with
another lexicon:

.. autofunction:: parce.rule.using
    :noindex:

Finally, there exists a special :class:`~parce.ruleitem.ActionItem` in the
:obj:`~parce.skip` object, it's an instance of
:class:`~parce.ruleitem.SkipAction` and it yields no actions, so in effect
creating no tokens. Use it if you want to match text, but do not need the
tokens. See for more information the documentation of the
:mod:`~parce.rule` module.


Lexicon parameters
------------------

The :attr:`@lexicon <parce.lexicon.lexicon>` decorator optionally accepts
arguments. Currently two arguments are supported:

``re_flags`` (0):
    to set the regular expression flags for the pattern the lexicon will
    create. See for all possible regular expression flags the documentation of
    the Python :mod:`re` module.

``consume`` (False):
    if set to True, tokens generated from the rule that pushed this
    lexicon are added to the newly created Context instead of the current.
    For example::

        class MyLang(Language):
            @lexicon
            def root(cls):
                yield '"', String, cls.string

            @lexicon(consume=True)
            def string(cls):
                yield '"', String, -1
                yield default_action, String

    This language definition generates this tree structure::

        >>> root(MyLang.root, '  "a string"  ').dump()
        <Context MyLang.root at 2-12 (1 child)>
         ╰╴<Context MyLang.string at 2-12 (3 children)>
            ├╴<Token '"' at 2:3 (Literal.String)>
            ├╴<Token 'a string' at 3:11 (Literal.String)>
            ╰╴<Token '"' at 11:12 (Literal.String)>

    Without the ``consume`` argument, the tree would have looked like this::

        <Context MyLang.root at 2-12 (2 children)>
         ├╴<Token '"' at 2:3 (Literal.String)>
         ╰╴<Context MyLang.string at 3-12 (2 children)>
            ├╴<Token 'a string' at 3:11 (Literal.String)>
            ╰╴<Token '"' at 11:12 (Literal.String)>

    Adding the tokens that switched context to the target context of a lexicon
    that has ``consume`` set to True only happens when that lexicon is pushed,
    not when the context is reached via "pop".

See for more information :doc:`lexicon`.


The Lexicon argument
--------------------

Although the lexicon function itself never uses any more arguments than
the first ``cls`` argument, it is possible to call an existing Lexicon with
an argument, which then must be a simple hashable item like an integer, string
or standard action. In most use cases it will be a string value.

Calling a Lexicon with such an argument creates a *derived Lexicon*, which
behaves just as the normal Lexicon, but which has the specified argument in the
``arg`` attribute. The derived Lexicon is cached as well.

It is then possible to access the argument using the :obj:`~parce.rule.ARG`
variable. This way it is possible to change anything in a rule based on the
argument of the derived lexicon. An example, taken from the tests directory::

    from parce import Language, lexicon, root
    from parce.action import Name, Text
    from parce.rule import arg, derive, MATCH

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r"@([a-z]+)@", Name, derive(cls.here, MATCH[1])
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

What happens: the :func:`~parce.rule.derive` helper switches to the ``here``
lexicon when the text ``@mark@`` is encountered. The part ``mark`` is captured
in the match group 1, and given as argument to the ``here`` lexicon. The
:func:`~parce.rule.arg` parce built-in yields the argument (``"mark"``) as a regular
expression pattern, with word boundaries, which causes the lexer to pop back to
the root context.

Note that the asterisk after the ``here`` lexicon name in the dump reveals that
it is a derived Lexicon.

(Why didn't we simply use arguments to the Lexicon function itself? This isn't
done because then we could simply hide rules with ``if``-constructs, but that
would obfuscate the possibility to access all rule items, actions and targets
etcetera beforehand, before parsing, which would break all language validation
possibilities and future logic to replace items in rules before parsing.)

There are three helper functions that create the Pattern based on the contents
of the lexicon argument:

.. autofunction:: parce.rule.pattern
    :noindex:

.. autofunction:: parce.rule.arg
    :noindex:

.. autofunction:: parce.rule.ifarg
    :noindex:

There is one helper function that creates a target lexicon using an
argument:

.. autofunction:: parce.rule.derive
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


Maintaining state using a derived Lexicon
-----------------------------------------

Although *parce* is essentially state-free (it can start its reparsing
anywhere, and all information is there), we can maintain state in the hashable
lexicon argument, e.g. by using a tuple or a frozen set.

The following example stores a set of "known" words (they have been "defined"
in this purely fictional language by prefixing them with a ``@``) which then
are recognized and get the action ``Name.Constant``. And defining them again
will be recognized as invalid!

Let's store the list of known words in a tuple. After importing necessary
stuff, we write two helper functions: one to create a new ``words`` tuple with
the added word, and the other to test for the presence of a word in the tuple::

    from parce import Language, lexicon, root
    from parce.action import Name
    from parce.rule import call, derive, select, ARG, MATCH, TEXT

    def add(words, text):
        """Return a new tuple with text added."""
        new = (text,)
        return words + new if words else new

    def ifknown(text, yes_value, no_value):
        """Return a dynamic rule item returning ``yes_value`` for known ``text``, otherwise ``no_value``."""
        known = lambda text, words: text in words if words else False
        return select(call(known, text, ARG), no_value, yes_value)

Initially, the lexicon argument is ``None``, so we do not add or test
membership if the ``words`` value itself evaluates to False. Now let's write
the language definition::

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r"@(\w+)", ifknown(MATCH[1], Name.Definition.Invalid,
                (Name.Definition, -1, derive(cls.root, call(add, ARG, MATCH[1]))))
            yield r"\w+", ifknown(TEXT, Name.Constant, Name.Variable)

There are two rules: to find a ``@``-prefixed word, or a normal word. If a
``@``-prefixed word is encountered for the first time, it is added to the
lexicon's argument; the current lexicon is popped and derived with the new
argument (the outermost lexicon is never popped off). If it's already known, it
gets the ``Invalid`` action mixed in.

If a normal word is encountered, it gets the ``Name.Constant`` action if known,
else ``Name.Variable``.

Let's test!

::

    >>> text = "bls lhrt sdf @wer gfdh wer iuj @sdf uhj sdf bls @bls bls @sdf @bls"
    >>> tree = root(MyLang.root, text)
    >>> tree.dump()
    <Context MyLang.root at 0-66 (7 children)>
     ├╴<Token 'bls' at 0:3 (Name.Variable)>
     ├╴<Token 'lhrt' at 4:8 (Name.Variable)>
     ├╴<Token 'sdf' at 9:12 (Name.Variable)>
     ├╴<Token '@wer' at 13:17 (Name.Definition)>
     ├╴<Context MyLang.root* at 18-35 (4 children)>
     │  ├╴<Token 'gfdh' at 18:22 (Name.Variable)>
     │  ├╴<Token 'wer' at 23:26 (Name.Constant)>
     │  ├╴<Token 'iuj' at 27:30 (Name.Variable)>
     │  ╰╴<Token '@sdf' at 31:35 (Name.Definition)>
     ├╴<Context MyLang.root* at 36-52 (4 children)>
     │  ├╴<Token 'uhj' at 36:39 (Name.Variable)>
     │  ├╴<Token 'sdf' at 40:43 (Name.Constant)>
     │  ├╴<Token 'bls' at 44:47 (Name.Variable)>
     │  ╰╴<Token '@bls' at 48:52 (Name.Definition)>
     ╰╴<Context MyLang.root* at 53-66 (3 children)>
        ├╴<Token 'bls' at 53:56 (Name.Constant)>
        ├╴<Token '@sdf' at 57:61 (Name.Definition.Invalid)>
        ╰╴<Token '@bls' at 62:66 (Name.Definition.Invalid)>

We can find the list of words that's known at any moment in the lexicon's
argument::

    >>> tree[6].lexicon.arg
    ('wer', 'sdf', 'bls')


Validating a Language
---------------------

The `validate` module provides a tool to check whether a language definition
should work correctly. By calling::

    from parce.validate import validate_language
    validate_language(MyLang)

it checks all the lexicons in the language. The following checks are
performed:

* A lexicon may only have one special rule, i.e. ``default_action`` or
  ``default_target``, not both or more than one of them

* The regular expression patterns should be valid and compilable

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

