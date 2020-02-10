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


import parce.action
import parce.target
from parce.lexicon import LexiconDescriptor, Lexicon


class Language:
    """A Language represents a set of Lexicons comprising a specific language.

    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.

    """

    @classmethod
    def comment_common(cls):
        """Highlights TODO, XXX and TEMP inside comments using Comment.Alert."""
        yield r"\b(XXX|TODO|TEMP)\b", parce.Comment.Alert
        yield parce.default_action, parce.Comment


def lexicons(lang):
    """Return a list of all the lexicons on the language."""
    lexicons = []
    for key, value in lang.__dict__.items():
        if isinstance(value, LexiconDescriptor):
            lexicons.append(getattr(lang, key))
    return lexicons


def standardactions(lang):
    """Return the set of all the StandardAction instances in the language.

    Does not follow targets to other languages.

    """
    def std_actions(a):
        if isinstance(a, parce.action.DynamicAction):
            for a in a.actions:
                yield from std_actions(a)
        elif isinstance(a, parce.action.StandardAction):
            yield a

    def get_actions():
        for lex in lexicons(lang):
            for pattern, action, *rest in lex():
                if pattern is parce.default_target:
                    continue
                yield from std_actions(action)
    return set(get_actions())


def languages(lang):
    """Return the set of all languages that this language refers to.

    Does not follow targets from languages that are referred to.

    """
    langs = set()
    def target_lexicons(target):
        for t in target:
            if isinstance(t, Lexicon):
                yield t
            elif isinstance(t, parce.target.DynamicTarget):
                for target in t.targets:
                    yield from target_lexicons(target)

    for lex in lexicons(lang):
        for pattern, action, *target in lex():
            if pattern is parce.default_target:
                target = (action, *target)
            for lx in target_lexicons(target):
                if lx.language is not lang:
                    langs.add(lx.language)
    return langs

