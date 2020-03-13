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


from . import action, document, lexer, pattern, rule, treebuilder, treedocument
from . import lexicon as lexicon_
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


def events(root_lexicon, text):
    """Convenience function that yields all the events from the text."""
    return lexer.Lexer([root_lexicon]).events(text)


def words(words, prefix="", suffix=""):
    r"""Return a :class:`~parce.pattern.Pattern` matching any of the words.

    The returned Pattern builds an optimized regular expression matching any of
    the words contained in the `words` list.

    A ``prefix`` or ``suffix`` can be given, which will be added to the regular
    expression. Using the word boundary character ``\b`` as suffix is
    recommended to be sure the match ends at a word end.

    """
    return pattern.Words(words, prefix, suffix)


def char(chars, positive=True):
    """Return a :class:`~parce.pattern.Pattern` matching one of the characters
    in the specified string.

    If `positive` is False, the set of characters is complemented, i.e. the
    Pattern matches any single character that is not in the specified string.

    """
    return pattern.Char(chars, positive)


def arg(escape=True, prefix="", suffix="", default=None):
    r"""Return a :class:`~parce.pattern.Pattern` that contains the argument the
    current Lexicon was called with.

    If there is no argument in the current lexicon, this Pattern yields the
    default value, which is by default None, resulting in the rule being
    skipped.

    When there is an argument, it is escaped using :func:`re.escape` (when
    ``escape`` was set to True), and if given, ``prefix`` is prepended and
    ``suffix`` is appended. When the default value is used, ``prefix`` and
    ``suffix`` are not used.

    """
    import re
    def predicate(arg):
        if isinstance(arg, str):
            if escape:
                arg = re.escape(arg)
            return prefix + arg + suffix
        return default
    return pattern.PredicatePattern(predicate)


def ifarg(pattern, else_pattern=None):
    r"""Return a :class:`~parce.pattern.Pattern` that only yields the specified
    regular expression pattern (or nested Pattern instance) if the lexicon was
    called with an argument.

    If there is no argument in the current lexicon, ``else_pattern`` is
    yielded, which is None by default, resulting in the rule being skipped.

    """
    def predicate(arg):
        return pattern if arg is not None else else_pattern
    return pattern.PredicatePattern(predicate)


def byarg(predicate, *itemlists):
    """Return an :class:`~parce.rule.ArgRuleItem` that chooses its output based
    on the lexicon argument.

    The predicate is called with the lexicon argument (which is None for a
    normal Lexicon, but can have another value for a derivative Lexicon.

    """
    return rule.ArgRuleItem(predicate, *itemlists)


def bymatch(predicate, *itemlists):
    """Return a :class:`~parce.rule.MatchRuleItem` that chooses its output
    based on the match object.

    The returned MatchRuleItem calls the predicate function with the match
    object as argument. The function should return the index of the itemlist
    to choose. If you provide two possible actions, the predicate function
    may also return True or False, in which case True chooses the second
    itemlist and False the first.

    This helper can be used both for action and target objects, or both
    at the same time.

    """
    return rule.MatchRuleItem(predicate, *itemlists)


def bytext(predicate, *itemlists):
    """Return a :class:`~parce.rule.TextRuleItem` that chooses the itemlist
    based on the text.

    The returned TextRuleItem calls the predicate function with the matched
    text as argument.  The function should return the index of the itemlist
    to choose, in the same way as with :func:`~parce.bymatch`.

    This helper can be used both for action and target objects, or both
    at the same time.

    """
    return rule.TextRuleItem(predicate, *itemlists)


def ifgroup(n, itemlist, else_itemlist=()):
    r"""Return a :class:`~parce.rule.MatchRuleItem` that yields ``itemlist`` if
    group n in the match is not empty.

    If group ``n`` in the match object is empty, ``else_itemlist`` is yielded.

    An example rule::

        yield r"\b([a-z]+)\b(\()?", bygroup(Keyword, Delimiter), ifgroup(2, cls.function)

    This rule matches a word with or without an opening parenthesis after it.
    The words gets the action Keyword, and the parenthesis, if there, gets the
    action Delimiter. If there *is* an opening parenthesis, parsing switches
    to the ``function`` lexicon of the same language.

    (See also :func:`bygroup`.)

    """
    predicate = lambda m: not m.group(m.lastindex + n)
    return bymatch(predicate, itemlist, else_itemlist)


