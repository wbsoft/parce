# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019-2020 by Wilbert Berendsen <info@wilbertberendsen.nl>
#
# This module is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This module is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.


"""
The parce Python module.

The main module provides the listed classes and functions, enough to build
a basic language definition or to use the bundled language definitions.

The standard actions that are used by the bundled language definitions to
specify the type of parsed text fragments are in the :mod:`~parce.action`
module. The helper functions for dynamic rule items are in the
:mod:`~parce.rule` module.

It is recommended to import *parce* like this::

    import parce

although in a language definition it can be easier to do this::

    from parce import Language, lexicon, skip, default_action, default_target
    from parce.rule import words, bygroup   # whichever you need
    import parce.action as a

Then you get the ``Language`` class and ``lexicon`` decorator from parce, and
all standard actions can be accessed via the ``a`` prefix, like ``a.Text``.

.. py:data:: version

   The version as a three-tuple(major, minor, patch). See :mod:`~parce.pkginfo`.

.. py:data:: version_string

   The version as a string.

"""

# imported when using from parce import *
__all__ = (
    # important classes
    'Cursor',
    'Document',

    # often used names when defining languages
    'default_action',
    'default_target',
    'Language',
    'lexicon',
    'skip',

    # toplevel functions
    'events',
    'find',
    'root',
    'theme_by_name',
    'theme_from_file',
    'tokens',
)

from . import document, lexer, rule, ruleitem, treebuilder, treedocument, util
from .lexicon import lexicon
from .language import Language
from .document import Cursor
from .pkginfo import version, version_string


class Document(treedocument.TreeDocumentMixin, document.Document):
    """A Document that automatically keeps its contents tokenized.

    You can specify your own TreeBuilder. By default, a BackgroundTreeBuilder
    is used.

    """
    def __init__(self, root_lexicon=None, text="", builder=None):
        document.Document.__init__(self, text)
        if builder is None:
            builder = treebuilder.BackgroundTreeBuilder(root_lexicon)
        else:
            builder.root.clear()
            builder.root.lexicon = root_lexicon
        treedocument.TreeDocumentMixin.__init__(self, builder)
        if text:
            builder.rebuild(text)


def find(name=None, *, filename=None, mimetype=None, contents=None):
    """Find a root lexicon, either by language name, or by filename, mimetype
    and/or contents.

    If you specify a name, tries to find the language with that name, ignoring
    the other arguments.

    If you don't specify a name, but instead one or more of the other (keyword)
    arguments, tries to find the language based on filename, mimetype or
    contents.

    If a language is found, returns the root lexicon. If no language could be
    found, None is returned (which can also be used as root lexicon, resulting
    in an empty token tree).

    Examples::

        >>> import parce
        >>> parce.find("xml")
        Xml.root
        >>> parce.find(contents='{"key": 123;}')
        Json.root
        >>> parce.find(filename="style.css")
        Css.root

    This function uses the :mod:`~parce.registry` module and by default it
    finds all bundled languages. See the module's documentation to find out how
    to add your own languages to a registry.

    """
    from . import registry
    if name:
        lexicon_name = registry.find(name)
    else:
        for lexicon_name in registry.suggest(filename, mimetype, contents):
            break
        else:
            return
    if lexicon_name:
        return registry.root_lexicon(lexicon_name)


def root(root_lexicon, text):
    """Return the root context of the tree structure of all tokens from text."""
    return treebuilder.build_tree(root_lexicon, text)


def tokens(root_lexicon, text):
    """Convenience function that yields all the tokens from the text."""
    return root(root_lexicon, text).tokens()


def events(root_lexicon, text):
    """Convenience function that yields all the events from the text."""
    return lexer.Lexer([root_lexicon]).events(text)


def theme_by_name(name="default"):
    """Return a Theme from the default themes in the themes/ directory."""
    from .theme import Theme
    return Theme.by_name(name)


def theme_from_file(filename):
    """Return a Theme loaded from the specified CSS filename."""
    from .theme import Theme
    return Theme(filename)


# these can be used in rules where a pattern is expected
default_action = util.Symbol("default_action")   #: denotes a default action for unmatched text
default_target = util.Symbol("default_target")   #: denotes a default target when no text matches


skip = ruleitem.SkipAction()
"""A dynamic action that yields no tokens, thereby ignoring the matched text."""


