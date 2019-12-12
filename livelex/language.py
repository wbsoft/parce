# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python module.
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



class Lexicon:
    """A Lexicon defines a series of pattern rules to look for.

    A Lexicon has two levels of existence: it is defined in a Language class
    and unbound when referred to from within the same class definition.
    
    As soon as a Lexicon is referred to from outside, via the class object,
    it acts as a descriptor and creates a copy for that class object.
    
    Target Lexicons in rules are automatically bound to the same language as
    the current Lexicon.


    """
    def __get__(self, instance, owner):
        """Called when accessed as a descriptor, via a class."""
        #if instance:
        #    raise RuntimeError('Language should never be instantiated')
        try:
            return self._lexicons[owner]
        except AttributeError:
            self._lexicons = {}
        except KeyError:
            pass
        lexicon = self._lexicons[owner] = type(self)(self._rules, self._default_target)
        lexicon._language = owner
        return lexicon

    def __init__(self, rules=None, default_target=None):
        self._rules = []
        if rules is not None:
            self._rules.extend(rules)
        self._default_target = default_target
        self._language = None

    def __repr__(self):
        if self._language is None:
            return '<unbound Lexicon at 0x{:x}>'.format(id(self))
        return "<Lexicon of '{0}' at 0x{1:x}>".format(self._language.__name__, id(self))

    def add_rule(self, token, pattern, *targets):
        """Add a rule."""
        self._rules.append((token, pattern, targets))
    
    def add_rules(self, rules):
        """Add multiple rules at once."""
        self._rules.extend(rules)

    def rules(self):
        """Return a list of rules. Unbound target lexicons are bound to our lexicon."""
        if self._language is None:
            return self._rules[:]
        rules = []
        Lexicon = type(self)
        for token, pattern, targets in self._rules:
            newtargets = []
            for t in targets:
                if isinstance(t, Lexicon) and t._language is None:
                    t = t.__get__(None, self._language)
                newtargets.append(t)
            rules.append((token, pattern, tuple(newtargets)))
        return rules

    def parse(self, text, pos):
        """Yield (matchobj, target) tuples. Target can be None or a new Lexicon."""


class Language:
    """A Language represents a set of Lexicons comprising a specific language.
    
    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.
    
    
    
    """
    root = Lexicon()
    string = Lexicon()
    music = Lexicon()
    
    root.add_rule('music', r'\b[a-g]\b')
    root.add_rule('string', r'"', string)
    root.add_rule('music', r'\b[a-g]\b', music)
    root.add_rule('music', r'\b[a-g]\b', music)

class LanguageB(Language):
    pass
