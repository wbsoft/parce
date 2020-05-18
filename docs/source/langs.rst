Bundled language definitions
============================

.. toctree::
   :hidden:
   :glob:

   lang/*

The *parce* package comes with an amount of bundled language definitions.
You can import them directly, e.g.::

    from parce.lang.css import Css
    root_lexicon = Css.root

but you can also use the :func:`~parce.find` function to get the root lexicon
of a language definition by its name::

    import parce
    root_lexicon = parce.find("css")

This is a listing of the modules in ``parce.lang`` and the Language classes
they define:

.. include:: langs.inc
