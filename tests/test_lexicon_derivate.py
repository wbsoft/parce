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
Test the derived Lexicon(arg) stuff
"""

import sys
sys.path.insert(0, '.')


def test_heredoc():

    from parce import Language, lexicon, root
    from parce.action import Name, Text
    from parce.rule import arg, derive, ARG, MATCH

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r"@([a-z]+)@", Name, derive(cls.here, MATCH[1])
            yield r"\w+", Text

        @lexicon
        def here(cls):
            yield arg(prefix=r"\b", suffix=r"\b"), Name, -1
            yield r"\w+", Text


    text = r""" text @mark@ bla bla mark bla bla """

    tree = root(MyLang.root, text)
    tree.dump()
    assert tree.query.all("mark").pick().is_last()
    assert tree.query.all(MyLang.here).pick()

    from parce.validate import validate_language
    assert validate_language(MyLang)


def test_list():

    from parce import Language, lexicon, root
    from parce.action import Name
    from parce.rule import call, derive, select, ARG, MATCH, TEXT

    def add(words, text):
        """Return a new tuple with text added."""
        new = (text,)
        return words + new if words else new

    def ifknown(text, yes_value, no_value):
        """Return a dynamic rule item returning ``yes_value`` for known ``text``, otherwise ``no_value``."""
        known = lambda text, words: text in words if words else False
        return select(call(known, text, ARG), no_value, yes_value)

    class MyLang(Language):
        @lexicon
        def root(cls):
            yield r"@(\w+)", ifknown(MATCH[1],
                Name.Definition.Invalid,
                (Name.Definition, -1, derive(cls.root, call(add, ARG, MATCH[1]))))
            yield r"\w+", ifknown(TEXT, Name.Constant, Name.Variable)

    text = "bls lhrt sdf @wer gfdh wer iuj @sdf uhj sdf bls @bls bls @sdf @bls"
    tree = root(MyLang.root, text)
    tree.dump()

    from parce.validate import validate_language
    assert validate_language(MyLang)


if __name__ == "__main__":
    test_heredoc()
    test_list()



