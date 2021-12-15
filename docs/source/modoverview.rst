Overview of all modules
=======================

.. currentmodule:: parce

The most used functions and classes are in the main :mod:`parce` module:
:class:`Cursor`, :class:`Document`,
the functions :func:`find`, :func:`root`, :func:`events`,
:func:`theme_by_name`, :func:`theme_from_file`,
and the most needed objects to make a language definition:
:class:`Language`, :obj:`default_action`, :obj:`default_target`,
:obj:`lexicon`, and :obj:`skip`.

Other important modules are: :mod:`.action` for the standard actions,
:mod:`.rule` for all dynamic rule items, :mod:`.transform` for the transforming
functionality and :mod:`.indent` for indenting functionality that some languages
support.

For syntax highlighting see :mod:`.out` and its submodules, :mod:`.theme`,
:mod:`.formatter` and :mod:`.themes` which contains the builtin themes.

Below is the full module list:

.. toctree::
   :maxdepth: 1

   parce.rst
   action.rst
   css.rst
   document.rst
   formatter.rst
   indent.rst
   introspect.rst
   language.rst
   lexer.rst
   lexicon.rst
   mutablestring.rst
   pkginfo.rst
   query.rst
   standardaction.rst
   regex.rst
   registry.rst
   rule.rst
   ruleitem.rst
   target.rst
   theme.rst
   themes.rst
   transform.rst
   tree.rst
   treebuilder.rst
   treebuilderutil.rst
   unicharclass.rst
   util.rst
   validate.rst
   work.rst

.. seealso:: :ref:`modindex` and :ref:`genindex`
