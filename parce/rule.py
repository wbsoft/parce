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
Replacable rule item objects and helper functions.

Instead of a fixed pattern, action and target you can use dynamic rule items,
which are replaced before, during and after lexing the text.

Dynamic rule items can adjust the rule to the lexicon argument, the match
object of the regular expression match (if a rule matches) or the matched text.

Rule items that depend on the lexicon argument are already evaluated *before*
the lexicon is first used. Rule items that depend on the text or the match
object are evaluated *during* lexing when a rule matches. *Dynamic actions*
are evaluated *after* lexing, when generating tokens.

Rule items may not inject arbitrary values in rules; for validation purposes it
must always be clear what kind of items a rule could contain before it is used.
So in most cases a :func:`select` function will be used with a predicate that
returns the index of the item to select.

There are also some helper functions that generate output directly, with no
special behaviour afterwards.

The following rule items and helper functions are available:

"""


import operator
import re

from . import regex
from . import ruleitem


ARG = ruleitem.VariableItem('arg')
"""The lexicon argument.

"""

MATCH = ruleitem.VariableItem('match', (lambda m, n: m.group(m.lastindex + n)))
"""The regular expression match object.

You can access a specific group using :obj:`MATCH(n)`; groups start with 1.
Even :obj:`MATCH(n)[s]` is possible, which yields a slice of the matched text
in group ``n``.

"""

TEXT = ruleitem.VariableItem('text')
"""The matched text.

You can use :obj:`TEXT[n]` to get a slice of the matched text.

