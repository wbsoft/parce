The parce module
================

::

   import parce

`Homepage       <https://parce.info>`_                          •
`Development    <https://github.com/wbsoft/parce>`_             •
`Download       <https://pypi.org/project/parce/>`_             •
`Documentation  <https://parce.info>`_                          •
`License        <https://www.gnu.org/licenses/gpl-3.0>`_

This Python package, `parce`, can be used for lexing text into tokens using
one of the supplied language definitions in the ``lang`` directory, or
building your own language definitions and lex text using them.

The `parce` module is designed to be very fast, while being written in pure
Python, using native data structures as much as possible. Lexing can be done
in a background thread.

A powerful feature of parce is that you can retokenize only modified parts of a
text if you already have tokenized it. This makes parce suitable for text
editors etc. that need to keep a tokenized structure of the text up-to-date
e.g. to support syntax highlighting as you type.

The module is written and maintained by Wilbert Berendsen. Python 3.5 and
higher is supported. Besides Python itself there are no other dependencies.
Testing is done by running ``pytest-3`` in the root directory.

The logo is a public domain tree image with the name in the Gentium italic font.
Why the name? It's short, sounds like 'parse', and has the meaning of
"friend", "buddy", "bro." :-)
