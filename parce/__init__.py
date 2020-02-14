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

For parsing tasks and writing language definitions, or using existing language
definitions, the main ``parce`` module provides all that's needed.

So a simple::

    import parce

is sufficient. Inside a language definition, it is easier to just use::

    from parce import *

to get easy access to all the actions and the helper functions.

Besides the classes and functions below, the following standard actions are
defined here. See the :py:mod:`action <parce.action>` module for more
explanation abount standard actions.

Generic actions:

    .. py:data:: Whitespace
    .. py:data:: Text

Base actions:

    .. py:data:: Comment
    .. py:data:: Delimiter
    .. py:data:: Error
    .. py:data:: Escape
    .. py:data:: Keyword
    .. py:data:: Literal
    .. py:data:: Name
    .. py:data:: Pseudo
    .. py:data:: Template

Actions that derive from :py:data:`Name`:

    .. py:data:: Name.Attribute
    .. py:data:: Name.Builtin
    .. py:data:: Name.Class
    .. py:data:: Name.Command
    .. py:data:: Name.Constant
    .. py:data:: Name.Decorator
    .. py:data:: Name.Exception
    .. py:data:: Name.Function
    .. py:data:: Name.Identifier
    .. py:data:: Name.Macro
    .. py:data:: Name.Method
    .. py:data:: Name.Namespace
    .. py:data:: Name.Object
    .. py:data:: Name.Property
    .. py:data:: Name.Symbol
    .. py:data:: Name.Tag
    .. py:data:: Name.Variable

Actions that derive from :py:data:`Literal`:

    .. py:data:: Verbatim( = Literal.Verbatim)
    .. py:data:: String( = Literal.String)
    .. py:data:: Number( = Literal.Number)
    .. py:data:: Boolean( = Literal.Boolean)
    .. py:data:: Char( = Literal.Char)

Other derived actions:

    .. py:data:: Comment.Alert
    .. py:data:: Literal.Color
    .. py:data:: Literal.Email
    .. py:data:: Literal.Url
    .. py:data:: Operator(= Delimiter.Operator)
    .. py:data:: String.Double
    .. py:data:: String.Single
    .. py:data:: String.Escape
    .. py:data:: Template.Preprocessed
    .. py:data:: Text.Deleted
    .. py:data:: Text.Inserted

If you reference a non-existing sub-action, it is created.

When highlighting, a standard action maps to a list of CSS classes with all the
names lowercased. So String.Double maps to the ("literal", "string", "double")
CSS classes. See the :py:mod:`theme <parce.theme>` module for more
information.

