.. parce documentation master file, created by
   sphinx-quickstart on Fri Dec 20 19:53:27 2019.

The parce module
================

::

   import parce

This Python package, `parce`, can be used for parsing text into tokens using
one of the supplied language definitions in the ``lang`` directory, or
building your own language definitions and parse text using them.

A powerful feature of parce is that you can retokenize only modified parts
of a text if you already have tokenized it. This makes parce suitable for
text editor etc. that need to keep a tokenized structure of the text up-to-date
e.g. to support syntax highlighting as you type.

The module is written and maintained by Wilbert Berendsen.
Python 3.5 and higher is supported.
Testing is done by running ``pytest-3`` in the root directory.

| Homepage: https://github.com/wbsoft/parce
| Download: https://pypi.org/project/parce/
| Online documentation: https://python-parce.readthedocs.io/en/latest/

Why the name? It's short, not already taken and sounds like 'parse' :-)


.. toctree::
   :maxdepth: 2
   :caption: Contents:

   overview.rst
   gettingstarted.rst
   deflanguage.rst
   treestructure.rst
   building.rst
   doc.rst

   modoverview.rst

Indices and tables
==================

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
