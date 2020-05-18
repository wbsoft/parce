Overview
========

The *parce* module consists of a *lexer* that can split text into tokens
according to a *lexicon*, which is a set of rules with patterns to look for. A
*tree builder* can put the lexed tokens in a tree structure, which can be
*queried* in powerful ways. A *transformer* can transform the tree structure in
any sophisticated, dedicated data structure you can imagine.

Lexicons are grouped together defining a language. Some language definitions
are already bundled, in the ``lang`` directory. But it is also very easy to
build your own language definitions or inherit from existing definitions and
taylor them to your own needs. This documentation helps you going, see
:doc:`gettingstarted`.

Features
^^^^^^^^

* lex text to a stream of `events` or a tree structure of `tokens`, according
  to a language definition
* examine and query the generated tree structure
* transform the tree structure to anything else
* apply changes to the text, and only update the needed part of a tree, also
  a transformation can reuse unchanged parts
* provide a Document (mutable string) that can be modified and that keeps
  its tokenized tree up-to-date automatically
* lex and transform in a background thread
* map the `action` of a token to CSS classes for highlighting based on CSS

You can lex a text once and examine the generated tree structure of tokens,
but, and this is a key point of `parce`, you can also use a Document which
keeps its text contents tokenized automatically, and if you change part of
the text, only updates the tokens that need to, leaving the rest in place.

The Document exactly tells the region that needs to be updated, and an
application could use the type of the tokens (action) to determine the text
format to highlight every type of text in a special way.

Using some programming you can integrate Document with a structure that
represents a text document in a GUI editor, and implement syntax highlighting
as you type. And because the token tree stucture has very powerful search and
query features, you can quickly provide the user with much feedback about the
type of the text that is entered/edited.

There is already a package `parceqt <https://github.com/wbsoft/parceqt>`_
that does this for applications based on the Qt5 library (using PyQt5).

Goal
^^^^

*parce* was written to replace the LilyPond-parser in the `Frescobaldi
<https://frescobaldi.org/>`_ editor. Frescobaldi highlights `LilyPond
<https://lilypond.org/>`_ music text as you type (as many other text editors),
and I wanted to use that highlighting information for more purposes than only
the color of the text.

That's why I created the tree structure; any token knows its parent context, so
sophisticated context-sensitive autocompletion can be implemented that needs no
tedious and slow text or token searching to determine what kind of text we're
in.

And because Frescobaldi needs to provide the user also with a *musical*
understanding of the LilyPond music, it converts the token structure of a text
document to a Music structure, which is currently rebuilt on every single
change of the text.

So I created the transform module, which is capable of transforming only the
modified parts of a text to anything else, smartly reusing intermediate
transformed results from contexts that didn't change.

TODO
^^^^

* create highlighted output such as HTML
* more bundled languages :-)

