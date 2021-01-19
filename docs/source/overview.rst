Overview
========

The *parce* module consists of a *lexer* that can split text into tokens
according to one or more *lexicons*, which are sets of rules with regular
expression patterns to look for. A *tree builder* can put the lexed tokens in a
tree structure, which can be *queried* in powerful ways. A *transformer* can
transform the tree structure in any sophisticated, dedicated data structure you
can imagine.

Lexicons are grouped together defining a language. Some language definitions
are already bundled, in the ``lang`` directory. But it is also very easy to
build your own language definitions or inherit from existing definitions and
taylor them to your own needs. This documentation helps you going, see
:doc:`gettingstarted`.

Features
^^^^^^^^

* tokenize text to a stream of `events` or a tree structure of `tokens`,
  according to a language definition
* examine and query the generated tree structure
* transform the tree structure to anything else
* apply changes to the text, and only update the needed part of a tree (also
  a transformation can reuse unchanged parts)
* provides a Document (mutable string) that automatically keeps its tokenized
  tree structure up-to-date.
* changes to be made to a document can be collected and applied at once
* lex and transform in a background thread
* highlight text by mapping the `action` of a token to a CSS class and reading
  style properties from a CSS "theme" file.

A key feature of *parce* is that you can re-lex and re-transform only modified
parts of a text if you already have lexed it. This makes *parce* suitable for
text editors etc. that need to keep a tokenized structure of the text
up-to-date e.g. to support syntax highlighting or very context-sensitive
autocompletion as you type.

Using some programming you can integrate the Document class with a structure
that represents a text document in a GUI editor. The tokenized tree structure
can be traversed and queried in many ways, enabling you to quickly provide the
user with feedback about the type of the text that is entered/edited.

There is already a package `parceqt <https://github.com/wbsoft/parceqt>`_
that does this for applications based on the Qt5 library (using PyQt5).

Goal
^^^^

*parce* was written to replace the LilyPond-parser in the `Frescobaldi
<https://frescobaldi.org/>`_ editor. Frescobaldi highlights `LilyPond
<https://lilypond.org/>`_ music text as you type (as many other text editors),
and I wanted to use that highlighting information for more purposes than only
to color the text.

That's why I created the tree structure; any token knows its parent context, so
sophisticated context-sensitive autocompletion can be implemented that needs no
tedious and slow text or token searching to determine what kind of text we're
in.

I created the transform module because Frescobaldi needs to provide the user
also with a *musical* understanding of the LilyPond music text: it should
convert the text document to a musical structure. Currently, this whole
structure is invalidated on every single change of the text, and then rebuilt
when requested. Using *parce*'s transform module, I can arrange it so that only
the modified part of the text and the tokenized tree structure need to be
re-transformed, smartly reusing intermediate transformed results from contexts
that didn't change.

Because this realtime, incrementally tokenizing and transforming is such a
generic process, I decided to make *parce* a separate, generic Python package.

TODO
^^^^

* create highlighted output formatters for other formats than HTML, like LaTeX,
  etc.
* more bundled languages :-)