"""

def call(predicate, *arguments):
    """Yield the result of calling the predicate with arguments."""
    return ruleitem.call(predicate, *arguments)


def select(index, *items):
    """Yield the item pointed to by the index.

    In most use cases the index will be the result of a predicate function,
    which returns an integer value (or True or False, which evaluate to 1 and 0,
    repectively).

    The following example yields Keyword when the matched text could be found
    in the keywords_list, and otherwise Name.Command::

        keywords_list = ['def', 'class', 'for', 'if', 'else', 'return']
        def predicate(text):
            return text in keywords_list
        select(call(predicate, TEXT), Name.Command, Keyword)

    If the selected item is a list or tuple, it is unrolled when injected
    into the rule.

    """
    return ruleitem.select(index, *items)


def pattern(value):
    """Yield the value (string or None), usable as regular expression.

    If None, the whole rule is skipped. This rule item may only be used as
    the first item in a rule, and of course, it may not depend on the TEXT
    or MATCH variables, but it may depend on the ARG variable (which enables
    you to create patterns that depend on the lexicon argument).

    """
    return ruleitem.pattern(value)


def target(value, *lexicons):
    """Yield either an integer target value, or a (possibly derived) Lexicon.

    Using this rule item you can have one predicate function decide whether to
    push the same lexicon again, or to pop, or to target another lexicon, which
    may also be derived.

    This is how it works: when the value is an integer, it is returned.
    Otherwise the value must be a two-tuple(index, argument). The index then
    selects one of the provided lexicons and the argument (if not None), calls
    the lexicon to get a derived lexicon, which is then yielded as result of
    this rule item.

    Here are some examples::

        target(-1)

    yields -1. And::

        target((1, "bla"), MyLang.lexicon1, MyLang.lexicon2)

    yields ``MyLang.lexicon2("bla")``.

    The following two incantations are equivalent (where n can be any
    expression)::

        target((n, None), MyLang.lexicon1, MyLang.lexicon2)
        select(n, MyLang.lexicon1, MyLang.lexicon2)

    Finally::

        target(call(my_predicate, TEXT), MyLang.lexicon1, MyLang.lexicon2)

    calls ``my_predicate`` with the matched text, and then uses the return
    value to either directly return or choose a lexicon.

    """
    return ruleitem.target(value, *lexicons)


### Helpers that create rule items

def ifeq(a, b, result, else_result=()):
    r"""Yield ``result`` if ``a == b``, else ``else_result``.

    This example selects actions and target based on the contents of the
    second subgroup in the match object::

        yield r'([^\W\d]\w*)\s*([\(\]])', \
            ifeq(MATCH(2), '(',
                 (bygroup(Name.Function, Delimiter), cls.func_call),
                 (bygroup(Name.Variable, Delimiter), cls.subscript))

    """
    return select(call(operator.eq, a, b), else_result, result)


def ifneq(a, b, result, else_result=()):
    r"""Yield ``result`` if ``a != b``, else ``else_result``."""
    return select(call(operator.ne, a, b), else_result, result)


def ifmember(item, sequence, result, else_result=()):
    r"""Yield ``result`` if ``item in sequence``, else ``else_result``.

    Example::

        commands = ['begin', 'end', 'if']
        yield r'\\\w+', ifmember(TEXT[1:], commands, Keyword, Name.Variable)

    This example matches any command that starts with a backslash, e.g.
    ``\begin``, but checks membership in a list without the backslash
    prepended.

    """
    return select(call(operator.contains, frozenset(sequence), item),
        else_result, result)


def ifgroup(n, result, else_result=()):
    """Yield ``result`` if match group ``n`` is not None.

    A regular expression match group is None when the group did not contribute
    to the match. For example, in the first expression the second group is
    None, while in the second expression the second group is the empty string::

        re.match(r'(a)(b)?', "ac").group(2) # → None
        re.match(r'(a)(b?)', "ac").group(2) # → ''

    Shortcut for::

        select(call(operator.ne, MATCH(n), None), else_result, result)

    """
    return select(call(operator.ne, MATCH(n), None), else_result, result)


def gselect(*results, default=()):
    """Yield one of the results if that group contributes to the match.

    For example::

        gselect(arg1, arg2, arg3, arg4, default=default)

    is equivalent to::

        ifgroup(1, arg1,
            ifgroup(2, arg2,
                ifgroup(3, arg3,
                    ifgroup(4, arg4, default))))

    When an ``arg`` is None, that group is skipped, so::

        gselect(arg1, None, arg2, arg3)

    is equivalent to::

        ifgroup(1, arg1,
            ifgroup(3, arg2,
                ifgroup(4, arg3)))

    """
    indices, results = zip(*((i, r) for i, r in enumerate(results, 1) if r is not None))
    indices = list(enumerate(indices))
    default_index = len(results)
    def predicate(m):
        for i, n in indices:
            if m.group(m.lastindex + n) is not None:
                return i
        return default_index
    return select(call(predicate, MATCH), *results, default)


def dselect(item, mapping, default=()):
    r"""Yield the ``item`` from the specified ``mapping`` (dictionary).

    If the item can't be found in the mapping, returns ``default``.

    An example from the LilyPond music language definition::

        RE_LILYPOND_LYRIC_TEXT = r'[^{}"\\\s$#\d]+'
        yield RE_LILYPOND_LYRIC_TEXT, dselect(TEXT, {
            "--": LyricHyphen,
            "__": LyricExtender,
            "_": LyricSkip,
        }, LyricText)

    This matches any text blob, but some text items get their own action.

    """
    d = {}
    items = [default]
    for i, (key, value) in enumerate(mapping.items(), 1):
        d[key] = i
        items.append(value)
    def get_index(text):
        return d.get(text, 0)
    return select(call(get_index, item), *items)


def derive(lexicon, argument):
    r"""Yield a derived lexicon with argument.

    Example::

        yield "['\"]", String, derive(cls.string, TEXT)

    This enters the lexicon ``string`` with a double quote as argument when a
    double quote is encountered, but with a single quote when a single quote
    was encountered.

    (Deriving a lexicon is not possible with the ``call`` statement, because
    that is not allowed as toplevel rule item.)

    """
    return target((0, argument), lexicon)


def findmember(item, pairs, default=()):
    r"""Yield the item corresponding to the first sequence the item is found in.

    The ``pairs`` argument is an iterable of tuples(sequence, result).
    When a sequence contains the item, ``result`` is yielded. When no sequence
    contained the item, ``default`` is yielded.

    The ``pairs`` argument can also be a dictionary, in case the order does not
    matter.

    """
    sequences = []
    items = []
    all_items = set()
    try:
        pairs = pairs.items()   # succeeds if it's a dict
    except AttributeError:
        pass
    for s, i in pairs:
        s = frozenset(set(s) - all_items)
        all_items |= s
        sequences.append(s)
        items.append(i)
    last = len(items)
    items.append(default)
    def predicate(text):
        for i, sequence in enumerate(sequences):
            if text in sequence:
                return i
        return last
    return select(call(predicate, item), *items)


### Pattern helpers


def words(words, prefix="", suffix=""):
    r"""Return an optimized regular expression pattern matching any of the
    words.

    A ``prefix`` or ``suffix`` can be given, which will be added to the regular
    expression. Using the word boundary character ``\b`` as suffix is
    recommended to be sure the match ends at a word end.

    """
    expr = regex.words2regexp(words)
    if prefix or suffix:
        return prefix + '(?:' + expr + ')' + suffix
    return expr


def char(chars, positive=True):
    """Return a regular expression pattern matching one of the characters in
    the specified string.

    If `positive` is False, the set of characters is complemented, i.e. the
    pattern matches any single character that is not in the specified string.

    """
    negate = "" if positive else "^"
    return '[{}{}]'.format(negate, regex.make_charclass(chars))


### Dynamic patterns (depending on ARG)


def arg(escape=True, prefix="", suffix="", default=None):
    r"""Create a pattern that contains the argument the current Lexicon was
    called with.

    If there is no argument in the current lexicon, this
    :class:`~parce.ruleitem.pattern` yields the default value, which is by
    default None, resulting in the rule being skipped.

    When there is an argument, it is escaped using :func:`re.escape` (when
    ``escape`` was set to True), and if given, ``prefix`` is prepended and
    ``suffix`` is appended. When the default value is used, ``prefix`` and
    ``suffix`` are not used.

    """
    def build(arg):
        """Return the lexicon argument as regular expression."""
        if isinstance(arg, str):
            if escape:
                arg = re.escape(arg)
            return prefix + arg + suffix
        return default
    return pattern(call(build, ARG))


def ifarg(pat, else_pat=None):
    r"""Create a pattern that returns the specified regular expression ``pat``
    if the lexicon was called with an argument.

    If there is no argument in the current lexicon, ``else_pat`` is
    yielded, which is None by default, resulting in the rule being skipped.

    """
    return pattern(select(call(bool, ARG), else_pat, pat))


### Dynamic actions


def bygroup(*actions):
    r"""Return a :class:`~parce.ruleitem.SubgroupAction` that yields tokens for
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
    return ruleitem.SubgroupAction(*actions)


