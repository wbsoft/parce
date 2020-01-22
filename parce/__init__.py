# -*- coding: utf-8 -*-
#
# This file is part of the parce Python package.
#
# Copyright © 2019 by Wilbert Berendsen <info@wilbertberendsen.nl>
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

"""

from . import pattern, action, target
from . import lexicon as lexicon_, treebuilder, document, treedocument
from .document import Cursor
from .language import Language
from .pkginfo import version, version_string


# these can be used in rules where a pattern is expected
default_action = object()   # denotes a default action for unmatched text
default_target = object()   # denotes a default target when no text matches


# used to suppress a token
skip = action.SkipAction()

# predefined standard actions
Whitespace = action.StandardAction("Whitespace")
Text = action.StandardAction("Text")

Escape = action.StandardAction("Escape")
Keyword = action.StandardAction("Keyword")
Name = action.StandardAction("Name")
Literal = action.StandardAction("Literal")
Delimiter = action.StandardAction("Delimiter")
Comment = action.StandardAction("Comment")
Error = action.StandardAction("Error")

Verbatim= Literal.Verbatim
String = Literal.String
Number = Literal.Number
Boolean = Literal.Boolean
Char = Literal.Char
Operator = Delimiter.Operator
Builtin = Name.Builtin
Function = Name.Function
Variable = Name.Variable


class Document(treedocument.TreeDocumentMixin, document.Document):
    """A Document that automatically keeps its contents tokenized."""
    def __init__(self, root_lexicon=None, text=""):
        document.Document.__init__(self, text)
        builder = treebuilder.BackgroundTreeBuilder(root_lexicon)
        treedocument.TreeDocumentMixin.__init__(self, builder)
        if text:
            with builder.change() as c:
                c.change_contents(text)


def words(words):
    """Return a Pattern object that builds a regular expression from a list of words.

    To be used as a pattern in a rule.

    """
    return pattern.Words(words)


def char(chars, positive=True):
    """Return a Pattern matching one of the characters in the specified string.

    If positive is False, the set of characters is complemented, i.e. the
    Pattern matches any single character that is not in the specified string.

    """
    return pattern.Char(chars, positive)


def bygroup(*actions):
    """Return a SubgroupAction that yields tokens for each subgroup in a regular expression.

    To be used as an action in a rule.

    """
    return action.SubgroupAction(*actions)


def bymatch(predicate, *actions):
    """Return a MatchAction that chooses the action based on the match object.

    To be used as an action in a rule.

    The predicate is run with the match object as argument and should return
    the (integer) index of the desired action. True and False are also valid
    return values, they count as 1 and 0, respectively.

    This might look cumbersome (it might look easier to just return the action
    from the function), but this way we know the possible actions beforehand,
    and we could translate the actions via a mapping and still keep everything
    working.

    """
    return action.MatchAction(predicate, *actions)


def bytext(predicate, *actions):
    """Return a TextAction that chooses the action based on the text.

    To be used as an action in a rule.

    The predicate is run with the match object as argument and should return
    the index of the desired action. See also bymatch().

    """
    return action.TextAction(predicate, *actions)


def tomatch(predicate, *targets):
    """Return a MatchTarget that chooses the target based on the match object.

    To be used as a target in a rule.

    The predicate is run with the match object as argument and should return
    the (integer) index of the desired target. True and False are also valid
    return values, they count as 1 and 0, respectively.

    Each target can be a list or tuple of targets, just like in normal rules,
    where the third and more items form a list of targets. A target can also be
    a single integer or a lexicon. Use () or 0 for a target that does nothing.

    """
    return target.MatchTarget(predicate, *targets)


def lexicon(rules_func=None, **kwargs):
    """Lexicon factory decorator.

    Use this decorator to make a function in a Language class definition a
    Lexicon object. The Lexicon object is actually a descriptor, and when
    calling it via the Language class attribute, a BoundLexicon is created,
    cached and returned.

    You can specify keyword arguments, that will be passed on to the
    BoundLexicon object as soon as it is created.

    The following keyword arguments are supported:

    re_flags: The flags that are passed to the regular expression compiler

    The code body of the function should return (yield) the rules of the
    lexicon, and is run with the Language class as first argument, as soon as
    the lexicon is used for the first time.

    You can also call the BoundLexicon object just as an ordinary classmethod,
    to get the rules, e.g. for inclusion in a different lexicon.

    """
    if rules_func and not kwargs:
        return lexicon_.Lexicon(rules_func)
    def lexicon(rules_func):
        return lexicon_.Lexicon(rules_func, **kwargs)
    return lexicon


def root(root_lexicon, text):
    """Return the root context of the tree structure of all tokens from text."""
    return treebuilder.TreeBuilder(root_lexicon).tree(text)


def tokens(root_lexicon, text):
    """Convenience function that yields all the tokens from the text."""
    return root(root_lexicon, text).tokens()


