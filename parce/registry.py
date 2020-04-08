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

You can use the :func:`suggest` function in this module to find a language
definition for a particular file type. There is basic functionality to pick a
language definition based on file name, mime type and the contents of the file.

Using the :func:`register` function it is also possible to register your own
language definitions at runtime and make them available through parce.

As a service, the bundled languages in ``parce.lang`` are automatically
registered.

"""


import collections
import fnmatch
import importlib
import operator
import re


Item = collections.namedtuple("Item", "name desc filenames mimetypes guesses")


_registry = {}


def register(language, *,
    name,
    desc,
    root_lexicon = "root",
    filenames = [],
    mimetypes = [],
    guesses = [],
):
    """Register or update a Language (or better: a root lexicon) for a particular
    filename (patterns), particular mime types or based on contents of the file.

    """
    key = (language, root_lexicon)
    _registry[key] = Item(name, desc, filenames, mimetypes, guesses)


def suggest(filename=None, mimetype=None, contents=None):
    """Return a list of registered language definitions, sorted on relevance.

    The filename has the most weight, if two have the same weight, the mimetype
    is looked at; if still the same, the contents are looked at with some
    heuristic.

    Every item in the returned list is a tuple of two strings (language,
    root_lexicon), where language is a fully qualified language name (e.g.
    ``"parce.lang.css.Css"``) and the root_lexicon the name of the root
    lexicon, in most cases ``"root"``.

    """
    results = []
    for key, item in _registry.items():
        filename_weight = 0
        if filename:
            for pattern, weight in item.filenames:
                if fnmatch.fnmatch(filename, pattern):
                    filename_weight += weight
        mimetype_weight = 0
        if mimetype:
            for mtype, weight in item.mimetypes:
                if mtype == mimetype:
                    mimetype_weight = max(mimetype_weight, weight)
        total_weight = filename_weight + mimetype_weight
        if total_weight == 0 and contents:
            for regex, weight in item.guesses:
                if re.search(regex, contents[:5000]):
                    total_weight += weight
        if total_weight:
            results.append((key, item, total_weight))
    results.sort(key=operator.itemgetter(2), reverse=True)
    return [key for key, item, weight in results]


def root_lexicon(item):
    """Import the module and return the root lexicon.

    Eg, for the item ("parce.lang.css.Css", "root"); returns the ``Css.root``
    lexicon.

    """
    language, root = item
    module, cls = language.rsplit(".", 1)
    mod = importlib.import_module(module)
    return getattr(getattr(mod, cls), root)


def registered_item(item):
    """Return the stored Item tuple for the specified item.

    The item is a 2-tuple of strings such as returned by the :func:`suggest`
    function, like ``("parce.lang.css.Css", "root")``.

    Returns None if the language definition is not available.

    """
    return _registry.get(item, None)


register("parce.lang.css.Css",
    name = "CSS",
    desc = "Cascading Style Sheet",
    filenames = [("*.css", 1)],
    mimetypes = [("text/css", 1)],
    guesses = [(r'\b@media\b', 0.5), (r'\bdiv\b', 0.1), (r'\bbody\s*\{', 0.4)],
)

register("parce.lang.ini.Ini",
    name = "INI",
    desc = "INI file format",
    filenames = [("*.ini", 1), ("*.cfg", 0.6), ("*.conf", 0.6)],
    mimetypes = [("text/plain", 0.1)],
    guesses = [(r'^\s*\[\w+\]', 0.5), (r"^\s*[#;]", 0.1)],
)

register("parce.lang.json.Json",
    name = "JSON",
    desc = "JavaScript Object Notation format",
    filenames = [("*.json", 1)],
    mimetypes = [("application/json", 1)],
    guesses = [(r'^\s*\{\s*"\w+"\s*:', .7)],
)

register("parce.lang.lilypond.LilyPond",
    name = "LilyPond",
    desc = "LilyPond music typesetter",
    filenames = [("*.ly", 1), ("*.ily", .8), ("*.lyi", .5)],
    mimetypes = [("text/x-lilypond", .8)],
    guesses = [(r'\\version\s*"\d', .8)],
)

register("parce.lang.scheme.Scheme",
    name = "Scheme",
    desc = "Scheme programming language",
    filenames = [("*.scm", 1)],
    mimetypes = [("text/x-script.scheme", 1), ("text/x-script.guile", 1)],
    guesses = [(r'^\s*[;(]', .5), (r'\(define\b', .7)],
)

register("parce.lang.xml.Xml",
    name = "XML",
    desc = "Extensible Markup Language",
    filenames = [("*.xml", 1)],
    mimetypes = [("text/xml", 1), ("application/xml", 1)],
    guesses = [(r'^\s*<\?xml ', 1)],
)

