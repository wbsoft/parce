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

| Homepage: https://github.com/wbsoft/parce
| Download: https://pypi.org/project/parce/
| Documentation: https://python-parce.readthedocs.io/en/latest/

Why the name? It's short, not already taken and sounds like 'parse' :-)


Features
--------

* Parses text into a tree structure of tokens using a language definition
* Powerful methods to iterate over, and examine the tree
* Can re-parse part of a text (just the changes part) and update the tree
* Can parse/tokenize in a background thread
* It is easy to write language definitions or inherit from existing ones
* Optionally use a Document (kind of mutable string) to keep and edit the text
* Extensive documentation and clean code design

The parce package requires Python 3.5+ and is released under the General Public
License version 3. Testing is done using ``pytest-3`` in the base directory.
Test files can be added to the ``tests/`` directory.
