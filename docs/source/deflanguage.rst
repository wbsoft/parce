Anatomy of a Language
=====================

In this chapter we'll cover all the details of how a language can be defined.

To ``parce``, a :class:`~parce.language.Language` is currently just a grouping
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

    ``r'\d+'``
        matches one or more decimal digits (0 - 9)
    ``r'\w+'``
        matches one or more "word" characters (i.e. non-whitespace,
        non-puctuation)

See for more information about regular expressions the documentation
of the Python :mod:`re` module.

When using a Pattern instance, `parce` obtains the regular expression by
calling its :meth:`~parce.pattern.Pattern.build` method. You can use a Pattern
object where manually writing a regular expression is too tedious.

There are convenient functions for creating some types of Pattern instances:

    .. autofunction:: parce.words
        :noindex:

    .. autofunction:: parce.char
        :noindex:

See for more information about Pattern objects the documentation of the
:mod:`~parce.pattern` module.


The action
----------

The second item in a normal rule is the action. This can be any object, as
``parce`` does not do anything special with it. You can provide a number,
a string, a method, whatever.

There are, however, two action types provided by `parce`:

1. a standard action type. A standard action looks like ``String``, etc. and
   is a singleton object that is either created using the
   :class:`~parce.action.StandardAction` class or by accessing a nonexistent
   attribute of an existing standard action. This concept is borrowed of the
   `pygments` module. A standard action defined in the latter way can be seen as
   a "child" of the action it was created from.

   A standard action always creates one Token from the pattern's match (if the
   match contained text).

   Language definitions included in `parce` use these standard actions.
   A list of pre-defined standard actions is in the :mod:`parce` module.

2. the :class:`~parce.action.DynamicAction` class. These actions are created
   dynamically when a rule's pattern has matched, and they can create zero or
   more Token instances with action based on the match object or text.

   There are a few convenient functions to create dynamic actions:

    .. autofunction:: parce.bygroup
        :noindex:

    .. autofunction:: parce.bymatch
        :noindex:

    .. autofunction:: parce.bytext
        :noindex:

(You might wonder why the predicate functions would not directly return the
action. This is done to be able to know all actions beforehand, and to be
able to translate actions using a mapping before parsing, and not each time
when parsing a document. So the actions are not hardwired even if they appear
verbatim in the lexicon's rules.)

There also exists a special DynamicAction in the ``skip`` object, it's an
instance of :class:`~parce.action.SkipAction` and it yields no actions, so in
effect creating no Tokens. Use it if you want to match text, but do not need
the tokens.

See for more information the documentation of the :mod:`~parce.action` module.


The target
----------

Third and following items in a normal rule are zero or more targets.
A target causes the parser to switch to another lexicon, and thereby
causes a new Context to be created for that lexicon.

In a rule, a target is specified using zero or more items after the pattern
and the action of the rule.

When a target list is non-empty, the targets contained therein are processed
as follows:

* if a single target is a lexicon, that lexicon is pushed on the stack
  and parsing continues there.

* if a single target is a positive integer, the current lexicon is pushed
  that many times onto the stack. and parsing continues.

* if a single target is a negative integer, that many lexicons are popped
  off the stack, and parsing continues in a previous lexicon, adding tokens
  to a Context that already exists. The root context is never popped of the
  stack.

Instead of a target list, one DynamicTarget may be specified. This computes
the target list based on the regular expression's match object. There is one
convenience function:

    .. autofunction:: parce.tomatch
     :noindex:

A target is always executed after adding the token(s) that were generated to
the current context. The newly created context can be seen as the "target" of
the token that switched to it. If the match object did not contain actual
text, no Token is generated, but the target *is* handled of course.

See for more information the documentation of the :mod:`~parce.target` module.


Special rules
-------------

There are currently two special rules, i.e. that do not provide a pattern
to match, but induce other behaviour:

1.  The ``default_action`` rule, which causes a token to be generated using
    the specified action for text that would otherwise not be matched by
    any of the lexicon's rules. It can be seen in action in the above
    example.

2.  The ``default_target`` rule, which defines the target to choose when
    none of the normal rules match. This can be seen as a "fallthrough"
    possibility to check for some text, but just go one somewhere else
    in case the text is not there.


Lexicon parameters
------------------

The :attr:`@lexicon <parce.lexicon>` decorator optionally accepts arguments.
Currently one argument is supported:

    ``re_flags``, to set the regular expression flags for the pattern
        the lexicon will create.

See for more information the documentation of the :mod:`~parce.lexicon`
module.


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

* Targets should be valid, either integers or lexicons; and when
  a DynamicTarget is used, there should not be other target items

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

