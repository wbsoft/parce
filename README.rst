The parce module
================

::

   import parce

`Homepage       <https://parce.info>`_                          •
`Development    <https://github.com/wbsoft/parce>`_             •
`Download       <https://pypi.org/project/parce/>`_             •
`Documentation  <https://parce.info>`_                          •
`License        <https://www.gnu.org/licenses/gpl-3.0>`_

This Python package, `parce`, can be used to lex text into a tree structure
using a language definition. The tree structure can subsequently be queried and
transformed in various powerful ways.

The `parce` module is designed to be very fast, while being written in pure
Python, using native data structures as much as possible. Lexing and
transforming can be done in a background thread.

A key feature of parce is that you can re-lex and re-transform only modified
parts of a text if you already have lexed it. This makes parce suitable for
text editors etc. that need to keep a tokenized structure of the text
up-to-date e.g. to support syntax highlighting as you type.

The module is written and maintained by Wilbert Berendsen. Python 3.5 and
higher is supported. Besides Python itself there are no other dependencies.
Testing is done by running ``pytest-3`` in the root directory.

The logo is a public domain tree image with the name in the Gentium italic font.
Why the name? It's short, sounds like 'parse', and has the meaning of
"friend", "buddy", "bro." :-)
