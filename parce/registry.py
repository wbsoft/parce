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

Using the :func:`register` function it is possible to register your own
language definitions at runtime and make them available through parce.
As a service, the bundled languages in ``parce.lang`` are automatically
registered in the global registry.

The global registry is in the :attr:`registry` module variable.
You can also create and populate your own :class:`Registry`.

.. py:data:: registry

   The global default parce :class:`Registry`.

"""


import collections
import fnmatch
import importlib
import itertools
import operator
import re


Entry = collections.namedtuple("Entry", (
    "name",
    "desc",
    "aliases",
    "filenames",
    "mimetypes",
    "guesses",
))
"""
Used to store entries in the Registry dict, using the qualified name of the
root lexicon as the key.
"""
Entry.name.__doc__ = "A human-readable name for the file type."
Entry.desc.__doc__ = "A short description."
Entry.aliases.__doc__ = "A list of other names this lexicon can be found under."
Entry.filenames.__doc__ = \
"""A list of tuples (pattern, weight). A pattern is a plain filename or a
filename with globbing characters, e.g. ``"Makefile"`` or ``"*.c"``, and the
weight is a floating point value indicating the probability that the root
lexicon should be chosen for this filename (0..1 range)."""
Entry.mimetypes.__doc__ = \
"""A list of tuples (mimetype, weight). A mimetype is a string like
``"text/css"``, the weight is a floating point value indicating the probability
that the root lexicon should be chosen for this filename (0..1 range)."""
Entry.guesses.__doc__ = \
"""A list of tuples (regexp, weight). The first 5000 characters of the contents
are matched against the regular expression, and when it matches, the weight is
added to the already computed weight for this root lexicon."""


class Registry(dict):
    """Registry of language definitions.

    The ``Registry`` is based on the Python dictionary class, and maps fully
    qualified lexicon names (such as ``"parce.lang.css.Css.root"``) to
    :class:`Entry` tuples.

    You can specify another Registry as fallback on construction, or set the
    :attr:`fallback` attribute later. The :meth:`find` method uses this
    fallback, if set.

    """

    fallback = None #: Another :class:`Registry` the :meth:`find` method can use.

    def __init__(self, fallback=None):
        super().__init__()
        self.fallback = fallback

    def copy(self):
        """Return a copy of this Registry. Any fallback is reused, not copied."""
        copy = type(self)(self.fallback)
        copy.update(self)
        return copy

    def add(self, lexicon_name, *,
        name,
        desc,
        aliases = (),
        filenames = (),
        mimetypes = (),
        guesses = (),
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

        This method simply creates an :class:`Entry` tuple with all the arguments
        and stores it using the lexicon name as key.

        """
        self[lexicon_name] = Entry(name, desc, aliases, filenames, mimetypes, guesses)

    def suggest(self, filename=None, mimetype=None, contents=None):
        """Return a list of registered language definitions, sorted on relevance.

        The filename has the most weight, if two have the same weight, the mimetype
        is looked at; if still the same, the contents are looked at with some
        heuristic.

        Every item in the returned list is the fully qualified name of the root
        lexicon, e.g. ``"parce.lang.css.Css.root"``.

        """
        weights = collections.defaultdict(int)
        if filename:
            for name in self:
                weight = max((w for pat, w in self[name].filenames
                               if fnmatch.fnmatch(filename, pat)), default=0)
                if weight:
                    weights[name] += weight
        if mimetype:
            for name in self:
                weight = max((w for mtype, w in self[name].mimetypes
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
            names = self.keys()
        if contents:
            contents = contents[:5000]
            for name in names:
                weight = sum(w for regex, w in self[name].guesses
                               if re.search(regex, contents))
                if weight:
                    weights[name] += weight
        return sorted(weights, key=weights.get, reverse=True)

    def qualname(self, name):
        """Find a fully qualified lexicon name for the specified name.

        First, tries to find the exact match on the ``name`` attribute, then
        the aliases, then a case insensitive match, and then the same for the
        Language class name.

        """
        aliases = []
        nocases = []
        classes = []
        name_lowered = name.lower()
        for qualname, entry in self.items():
            if name == entry.name:
                return qualname
            if name in entry.aliases:
                aliases.append(qualname)
            if name_lowered == entry.name.lower() or any(
                    alias.lower() == name_lowered for alias in entry.aliases):
                nocases.append(qualname)
            cls = qualname.rsplit(".", 2)[1]
            if name_lowered == cls.lower():
                classes.append(qualname)
        for qualname in itertools.chain(aliases, nocases, classes):
            return qualname

    @staticmethod
    def lexicon(qualname):
        """Import the module and return the actual lexicon.

        Eg, for the fully qualified ``qualname`` ``"parce.lang.css.Css.root"``,
        imports the ``parce.lang.css`` module and returns the ``Css.root``
        lexicon.

        """
        module, cls, root = qualname.rsplit(".", 2)
        mod = importlib.import_module(module)
        return getattr(getattr(mod, cls), root)

    def find(self, name=None, filename=None, mimetype=None, contents=None):
        """Convenience method to find a root lexicon, either by language name,
        or by filename, mimetype and/or contents.

        If you specify a name, tries to find the language with that name (using
        :meth:`qualname`), ignoring the other arguments.

        If you don't specify a name, but instead one or more of the other
        arguments, tries to find the language based on filename, mimetype or
        contents (using :meth:`suggest`).

        If a language is found, returns the root lexicon (using
        :meth:`lexicon`). If no language could be found, the fallback registry
        is consulted, if set. Ultimately, None is returned (which can also be
        used as root lexicon, resulting in an empty token tree).

        Examples::

            >>> from parce.registry import registry as r
            >>> r.find("xml")
            Xml.root
            >>> r.find(contents='{"key": 123;}')
            Json.root
            >>> r.find(filename="style.css")
            Css.root

        """
        if name:
            def lexicons(reg):
                qualname = reg.qualname(name)
                if qualname:
                    yield reg.lexicon(qualname)
        else:
            def lexicons(reg):
                for qualname in reg.suggest(filename, mimetype, contents):
                    yield reg.lexicon(qualname)
        while self:
            for lexicon in lexicons(self):
                return lexicon
            self = self.fallback


# the global Registry is in the ``registry`` module variable
registry = Registry()


def register(lexicon_name, **kwargs):
    """Register a lexicon in the global registry.

    For all the arguments, see :meth:`Registry.add`.

    """
    registry.add(lexicon_name, **kwargs)


## register the bundled languages

import parce.lang._registry