def ifmember(sequence, itemlist, else_itemlist=()):
    r"""Return a :class:`~parce.rule.TextRuleItem` that yields ``itemlist`` if
    the text is in sequence.

    If text is not in sequence, ``else_itemlist`` is yielded.

    An example rule::

        keywords = ['foo', 'bar' ,'baz' ,'quux']
        yield r"\b[a-z]+\b", ifmember(keywords, (Keyword, cls.keyword), Name.Variable)

    This rule matches any lowercase word, but marks words in the keywords list
    with the Keyword action, and only for those, switches to the
    ``cls.keyword`` lexicon. Other words get the Name.Variable action.

    """
    def predicate(text):
        return text in sequence
    return rule.TextRuleItem(predicate, else_itemlist, itemlist)


def ifgroupmember(n, sequence, itemlist, else_itemlist=()):
    """Return a :class:`~parce.rule.MatchRuleItem` that yields ``itemlist`` if
    group ``n`` is in sequence.

    If group ``n`` is not in sequence, ``else_itemlist`` is yielded.

    """
    def predicate(m):
        return m.group(m.lastindex + n) in sequence
    return rule.MatchRuleItem(predicate, else_itemlist, itemlist)


def _get_items_map(dictionary, default):
    """Map dictionary items to itemlists, and put their indexes in a new dict.

    Returns a ``get(text)`` callable returning an index for the text and the
    itemlists.

    """
    itemlists = [default]
    d = {}
    for i, (key, value) in enumerate(dictionary.items(), 1):
        d[key] = i
        itemlists.append(value)
    return (lambda t: d.get(t, 0)), itemlists


def maptext(dictionary, default=()):
    r"""Return a :class:`~parce.rule.TextRuleItem` that yields the itemlist
    from the dictionary, using the text as key.

    If the dict does not contain the key, the default value is yielded.

    An example from the LilyPond music language definition::

        RE_LILYPOND_LYRIC_TEXT = r'[^{}"\\\s$#\d]+'
        yield RE_LILYPOND_LYRIC_TEXT, maptext({
            "--": LyricHyphen,
            "__": LyricExtender,
            "_": LyricSkip,
        }, LyricText)

    This matches any text blob, but some text items get their own action.

    """
    predicate, itemlists = _get_items_map(dictionary, default)
    return rule.TextRuleItem(predicate, *itemlists)


def mapgroup(n, dictionary, default=()):
    """Return a :class:`~parce.rule.MatchRuleItem` that yields the itemlist
    from the dictionary, using the specified match group as key.

    If the dict does not contain the key, the default value is yielded.

    """
    get, itemlists = _get_items_map(dictionary, default)
    def predicate(m):
        return get(m.group(m.lastindex + n))
    return rule.MatchRuleItem(predicate, *itemlists)


def bygroup(*actions):
    r"""Return a :class:`~parce.action.SubgroupAction` that yields tokens for
    each subgroup in a regular expression.

    This action uses capturing subgroups in the regular expression pattern
    and creates a Token for every subgroup, with that action. You should
    provide the same number of actions as there are capturing subgroups in
    the pattern. Use non-capturing subgroups for the parts you're not
    interested in, or the special ``skip`` action.

    An example from the CSS language definition::

        yield r"(url)(\()", bygroup(Name, Delimiter), cls.url_function

    If this rule matches, it generates two tokens, one for "url" and the other
    for the opening parenthesis, each with their own action.

    """
    return action.SubgroupAction(*actions)


def withgroup(n, lexicon, mapping=None):
    r"""Return a :class:`~parce.rule.LexiconWithGroup` rule item that calls the
    ``lexicon`` with the matched text from group ``n``.

    Calling a Lexicon creates a derived Lexicon, i.e. one that has the same set
    of rules and the same name, but the patterns and/or rules may differ by
    using ArgRuleItem instances in the rule, which base their replacement
    output on the argument the initial Lexicon was called with.

    If a ``mapping`` dictionary is specified, the matched text from group ``n``
    is used as key, and the result of the mapping (None if not present) gives
    the argument to call the lexicon with.

    """
    return rule.LexiconWithGroup(n, lexicon, mapping)


def withtext(lexicon, mapping=None):
    r"""Return a :class:`~parce.rule.LexiconWithText` rule item that calls the
    ``lexicon`` with the matched text.

    If a ``mapping`` dictionary is specified, the matched text is used as key,
    and the result of the mapping (None if not present) gives the argument to
    call the lexicon with.

    """
    return rule.LexiconWithText(lexicon, mapping)


def witharg(lexicon):
    r"""Return a :class:`~parce.rule.LexiconWithArg` rule item that calls the
    ``lexicon`` with the same argument as the current lexicon.

    """
    return rule.LexiconWithArg(lexicon)


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


