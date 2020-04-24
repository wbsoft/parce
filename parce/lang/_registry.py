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
Registry of built-in language definitions.

This file is imported by the :mod:`parce.registry` module, so that the global
registry contains all the language definitions listed below.

This file is manually updated.

If you add a language definition, add a listing here. The order is not
significant, although it is comfortable to keep the listing here in sorted
order. Carefully check the weights of the guesses in order to to maximize the
guessing accuracy.

"""


from parce.registry import register


register("parce.lang.css.Css.root",
    name = "CSS",
    desc = "Cascading Style Sheet",
    filenames = [("*.css", 1)],
    mimetypes = [("text/css", 1)],
    guesses = [(r'\b@media\b', 0.5), (r'\bdiv\b', 0.1), (r'\bbody\s*\{', 0.4)],
)

register("parce.lang.xml.Dtd.root",
    name = "DTD",
    desc = "Document Type Definition",
    filenames = [("*.dtd", 1)],
    mimetypes = [("application/xml-dtd", 1)],
    guesses = [(r'<!ENTITY\b', 0.5)],
)

register("parce.lang.ini.Ini.root",
    name = "INI",
    desc = "INI file format",
    aliases = ["config"],
    filenames = [("*.ini", 1), ("*.cfg", 0.6), ("*.conf", 0.6)],
    mimetypes = [("text/plain", 0.1)],
    guesses = [(r'^\s*\[\w+\]', 0.5), (r"^\s*[#;]", 0.1)],
)

register("parce.lang.json.Json.root",
    name = "JSON",
    desc = "JavaScript Object Notation format",
    filenames = [("*.json", 1)],
    mimetypes = [("application/json", 1)],
    guesses = [(r'^\s*\{\s*"\w+"\s*:', .7)],
)

register("parce.lang.html.Html.root",
    name = "HTML",
    desc = "HTML (4 or 5)",
    filenames = [("*.html", 1), ("*.htm", 1)],
    mimetypes = [("text/html", 1)],
    guesses = [(r'(?i)<!DOCTYPE html', .9), (r'\bXHTML.*?\bTransitional/', .9),(r'(?i)<html\b', .9)],
)

register("parce.lang.tex.Latex.root",
    name = "LaTeX",
    desc = "TeX and LaTeX",
    aliases = ["TeX"],
    filenames = [("*.tex", 1), ("*.sty", .8), ("*.cls", .1)],
    mimetypes = [("text/x-latex", .8), ("application/x-latex", .8)],
    guesses = [(r'\\document(class|style)\{', .8)],
)

register("parce.lang.lilypond.LilyPond.root",
    name = "LilyPond",
    desc = "LilyPond music typesetter",
    filenames = [("*.ly", 1), ("*.ily", .8), ("*.lyi", .5)],
    mimetypes = [("text/x-lilypond", .8)],
    guesses = [(r'\\version\s*"\d', .8)],
)

register("parce.lang.python.Python.root",
    name = "Python",
    desc = "Python programming language",
    filenames = [("*.py", 1)],
    mimetypes = [("text/x-python", .8)],
    guesses = [(r'^#!.{,20}python', .8), (r'\bimport\s+[a-z]+\b', .3)],
)

register("parce.lang.scheme.Scheme.root",
    name = "Scheme",
    desc = "Scheme programming language",
    aliases = ["guile"],
    filenames = [("*.scm", 1)],
    mimetypes = [("text/x-script.scheme", 1), ("text/x-script.guile", 1)],
    guesses = [(r'^\s*[;(]', .5), (r'\(define\b', .7)],
)

register("parce.lang.toml.Toml.root",
    name = "TOML",
    desc = "Tom's Obvious, Minimal Language",
    filenames = [("*.toml", 1), ("*.tml", .5)],
    mimetypes = [("application/toml", 1)],
    guesses = [(r'^\s*\[\\w+(\.(w+))*\]', 0.5), (r"^\s*#", 0.05)],
)

register("parce.lang.html.XHtml.root",
    name = "XHTML",
    desc = "HTML that is valid XML",
    filenames = [("*.html", 1), ("*.htm", 1), ("*.xhtml", 1)],
    mimetypes = [("text/html", 1), ("application/xhtml+xml", 1)],
    guesses = [(r'(?i)<!DOCTYPE html', .8), (r'\bXHTML.*?\bStrict/', .9),(r'(?i)<html\b', .8)],
)

register("parce.lang.xml.Xml.root",
    name = "XML",
    desc = "Extensible Markup Language",
    aliases = ['sgml'],
    filenames = [("*.xml", 1)],
    mimetypes = [("text/xml", 1), ("application/xml", 1)],
    guesses = [(r'^\s*<\?xml ', 1)],
)

