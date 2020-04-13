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
Registry of language definitions.

Instead of importing language definitions directly, you can use a Registry to
manage and find language definitions.

The registry stores the fully qualified name for a root lexicon, for example
``"parce.lang.css.Css.root"``. This qualified name should have at least 2 dots,
to separate module name, class name and the name of the root lexicon.

Use :func:`find` to find a language definition by name, or :func:`suggest` to
find a language definition for a particular file type. There is basic
functionality to pick a language definition based on file name, mime type
and/or the contents of the file.

Using the :func:`register` function it is possible to register your own
language definitions at runtime and make them available through parce.
As a service, the bundled languages in ``parce.lang`` are automatically
registered in the global registry.

The global Registry is in the ``registry`` module variable.
You can also create and populate your own :class:`Registry`.
"""


import collections
import fnmatch
import importlib
import itertools
import operator
import re


Item = collections.namedtuple("Item", (
    "name",
    "desc",
    "aliases",
    "filenames",
    "mimetypes",
    "guesses",
))


class Registry:
    """Registry of language definitions."""
    def __init__(self):
        self._registry = {}

    def copy(self):
        """Return a copy of the registry."""
        r = type(self)()
        r._registry.update(self._registry)
        return r

    def register(self, lexicon_name, *,
        name,
        desc,
        aliases = [],
        filenames = [],
        mimetypes = [],
        guesses = [],
    ):
        """Register or update a Language's root lexicon for a particular filename
        (patterns), particular mime types or based on contents of the file.

        The arguments:

        ``lexicon_name``
            The fully qualified name of a root lexicon, e.g.
            ``"parce.lang.css.Css.root"``. Must contain at least two dots.
        ``name``
            A human-readable name for the file type
        ``desc``
            A short description
        ``aliases``
            An optional list of other names this lexicon can be found under.
        ``filenames``
            A list of tuples (pattern, weight). A pattern is a plain filename or a
            filename with globbing characters, e.g. ``"Makefile"`` or ``"*.c"``,
            and the weight is a floating point value indicating the probability
            that the root lexicon should be chosen for this filename (0..1 range).
        ``mimetypes``
            A list of tuples (mimetype, weight). A mimetype is a string like
            ``"text/css"``, the weight is a floating point value indicating the
            probability that the root lexicon should be chosen for this filename
            (0..1 range).
        ``guesses``
            A list of tuples (regexp, weight). The first 5000 characters of the
            contents are matched against the regular expression, and when it
            matches, the weight is added to the already computed weight for this
            root lexicon.

        """
        self._registry[lexicon_name] = Item(
                    name, desc, aliases, filenames, mimetypes, guesses)

    def suggest(self, filename=None, mimetype=None, contents=None):
        """Return a list of registered language definitions, sorted on relevance.

        The filename has the most weight, if two have the same weight, the mimetype
        is looked at; if still the same, the contents are looked at with some
        heuristic.

        Every item in the returned list is the fully qualified name of the root
        lexicon, e.g. ``"parce.lang.css.Css.root"``.

        """
        reg = self._registry
        weights = collections.defaultdict(int)
        if filename:
            for name in reg:
                weight = max((w for pat, w in reg[name].filenames
                               if fnmatch.fnmatch(filename, pat)), default=0)
                if weight:
                    weights[name] += weight
        if mimetype:
            for name in reg:
                weight = max((w for mtype, w in reg[name].mimetypes
                               if mtype == mimetype), default=0)
                if weight:
                    weights[name] += weight

        # check the contents only if no filename/mimetype matched
        # or there were multiple matches with the same weight
        if weights:
            names = sorted(weights, key=weights.get, reverse=True)
            if len(names) == 1 or weights[names[0]] > weights[names[1]]:
                return names
        else:
            names = reg.keys()
        if contents:
            contents = contents[:5000]
            for name in names:
                weight = sum(w for regex, w in reg[name].guesses
                               if re.search(regex, contents))
                if weight:
                    weights[name] += weight
        return sorted(weights, key=weights.get, reverse=True)

    def registered_item(self, lexicon_name):
        """Return the stored Item tuple for the specified ``lexicon_name``.

        The Item tuple has the same attributes as the arguments of the
        :func:`register` function.

        Returns None if the language definition is not available.

        """
        return self._registry.get(lexicon_name, None)

    def find(self, name):
        """Find a fully qualified lexicon name for the specified name.

        First, tries to find the exact match on the ``name`` attribute, then
        the aliases, then a case insensitive match, and then the same for the
        Language class name.

        """
        aliases = []
        nocases = []
        classes = []
        name_lowered = name.lower()
        for lexicon_name, item in self._registry.items():
            if name == item.name:
                return lexicon_name
            if name in item.aliases:
                aliases.append(lexicon_name)
            if name_lowered == item.name.lower() or any(
                    alias.lower() == name_lowered for alias in item.aliases):
                nocases.append(lexicon_name)
            cls = lexicon_name.rsplit(".", 2)[1]
            if name_lowered == cls.lower():
                classes.append(lexicon_name)
        for lexicon_name in itertools.chain(aliases, nocases, classes):
            return lexicon_name

    def rename(self, lexicon_name, new_name=None):
        """Rename the registration of an exiting lexicon.

        This can be useful if you want to override a bundled language definition
        and use your version.

        If you don't specify a new name, the existing registration is removed.

        """
        try:
            old = self._registry.pop(lexicon_name)
            if new_name:
                _registry[new_name] = old
        except KeyError:
            pass


#: the global Registry is in the ``registry`` module variable
registry = Registry()


def register(lexicon_name, **kwargs):
    """:meth:`~Registry.register` a lexicon in the global registry."""
    registry.register(lexicon_name, **kwargs)


def suggest(filename=None, mimetype=None, contents=None):
    """:meth:`~Registry.suggest` zero or more lexicons from the global registry."""
    return registry.suggest(filename, mimetype, contents)


def find(name):
    """:meth:`~Registry.find` a lexicon by name from the global registry."""
    return registry.find(name)


def root_lexicon(lexicon_name):
    """Import the module and return the root lexicon.

    Eg, for the ``lexicon_name`` ``"parce.lang.css.Css.root"`` imports the
    ``parce.lang.css`` module and returns the ``Css.root`` lexicon.

    """
    module, cls, root = lexicon_name.rsplit(".", 2)
    mod = importlib.import_module(module)
    return getattr(getattr(mod, cls), root)




## register the bundled languages

import parce.lang._registry
