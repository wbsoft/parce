The livelex Python module
=========================

This module is designed to parse text using rules, which are regular-expression
based. Rules are grouped into lexicons, and lexicons are grouped into a
Language object. Every lexicon has its own set of rules that describe the text
that is expected in that context.

A rule consists of three parts: a pattern, an action and a target.

* The pattern is a either a regular expression string, or an object that
  inherits Pattern. In that case its build() method is called to get the
  pattern.

* The action can be any object, and is streamed together with the matched part
  of the text. It can be seen as a token. If the action is an instance of
  Action, its filter_actions() method is called, which can yield zero or more
  tokens.  The special `skip` action skips the matching text.

* The target is a list of objects, which can be integer numbers or references
  to a different lexicon. A positive number pushes the same lexicon on the
  stack, while a negative number pops the current lexicon(s) off the stack, so
  that lexing the text continues with a previous lexicon. It is also possible
  to pop a lexicon and push a different one.

Using a special rule, a lexicon may specify a default action, which is
streamed with text that is not recognized by any other rule in the lexicon.
A lexicon may also specify a default target, which is chosen when no rule
matches the current text.

Here is a crude example of how to create a Language class and then use it:

.. code:: python

    from livelex import *


    class MyLang(Language):
        """A Language represents a set of Lexicons comprising a specific language.

        A Language is never instantiated. The class itself serves as a namespace
        and can be inherited from.



        """

        @lexicon(re_flags=0)
        def root(cls):
            yield Words(('bla', 'BLA')), 'bla action'
            yield r'ble', 'ble action'
            yield r'\s+', skip      # this text is skipped
            yield r'(bl)(ub)', Subgroup('bl act', 'ub act')
            yield r'blo', 'blo action', cls.blo
            yield default_action, "TEXT"

        @lexicon
        def blo(cls):
            yield r'\s+', skip      # this text is skipped
            yield r'1', '1 in blo'
            yield r'4', '4 in blo, end', -1
            yield r'[0-9]', Text(lambda t: "has 3" if '3' in t else 'no 3')
            yield default_action, "unparsed"

    >>> from livelex import Lexer
    >>> from pprint import pprint
    >>> s = "bla pythonBLA blub blablo b39la 1 4 ble"
    >>> pprint(list(Lexer(MyLang.root).lex(s)))
    [(0, 'bla', 'bla action', False),
     (4, 'python', 'TEXT', False),
     (10, 'BLA', 'bla action', False),
     (14, 'bl', 'bl act', None),
     (16, 'ub', 'ub act', False),
     (19, 'bla', 'bla action', False),
     (22, 'blo', 'blo action', True),
     (26, 'b', 'unparsed', False),
     (27, '3', 'has 3', False),
     (28, '9', 'no 3', False),
     (29, 'la', 'unparsed', False),
     (32, '1', '1 in blo', False),
     (34, '4', '4 in blo, end', True),
     (36, 'ble', 'ble action', False)]



The livelex module is written and maintained by Wilbert Berendsen.
