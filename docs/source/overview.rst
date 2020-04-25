Overview
========

The `parce` module consists of a lexer that can build a tree structure of
`tokens` from a text, using regular expression patterns. Lexing happens by a
`lexicon`, which is a set of rules with patterns to look for. Tokens can be
given a meaning (`action`) and a rule can, if its pattern matches, also
move parsing to another lexicon, "opening a new context", so to say.

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
* apply changes to the text, and only update the needed part of a tree
* provides a Document (mutable string) that can be modified and that keeps
  its tokenized tree up-to-date automatically
* parsing and tokenizing can be done in a background thread
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

A difference with a beautiful package like `pygments` is that emphasis in
`parce` lies on live updating and interactive usage of the token tree, which
means that parsing is always sequential. For example, it is not supported that
first a large chunk of text is matched by one, and then tokenized by another
lexer. But is is very easy to switch language, because lexicons are not tied to
a particular language; you can switch to them from any other language or
incorporate its rules in your own lexicon. You can also use lookahead patterns
to switch lexicon before generating tokens if it is really needed.

Using dynamic patterns it is possible to switch to a parsing context giving an
argument that is determined at parse time, e.g. a specific pattern that causes
the parser to pop back to the previous context. This can be useful to parse
things like "here documents", which are well-known in languages like Bash and
Ruby.

A parser does not keep any state information, and that's why `parce` can so
easily update only a small part of a large token tree: it can start parsing
anywhere, the context the current token resides in is all the information that
is available.

TODO
^^^^

* create highlighted output such as HTML
* more bundled languages :-)

