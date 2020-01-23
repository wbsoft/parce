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
the same class. This makes inheriting and re-implementing just one of a few
lexicons very easy.

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
  of the characters contained in the string. To make an expression *not*
  matching any of the characters in the string, use ``char(string, False)``.

See for more information the documentation of the pattern module.

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

2. the DynamicAction class. These actions are created dynamically when
   a rule's pattern has matched, and they can create zero or more Token
   instances with action based on the match object or text.

   There are a few convenient functions to create dynamic actions:

   * ``bygroup(Act1, Act2, ...)`` uses capturing subgroups in the regular
       expression pattern and creates a Token for every subgroup, with that
       action. You should provide the same number of actions as there are
       capturing subgroups in the pattern.

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

See for more information the documentation of the action module.


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

See for more information the documentation of the target module.


