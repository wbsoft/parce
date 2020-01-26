Overview
========

The `parce` module consists of a parser that can build a tree structure of
`tokens` from a text, using regular expression patterns. Parsing happens by a
`lexicon`, which is a set of rules with patterns to look for. Tokens can be
give a meaning (`action`) and a rule can, if its pattern matches, also
move parsing to another lexicon, "opening a new context", so to say.

Lexicons are grouped together defining a language. Some language definitions
are already bundled, in the ``lang`` directory. But it is also very easy to
build your own language definitions or inherit from existing definitions and
taylor them to your own needs. This documentation helps you going, see
:doc:`gettingstarted`.

Features
^^^^^^^^

You can parse a text once and examine the generated tree structure of tokens,
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

A difference with a beautiful package like `pygments` is that emphasis in
`parce` lies on live updating and interactive usage of the token tree, which
means that parsing is always sequential. For example, it is not supported
that first a large chunk of text is matched and then tokenized by another
lexer. But is is very easy to switch language, because lexicons are not tied
to a particular language; you can switch to them from any other language or
incorporate its rules in your own lexicon. You can also use lookahead
patterns to switch lexicon before generating tokens if it is really needed.

A parser does not keep any state information, and that's why `parce` can so
easily update only a small part of a large token tree: it can start anywhere
parsing, the context the current token resides in is all the information that
is available.

TODO
^^^^

Functionality to provide default text formats for highlighting text
will be added, based on CSS.

Modules to convert plain tokenized text to syntax highlighted formats
such as HTML will also be added.

More bundled languages :-)
