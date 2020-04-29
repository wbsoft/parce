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

Besides the classes and functions below, a large amount of *standard actions* is
also available in the ``parce`` module namespace. See for the full list
:doc:`stdactions`.

"""


from . import (
    action, document, lexer, pattern, rule, treebuilder, treedocument, util)
from . import lexicon as lexicon_
from .document import Cursor
from .language import Language
from .pkginfo import version, version_string
from .stdactions import *


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


def words(words, prefix="", suffix=""):
    r"""Return a :class:`~parce.pattern.Words` pattern matching any of the
    words.

    The returned Pattern builds an optimized regular expression matching any of
    the words contained in the `words` list.

    A ``prefix`` or ``suffix`` can be given, which will be added to the regular
    expression. Using the word boundary character ``\b`` as suffix is
    recommended to be sure the match ends at a word end.

    """
    return pattern.Words(words, prefix, suffix)


def char(chars, positive=True):
    """Return a :class:`~parce.pattern.Char` pattern matching one of the
    characters in the specified string.

    If `positive` is False, the set of characters is complemented, i.e. the
    Pattern matches any single character that is not in the specified string.

    """
    return pattern.Char(chars, positive)


def arg(escape=True, prefix="", suffix="", default=None):
    r"""Return an :class:`~parce.pattern.Arg` pattern that contains the
    argument the current Lexicon was called with.

    If there is no argument in the current lexicon, this Pattern yields the
    default value, which is by default None, resulting in the rule being
    skipped.

    When there is an argument, it is escaped using :func:`re.escape` (when
    ``escape`` was set to True), and if given, ``prefix`` is prepended and
    ``suffix`` is appended. When the default value is used, ``prefix`` and
    ``suffix`` are not used.

    """
    return pattern.Arg(escape, prefix, suffix, default)


def ifarg(pattern, else_pattern=None):
    r"""Return an :class:`~parce.pattern.IfArg` pattern yielding the specified
    regular expression pattern (or nested Pattern instance) if the lexicon was
    called with an argument.

    If there is no argument in the current lexicon, ``else_pattern`` is
    yielded, which is None by default, resulting in the rule being skipped.

    """
    return pattern.IfArg(pattern, else_pattern)


def byarg(predicate, *itemlists):
    """Return an :class:`~parce.rule.PredicateArgItem` that chooses its output
    based on the lexicon argument.

    The predicate is called with the lexicon argument (which is None for a
    normal Lexicon, but can have another value for a derivative Lexicon.

    """
    return rule.PredicateArgItem(predicate, *itemlists)


def bymatch(predicate, *itemlists):
    """Return a :class:`~parce.rule.MatchItem` that chooses its output
    based on the match object.

    The returned MatchItem calls the predicate function with the match object
    as argument. The function should return the index of the itemlist to
    choose. If you provide two possible actions, the predicate function may
    also return True or False, in which case True chooses the second itemlist
    and False the first.

    This helper can be used both for action and target objects, or both
    at the same time.

    """
    return rule.MatchItem(predicate, *itemlists)


def bytext(predicate, *itemlists):
    """Return a :class:`~parce.rule.TextItem` that chooses the itemlist
    based on the text.

    The returned TextItem calls the predicate function with the matched text as
    argument.  The function should return the index of the itemlist to choose,
    in the same way as with :func:`~parce.bymatch`.

    This helper can be used both for action and target objects, or both
    at the same time.

    """
    return rule.TextItem(predicate, *itemlists)


def ifgroup(n, itemlist, else_itemlist=()):
    r"""Return a :class:`~parce.rule.MatchItem` that yields ``itemlist`` if
    group n in the match is not None.

    If group ``n`` in the match object is None, ``else_itemlist`` is yielded.
    A match group is None when the group was optional and did not participate
    in the match.

    An example rule::

        yield r"\b([a-z]+)\b(\()?", bygroup(Keyword, Delimiter), ifgroup(2, cls.function)

    This rule matches a word with or without an opening parenthesis after it.
    The words gets the action Keyword, and the parenthesis, if there, gets the
    action Delimiter. If there *is* an opening parenthesis, parsing switches
    to the ``function`` lexicon of the same language.

    (See also :func:`bygroup`.)

    """
    predicate = lambda m: m.group(m.lastindex + n) is None
    return bymatch(predicate, itemlist, else_itemlist)


def ifmember(sequence, itemlist, else_itemlist=()):
    r"""Return a :class:`~parce.rule.TextItem` that yields ``itemlist`` if
    the text is in sequence.

    If text is not in sequence, ``else_itemlist`` is yielded.

    An example rule::

        keywords = ['foo', 'bar' ,'baz' ,'quux']
        yield r"\b[a-z]+\b", ifmember(keywords, (Keyword, cls.keyword), Name.Variable)

    This rule matches any lowercase word, but marks words in the keywords list
    with the Keyword action, and only for those, switches to the
    ``cls.keyword`` lexicon. Other words get the Name.Variable action.

    Internally this helper function creates a frozenset of the sequence, to
    speed up membership testing.

    """
    sequence_set = frozenset(sequence)
    predicate = sequence_set.__contains__
    return bytext(predicate, else_itemlist, itemlist)


def ifgroupmember(n, sequence, itemlist, else_itemlist=()):
    """Return a :class:`~parce.rule.MatchItem` that yields ``itemlist`` if
    group ``n`` is in sequence.

    If group ``n`` is not in sequence, ``else_itemlist`` is yielded.

    Internally this helper function creates a frozenset of the sequence, to
    speed up membership testing.

    """
    sequence_set = frozenset(sequence)
    def predicate(m):
        return m.group(m.lastindex + n) in sequence_set
    return bymatch(predicate, else_itemlist, itemlist)


def _get_sequences_map(pairs, default):
    """Map sequences to itemlists, with a default value.

    Returns a predicate that tries to find text in sequences (the first one
    that has a match is chosen) and the itemlists.

    Optimizes by making a frozenset of each sequence.

    """
    sequences = []
    itemlists = []
    all_items = set()
    try:
        pairs = pairs.items()   # succeeds if it's a dict
    except AttributeError:
        pass
    for s, i in pairs:
        s = frozenset(set(s) - all_items)
        all_items |= s
        sequences.append(s)
        itemlists.append(i)
    last = len(itemlists)
    itemlists.append(default)
    def predicate(text):
        for i, sequence in enumerate(sequences):
            if text in sequence:
                return i
        return last
    return predicate, itemlists


def mapmember(pairs, default=()):
    r"""Return a :class:`~parce.rule.TextItem` that yields ``itemlist`` from
    a pair's itemlist if the text is in the pair's sequence.

    ``pairs`` can be a list of (sequence, itemlist) values, or a (ordered)
    dictionary.

    """
    predicate, itemlists = _get_sequences_map(pairs, default)
    return bytext(predicate, *itemlists)


def mapgroupmember(n, pairs, default=()):
    r"""Return a :class:`~parce.rule.MatchItem` that yields ``itemlist`` from
    a pair's itemlist if the matched group is in the pair's sequence.

    ``pairs`` can be a list of (sequence, itemlist) values, or a (ordered)
    dictionary.

    """
    text_predicate, itemlists = _get_sequences_map(pairs, default)
    def predicate(m):
        return text_predicate(m.group(m.lastindex + n))
    return bymatch(predicate, *itemlists)



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
    r"""Return a :class:`~parce.rule.TextItem` that yields the itemlist
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
    return bytext(predicate, *itemlists)


def mapgroup(n, dictionary, default=()):
    """Return a :class:`~parce.rule.MatchItem` that yields the itemlist
    from the dictionary, using the specified match group as key.

    If the dict does not contain the key, the default value is yielded.

    If you have an optional match group, use None as key value to select
    the case the group was not present in the match.

    """
    get, itemlists = _get_items_map(dictionary, default)
    def predicate(m):
        return get(m.group(m.lastindex + n))
    return bymatch(predicate, *itemlists)


def maparg(dictionary, default=()):
    r"""Return a :class:`~parce.rule.PredicateArgItem` that yields the itemlist
    from the dictionary, using the current lexicon argument as key.

    If the dict does not contain the key, the default value is yielded.

    """
    predicate, itemlists = _get_items_map(dictionary, default)
    return byarg(predicate, *itemlists)


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


def using(lexicon):
    r"""Return a :class:`~parce.action.DelegateAction` that yields tokens
    using the specified lexicon.

    All tokens are yielded as one group, flattened, ignoring the tree
    structure, so this is not efficient for large portions of text, as the
    whole region is parsed again on every modification.

    But it can be useful when you want to match a not too large text blob first
    that's difficult to capture otherwise, and then lex it with a lexicon that
    does (almost) not enter other lexicons.

    """
    return action.DelegateAction(lexicon)


def withgroup(n, lexicon, mapping=None):
    r"""Return a :class:`~parce.rule.LexiconMatchItem` rule item that calls
    the ``lexicon`` with the matched text from group ``n``.

    Calling a Lexicon creates a derived Lexicon, i.e. one that has the same set
    of rules and the same name, but the patterns and/or rules may differ by
    using ArgRuleItem instances in the rule, which base their replacement
    output on the argument the initial Lexicon was called with.

    If a ``mapping`` dictionary is specified, the matched text from group ``n``
    is used as key, and the result of the mapping (None if not present) gives
    the argument to call the lexicon with.

    """
    if mapping:
        def predicate(match):
            return mapping.get(match.group(match.lastindex + n))
    else:
        def predicate(match):
            return match.group(match.lastindex + n)
    return rule.LexiconMatchItem(predicate, lexicon)


def withtext(lexicon, mapping=None):
    r"""Return a :class:`~parce.rule.LexiconTextItem` rule item that calls
    the ``lexicon`` with the matched text.

    If a ``mapping`` dictionary is specified, the matched text is used as key,
    and the result of the mapping (None if not present) gives the argument to
    call the lexicon with.

    """
    predicate = mapping.get if mapping else lambda t: t
    return rule.LexiconTextItem(predicate, lexicon)


def witharg(lexicon):
    r"""Return a :class:`~parce.rule.LexiconArgItem` rule item that calls the
    ``lexicon`` with the current lexicon's argument.

    Use this to get a derived lexicon with the same argument as the current
    lexicon.

    """
    return rule.LexiconArgItem(lexicon)


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
default_action = util.Symbol("default_action")   #: denotes a default action for unmatched text
default_target = util.Symbol("default_target")   #: denotes a default target when no text matches


#: used to suppress generating a token
skip = action.SkipAction()

