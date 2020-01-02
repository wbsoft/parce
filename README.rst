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

    from livelex import (
        Language, lexicon,
        Words, Subgroup, Text,
        default_action,
        default_target,
        skip,
        MatchTarget, TextTarget,
    )

    class MyLang(Language):
        """A Language represents a set of Lexicons comprising a specific language.

        A Language is never instantiated. The class itself serves as a namespace
        and can be inherited from.



        """

        @lexicon(re_flags=0)
        def root(cls):
            yield r'"', "string", cls.string
            yield r'\(', "paren", cls.parenthesized
            yield r'\d+', "number"
            yield r'%', "comment", cls.comment
            yield r'[,.!?]', "punctuation"
            yield r'\w+', "word"
        
        @lexicon
        def string(cls):
            yield r'\\[\\"]', 'string escape'
            yield r'"', "string", -1
            yield default_action, "string"

        @lexicon(re_flags=re.MULTILINE)
        def comment(cls):
            yield r'$', "comment", -1
            yield r'XXX|TODO', "todo"
            yield default_action, "comment"

        @lexicon
        def parenthesized(cls):
            yield r'\)', "paren", -1
            yield from cls.root()


    s = r"""
    This is (an example) text with 12 numbers
    and "a string with \" escaped characters",
    and a % comment that TODO lasts until the end
    of the line.
    """


    >>> from livelex import Document
    >>> Document(MyLang.root, s).root().dump()
    <Context MyLang.root at 1-144 (20 children)>
     ├╴<Token 'This' at 1 (word)>
     ├╴<Token 'is' at 6 (word)>
     ├╴<Token '(' at 9 (paren)>
     ├╴<Context MyLang.parenthesized at 10-21 (3 children)>
     │  ├╴<Token 'an' at 10 (word)>
     │  ├╴<Token 'example' at 13 (word)>
     │  ╰╴<Token ')' at 20 (paren)>
     ├╴<Token 'text' at 22 (word)>
     ├╴<Token 'with' at 27 (word)>
     ├╴<Token '12' at 32 (number)>
     ├╴<Token 'numbers' at 35 (word)>
     ├╴<Token 'and' at 43 (word)>
     ├╴<Token '"' at 47 (string)>
     ├╴<Context MyLang.string at 48-84 (4 children)>
     │  ├╴<Token 'a string with ' at 48 (string)>
     │  ├╴<Token '\\"' at 62 (string escape)>
     │  ├╴<Token ' escaped characters' at 64 (string)>
     │  ╰╴<Token '"' at 83 (string)>
     ├╴<Token ',' at 84 (punctuation)>
     ├╴<Token 'and' at 86 (word)>
     ├╴<Token 'a' at 90 (word)>
     ├╴<Token '%' at 92 (comment)>
     ├╴<Context MyLang.comment at 93-131 (3 children)>
     │  ├╴<Token ' comment that ' at 93 (comment)>
     │  ├╴<Token 'TODO' at 107 (todo)>
     │  ╰╴<Token ' lasts until the end' at 111 (comment)>
     ├╴<Token 'of' at 132 (word)>
     ├╴<Token 'the' at 135 (word)>
     ├╴<Token 'line' at 139 (word)>
     ╰╴<Token '.' at 143 (punctuation)>


The livelex module is written and maintained by Wilbert Berendsen.
