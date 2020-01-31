Anatomy of a Language
=====================

In this chapter we'll cover all the details of how a language can be defined.

To ``parce``, a Language is currently just a grouping container for lexicons,
which group rules, and rules consist of a pattern, an action and zero or more
targets.

Let's look closer again at the example from the Getting started section::


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


The ``@lexicon`` decorated methods behave like classmethods, i.e. when you
call the method through the class definition, it yields the rules, and the
code yielding the rules knows the current Language class via the ``cls``
argument. So the rules are able to in their target point to other lexicons of
the same class. This makes inheriting and re-implementing just one or a few
lexicons very easy. Of course a target may also point to a lexicon from a
*different* language class, in case you need to switch languages.

The pattern
-----------

The first item in a normal rule is the pattern, which is either a string
containing a regular expression, or an object inheriting from
``pattern.Pattern``. In that case, the regular expression is obtained by
calling the ``build()`` method of the pattern. You use a Pattern object where
manually writing a regular expression is too tedious.

There are convenient functions for creating some types of Pattern instances:

 * ``words(long_list_of_words)`` creates an optimized regular expression
   matching any of the words contained in the ``long_list_of_words``.

 * ``char(string)`` creates an optimized regular expression matching any one
   of the characters contained in the string. To make an expression matching
   any character that is *not* in the string, use ``char(string, False)``.

See for more information about regular expressions the documentation
of the :doc:`Python re module <python:library/re>`.

See for more information about ``Pattern`` objects the documentation of the
:doc:`pattern <pattern>` module.

The action
----------

The second item in a normal rule is the action. This can be any object, as
``parce`` does not do anything special with it. You can provide a number,
a string, a method, whatever.

There are, however, two action types provided by ``parce``:

1. a standard action type. A standard action looks like ``String``, etc. and
   is a singleton object that is either created using the
   ``action.StandardAction()`` class or by accessing a nonexistent attribute
   of an exisiting standard action. This concept is borrowed of the pygments
   module. A standard action defined in the latter way can be seen as a "child"
   of the action it was created from.

   A standard action always creates one Token from the pattern's match (if the
   match contained text).

   Language definitions included in ``parce`` use these standard actions.

2. the ``DynamicAction`` class. These actions are created dynamically when
   a rule's pattern has matched, and they can create zero or more Token
   instances with action based on the match object or text.

   There are a few convenient functions to create dynamic actions:

   * ``bygroup(Act1, Act2, ...)`` uses capturing subgroups in the regular
       expression pattern and creates a Token for every subgroup, with that
       action. You should provide the same number of actions as there are
       capturing subgroups in the pattern. Use non-capturing subgroups for
       the parts you're not interested in, or the special ``skip`` action
       (see below).

   * ``bymatch(predicate, Act1, Act2, ...)`` calls the predicate function
       with the match object as argument. The function should return the
       index of the action to choose. If you provide two possible actions,
       the predicate function may also return ``True`` or ``False``, in which
       case ``True`` chooses the second action and ``False`` the first.

   * ``bytext(predicate, Act1, Act2, ...)`` calls the predicate function
       with the matched text as argument.  The function should return the
       index of the action to choose, in the same way as with ``bymatch()``.

(You might wonder why the predicate functions would not directly return the
action. This is done to be able to know all actions beforehand, and to be
able to translate actions using a mapping before parsing, and not each time
when parsing a document. So the actions are not hardwired even if they appear
verbatim in the lexicon's rules.)

There also exists a special DynamicAction in the ``skip`` object, it's an
instance of ``SkipAction`` and it yields no actions, so in effect creating no
Tokens. Use it if you want to match text, but do not need the tokens.

See for more information the documentation of the :doc:`action <action>` module.


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
convenience function: ``tomatch(predicate, Targetlist1, TargetList2, ..)``
that works in the same was as the dynamic action objects. A "``Targetlist``"
may also be a single target such as ``-1`` or ``cls.something``.

A target is always executed after adding the token(s) that were generated to
the current context. The newly created context can be seen as the "target" of
the token that switched to it. If the match object did not contain actual
text, no Token is generated, but the target *is* handled of course.

See for more information the documentation of the :doc:`target <target>`
module.


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

The ``@lexicon`` decorator optionally accepts arguments. Currently one
argument is supported:

*  ``re_flags``, to set the regular expression flags for the pattern
     the lexicon will create.

See for more information the documentation of the :doc:`lexicon <lexicon>`
module.