"""

from . import pattern, action, target
from . import lexicon as lexicon_, treebuilder, document, treedocument
from .document import Cursor
from .language import Language
from .pkginfo import version, version_string


class Document(treedocument.TreeDocumentMixin, document.Document):
    """A Document that automatically keeps its contents tokenized."""
    def __init__(self, root_lexicon=None, text=""):
        document.Document.__init__(self, text)
        builder = treebuilder.BackgroundTreeBuilder(root_lexicon)
        treedocument.TreeDocumentMixin.__init__(self, builder)
        if text:
            with builder.change() as c:
                c.change_contents(text)


def root(root_lexicon, text):
    """Return the root context of the tree structure of all tokens from text."""
    return treebuilder.TreeBuilder(root_lexicon).tree(text)


def tokens(root_lexicon, text):
    """Convenience function that yields all the tokens from the text."""
    return root(root_lexicon, text).tokens()


def words(words, prefix="", suffix=""):
    r"""Return a Pattern matching any of the words.

    The returned Pattern builds an optimized regular expression matching any of
    the words contained in the `words` list.

    A ``prefix`` or ``suffix`` can be given, which will be added to the regular
    expression. Using the word boundary character ``\b`` as suffix is
    recommended to be sure the match ends at a word end.

    """
    return pattern.Words(words, prefix, suffix)


def char(chars, positive=True):
    """Return a Pattern matching one of the characters in the specified string.

    If `positive` is False, the set of characters is complemented, i.e. the
    Pattern matches any single character that is not in the specified string.

    """
    return pattern.Char(chars, positive)


def bygroup(*actions):
    """Return a SubgroupAction that yields tokens for each subgroup in a regular expression.

    This action uses capturing subgroups in the regular expression pattern and
    creates a Token for every subgroup, with that action. You should provide
    the same number of actions as there are capturing subgroups in the pattern.
    Use non-capturing subgroups for the parts you're not interested in, or the
    special ``skip`` action.

    """
    return action.SubgroupAction(*actions)


def bymatch(predicate, *actions):
    """Return a MatchAction that chooses the action based on the match object.

    The returned MatchAction calls the predicate function with the match object
    as argument. The function should return the index of the action to choose.
    If you provide two possible actions, the predicate function may also return
    True or False, in which case True chooses the second action and
    False the first.

    """
    return action.MatchAction(predicate, *actions)


def bytext(predicate, *actions):
    """Return a TextAction that chooses the action based on the text.

    The returned TextAction calls the predicate function with the matched text
    as argument.  The function should return the index of the action to choose,
    in the same way as with :func:`~parce.bymatch`.

    """
    return action.TextAction(predicate, *actions)


def tomatch(predicate, *targets):
    """Return a MatchTarget that chooses the target based on the match object.

    The predicate is run with the match object as argument and should return
    the (integer) index of the desired target. True and False are also valid
    return values, they count as 1 and 0, respectively.

    Each target can be a list or tuple of targets, just like in normal rules,
    where the third and more items form a list of targets. A target can also be
    a single integer or a lexicon. Use ``()`` or ``0`` for a target that does
    nothing.

    """
    return target.MatchTarget(predicate, *targets)


def lexicon(rules_func=None, **kwargs):
    """Lexicon factory decorator.

    Use this decorator to make a function in a Language class definition a
    LexiconDescriptor object. The LexiconDescriptor is a descriptor, and when
    calling it via the Language class attribute, a Lexicon is created, cached
    and returned.

    You can specify keyword arguments, that will be passed on to the Lexicon
    object as soon as it is created.

    The following keyword arguments are supported:

    re_flags: The flags that are passed to the regular expression compiler

    The code body of the function should return (yield) the rules of the
    lexicon, and is run with the Language class as first argument, as soon as
    the lexicon is used for the first time.

    You can also call the Lexicon object just as an ordinary classmethod, to
    get the rules, e.g. for inclusion in a different lexicon.

    """
    if rules_func and not kwargs:
        return lexicon_.LexiconDescriptor(rules_func)
    def lexicon(rules_func):
        return lexicon_.LexiconDescriptor(rules_func, **kwargs)
    return lexicon


def theme_by_name(name="default"):
    """Return a Theme from the default themes in the themes/ directory."""
    from .theme import Theme
    return Theme.byname(name)


def theme_from_file(filename):
    """Return a Theme loaded from the specified CSS filename."""
    from .theme import Theme
    return Theme(filename)


# these can be used in rules where a pattern is expected
default_action = object()   #: denotes a default action for unmatched text
default_target = object()   #: denotes a default target when no text matches


#: used to suppress generating a token
skip = action.SkipAction()

# predefined standard actions
# keep these in sync with the list above in the doc string.
Whitespace = action.StandardAction("Whitespace")
Text = action.StandardAction("Text")

Comment = action.StandardAction("Comment")
Delimiter = action.StandardAction("Delimiter")
Error = action.StandardAction("Error")
Escape = action.StandardAction("Escape")
Keyword = action.StandardAction("Keyword")
Literal = action.StandardAction("Literal")
Name = action.StandardAction("Name")
Pseudo = action.StandardAction("Pseudo")
Template = action.StandardAction("Template")

# Actions that derive from Name

Name.Attribute
Name.Builtin
Name.Class
Name.Command
Name.Constant
Name.Decorator
Name.Exception
Name.Function
Name.Identifier
Name.Macro
Name.Method
Name.Namespace
Name.Object
Name.Property
Name.Symbol
Name.Tag
Name.Variable

# Actions that derive from Literal:

Verbatim = Literal.Verbatim
String = Literal.String
Number = Literal.Number
Boolean = Literal.Boolean
Char = Literal.Char

# Other derived actions:

Comment.Alert
Literal.Color
Literal.Email
Literal.Url
Operator = Delimiter.Operator
String.Double
String.Single
String.Escape
Template.Preprocessed
Text.Deleted
Text.Inserted


