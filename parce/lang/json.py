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
JavaScript Object Notation parser.

Numbers become Number tokens, ``true``, ``false`` and ``null`` become
Name.Constant tokens, strings are yielded in ``string`` contexts, with String
tokens and possibily String.Escape tokens for escaped characters.

Objects (``{ ... }``) become ``object`` contexts with alternating ``key`` and
``value`` child contexts. Arrays (``[ ... ]``) become ``array`` contexts.

"""

__all__ = ('Json', 'JsonTransform')

import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import Delimiter, Name, Number, String
from parce.rule import chars, words
from parce.transform import Transform


JSON_CONSTANTS = {
    'true': True,
    'false': False,
    'null': None,
}

JSON_ESCAPE_CHARS = {
    'b': '\b',  # 0x08 Backspace
    'f': '\f',  # 0x0c Form feed
    'n': '\n',  # 0x0a New line
    'r': '\r',  # 0x0d Carriage return
    't': '\t',  # 0x09 Tab
    '"': '"',   # 0x22 Double quote
    '/': '/',   # 0x2f Slash
    '\\': '\\', # 0x5c Backslash character
}

class Json(Language):
    @lexicon
    def root(cls):
        yield from cls.values()

    @classmethod
    def values(cls):
        yield r"\{", Delimiter, cls.object
        yield r"\[", Delimiter, cls.array
        yield '"', String, cls.string
        yield r"-?\d+(?:\.\d+)?(?:[Ee][+-]?\d+)?", Number
        yield words(JSON_CONSTANTS, r'\b', r'\b'), Name.Constant

    @lexicon
    def object(cls):
        yield r"\}", Delimiter, -1
        yield r"\s+", skip
        yield default_target, cls.key

    @lexicon
    def key(cls):
        yield '"', String, cls.string
        yield ":", Delimiter, -1, cls.value

    @lexicon
    def value(cls):
        yield from cls.values()
        yield ",", Delimiter, -1
        yield r"\}", Delimiter, -2

    @lexicon
    def array(cls):
        yield from cls.values()
        yield ",", Delimiter
        yield r"\]", Delimiter, -1

    @lexicon
    def string(cls):
        yield '"', String, -1
        yield r'\\(?:'+ chars(JSON_ESCAPE_CHARS) + '|u[0-9a-fA-F]{4})', String.Escape
        yield default_action, String


class JsonTransform(Transform):
    """Transforms a Json expression tree to the Python equivalent."""
    def root(self, items):
        for value in self.values(items):
            return value

    def values(self, items):
        """Yield values like the Json.values() classmethod generates."""
        for i in items:
            if i.is_token:
                if i.action == Number:
                    n = float(i.text)
                    if n.is_integer():
                        n = int(n)
                    yield n
                elif i.action == Name.Constant:
                    yield JSON_CONSTANTS[i.text]
            else:
                yield i.obj

    def object(self, items):
        return dict(items.grouped_objects("key", "value"))

    def key(self, items):
        for i in items.items("string"):
            return i.obj

    def value(self, items):
        for value in self.values(items):
            return value

    def array(self, items):
        return list(self.values(items))

    def string(self, items):
        if items and items[-1] == '"':
            del items[-1]   # strip closing quote
        def gen():
            for t in items.tokens():
                if t.action is String.Escape:
                    if t.text[1] == 'u':
                        yield chr(int(t.text[2:], 16))
                    else:
                        yield JSON_ESCAPE_CHARS[t.text[1]]
                else:
                    yield t.text
        return ''.join(gen())