def using(lexicon):
    r"""Return a :class:`~parce.ruleitem.DelegateAction` that yields tokens
    using the specified lexicon.

    All tokens are yielded as one group, flattened, ignoring the tree
    structure, so this is not efficient for large portions of text, as the
    whole region is parsed again on every modification.

    But it can be useful when you want to match a not too large text blob first
    that's difficult to capture otherwise, and then lex it with a lexicon that
    does (almost) not enter other lexicons.

    """
    return ruleitem.DelegateAction(lexicon)


### Helper to yield modified rules


def anyof(lexicon, *target):
    """Yield certain rules from the specified ``lexicon``, adding a ``target``.

    Rules that specify a target themselves, and rules starting with
    ``default_action`` or ``default_target``, are skipped. If no ``target`` is
    specified, the ``lexicon`` becomes the target itself (specify ``0`` to
    suppress that).

    So when you use this function in a lexicon ``mylexicon`` like this::

        @lexicon
        def mylexicon(cls):
            yield from anyof(cls.other_lexicon)

        @lexicon
        def other_lexicon(cls):
            yield "patt1", Name.Symbol
            yield "patt2", Delimiter, cls.yet_another_lexicon

    the first rule of ``other_lexicon`` is yielded as::

        ("patt1", Name.Symbol, cls.other_lexicon)

    but the second rule ``"patt2"`` is not yielded, because it has a target
    itself.

    """
    import parce.target
    if not target:
        target = lexicon,
    for pattern, action, *t in lexicon:
        if pattern not in (parce.default_action, parce.default_target) and \
                not parce.target.TargetFactory.make(lexicon, t):
            yield (pattern, action, *target)


