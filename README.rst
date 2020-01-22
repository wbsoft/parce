The parce Python module
=========================

This module parses text into tokens, and is able to reparse only modified parts
of the text, using the earlier generated tokens. Tokenized text lives in a tree
structure with powerful quering methods for finding tokens and contexts.

The parce module is designed to be fast, and can tokenize in a background
thread, so that even when using very large documents, GUI applications that
need to be responsive do not grind to a halt.

Main use case: syntax highlighting in text editors, but also understanding the
meaning of text to be able to provided context sensitive editing features.

The parce module is written and maintained by Wilbert Berendsen.

Homepage: https://github.com/wbsoft/parce
Download: https://pypi.org/project/parce/

The module is designed to parse text using rules, which are regular-expression
based. Rules are grouped into lexicons, and lexicons are grouped into a
Language object. Every lexicon has its own set of rules that describe the text
that is expected in that context.

A rule consists of three parts: a pattern, an action and a target.

* The pattern is a either a regular expression string, or an object that
  inherits Pattern. In that case its build() method is called to get the
  pattern. If the pattern matches, a match object is created. If not,
  the next rule is tried.

* The action can be any object, and is streamed together with the matched part
  of the text. It can be seen as a token. If the action is an instance of
  DynamicAction, its filter_actions() method is called, which can yield zero or
  more tokens.  The special `skip` action skips the matching text.

* The target is a list of objects, which can be integer numbers or references
  to a different lexicon. A positive number pushes the same lexicon on the
  stack, while a negative number pops the current lexicon(s) off the stack, so
  that lexing the text continues with a previous lexicon. It is also possible
  to pop a lexicon and push a different one.

  Instead of a list of objects, a DynamicTarget object can also be used, which
  can change the target based on the match object.

Using a special rule, a lexicon may specify a default action, which is
streamed with text that is not recognized by any other rule in the lexicon.
A lexicon may also specify a default target, which is chosen when no rule
matches the current text.


Parsing
-------

Parsing (better: lexing) text always starts in a lexicon, which is called the
root lexicon. The rules in that lexicon are tried one by one. As soon as there
is a match, a Token is generated with the matching text, the position of the
text and the action that was specified in the rule. And if a target was
specified, parsing continues in a different lexicon.

The tokens are put in a tree structure. Every active lexicon creates a Context
list that holds the tokens and child contexts. If a target pops back to a
previous lexicon, the previous context becomes the current one again.

All tokens and contexts point to their parents, so it is possible to manipulate
and query the tree structure in various ways.

The structure of the tree is built by the TreeBuilder, see the `tree` and the
`treebuilder` module. At the root is the Context carrying the root lexicon.
The root context contains Tokens and/or other Contexts.

The TreeBuilder is capable of tokenizing the text in a background thread and
also to rebuild just a changed part of the text, smartly reusing earlier
generated tokens if possible.


Iterating and Querying
----------------------

Both Token and Context have many methods for iterating over the tree, for
getting at the parent, child or sibling nodes. Context has various find()
methods to quickly find a token or context at a certain position in the text.

Using the Context.query property you can build XPath-like chains of filtering
queries to quickly find tokens or contexts based on text, action or lexicon.
This is described in the `query` module.


Example
-------

Here are some examples of how to create a Language class and then use it:

.. code:: python

    import parce

    from parce import (
        Language, lexicon,
        words, bygroup, bymatch, bytext,
        default_action,
        default_target,
        skip,
        tomatch,
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


    >>> import parce
    >>> tree = parce.root(MyLang.root, s)
    >>> tree.dump()
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
    >>> tree.find_token(50)
    <Token 'a string with ' at 48 (string)>
    >>> tree.find_token(50).parent
    <Context MyLang.string at 48-84 (4 children)>

    >>> d = parce.Document(MyLang.root, s)
    >>> d
    <Document '\nThis is (an example) text w...'>

    >>> print(d.text())

    This is (an example) text with 12 numbers
    and "a string with \" escaped characters",
    and a % comment that TODO lasts until the end
    of the line.

    >>> d[50:56]
    'string'
    >>> with d:
    ...  d[9:12] = '(a "much longer'
    ...  d[20:20] = '"'
    ...
    >>> print(d.text())

    This is (a "much longer example") text with 12 numbers
    and "a string with \" escaped characters",
    and a % comment that TODO lasts until the end
    of the line.

    >>> d.get_root()[3].dump()
    <Context MyLang.parenthesized at 10-34 (4 children)>
     ├╴<Token 'a' at 10 (word)>
     ├╴<Token '"' at 12 (string)>
     ├╴<Context MyLang.string at 13-33 (2 children)>
     │  ├╴<Token 'much longer example' at 13 (string)>
     │  ╰╴<Token '"' at 32 (string)>
     ╰╴<Token ')' at 33 (paren)>



