.. parce documentation master file, created by
   sphinx-quickstart on Fri Dec 20 19:53:27 2019.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

Welcome to parce's documentation!
===================================

This module parses text into tokens, and is able to reparse only modified parts
of the text, using the earlier generated tokens. Tokenized text lives in a tree
structure with powerful quering methods for finding tokens and contexts.

The parce module is designed to be fast, and can tokenize in a background
thread, so that even when using very large documents, GUI applications that
need to be responsive do not grind to a halt.

Main use case: syntax highlighting in text editors, but also understanding the
meaning of text to be able to provided context sensitive editing features.

The parce module is written and maintained by Wilbert Berendsen.

Supports Python 3.5 and higher.
Testing is done by running ``pytest-3`` in the root directory.

Homepage: https://github.com/wbsoft/parce
Download: https://pypi.org/project/parce/

Why the name? It's short, not already taken and sounds like 'parse' :-)


Overview
--------

The module is designed to parse text using rules, which are regular-expression
based. Rules are grouped into lexicons, and lexicons are grouped into a
``Language`` object. Every lexicon has its own set of rules that describe the
text that is expected in that context.

A rule consists of three parts: a pattern, an action and a target.

* The pattern is a either a regular expression string, or an object that
  inherits ``Pattern``. In that case its ``build()`` method is called to get the
  pattern. If the pattern matches, a match object is created. If not, the next
  rule is tried.

* The action can be any object, and is streamed together with the matched part
  of the text. It can be seen as a token. If the action is an instance of
  ``DynamicAction``, its ``filter_actions()`` method is called, which can yield
  zero or more tokens.

* The target is a list of objects, which can be integer numbers or references
  to a different lexicon. A positive number pushes the same lexicon on the
  stack, while a negative number pops the current lexicon(s) off the stack, so
  that lexing the text continues with a previous lexicon. It is also possible
  to pop a lexicon and push a different one.

  Instead of a list of objects, a ``DynamicTarget`` object can also be used,
  which can change the target based on the match object.

Using a special rule, a lexicon may specify a default action, which is
streamed with text that is not recognized by any other rule in the lexicon.
A lexicon may also specify a default target, which is chosen when no rule
matches the current text.


Parsing
-------

Parsing (better: lexing) text always starts in a lexicon, which is called the
root lexicon. The rules in that lexicon are tried one by one. As soon as there
is a match, a ``Token`` is generated with the matching text, the position of the
text and the action that was specified in the rule. And if a target was
specified, parsing continues in a different lexicon.

The tokens are put in a tree structure. Every active lexicon creates a
``Context`` list that holds the tokens and child contexts. If a target pops
back to a previous lexicon, the previous context becomes the current one again.

All tokens and contexts point to their parents, so it is possible to manipulate
and query the tree structure in various ways.

The structure of the tree is built by the ``TreeBuilder``, see the ``tree`` and
the ``treebuilder`` module. At the root is the Context carrying the root
lexicon. The root context contains ``Token``\s and/or other ``Context``\s.

The ``TreeBuilder`` is capable of tokenizing the text in a background thread and
also to rebuild just a changed part of the text, smartly reusing earlier
generated tokens if possible.


Iterating and Querying
----------------------

Both ``Token`` and ``Context`` have many methods for iterating over the tree,
for getting at the parent, child or sibling nodes. Context has various
``find...()`` methods to quickly find a token or context at a certain position
in the text.

Using the ``query`` property of ``Token`` or ``Context`` you can build
XPath-like chains of filtering queries to quickly find tokens or contexts
based on text, action or lexicon. This is described in the ``query`` module.




.. toctree::
   :maxdepth: 1
   :caption: Contents:

   parce.rst
   action.rst
   document.rst
   language.rst
   lexicon.rst
   pattern.rst
   pkginfo.rst
   query.rst
   regex.rst
   target.rst
   tree.rst
   treebuilder.rst
   treedocument.rst
   validate.rst



Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
