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
Parse DocBook.

"""

__all__ = ('DocBook',)

import re

from parce import Language, lexicon
from parce.lang.xml import Xml, RE_XML_NAME
from parce.rule import MATCH, bygroup, dselect, ifmember
from parce.action import Delimiter, Keyword, Name


class DocBook(Xml):
    """DocBook is also valid Xml."""

    @lexicon(re_flags=re.IGNORECASE)
    def root(cls):
        tag = ifmember(MATCH[2], DOCBOOK_ELEMENTS, Keyword, Name.Tag)
        # copied and modified from Xml to use Keyword for known DB tags
        yield fr'(<\s*?/)\s*({RE_XML_NAME})\s*(>)', bygroup(Delimiter, tag, Delimiter), -1
        yield fr'(<)\s*({RE_XML_NAME})(?:\s*((?:/\s*)?>))?', \
            bygroup(Delimiter, tag, Delimiter), dselect(MATCH[3], {
                None: cls.attrs,        # no ">" or "/>": go to attrs
                ">": cls.tag,           # a ">": go to tag
            })                          # by default ("/>"): stay in context
        yield from super().root


DOCBOOK_ELEMENTS = (
    "abbrev", "abstract", "accel", "acknowledgements", "acronym", "address",
    "affiliation", "alt", "anchor", "annotation", "answer", "appendix",
    "application", "arc", "area", "areaset", "areaspec", "arg", "article",
    "artpagenums", "attribution", "audiodata", "audioobject", "author",
    "authorgroup", "authorinitials", "bibliocoverage", "bibliodiv",
    "biblioentry", "bibliography", "biblioid", "bibliolist", "bibliomisc",
    "bibliomixed", "bibliomset", "biblioref", "bibliorelation", "biblioset",
    "bibliosource", "blockquote", "book", "bridgehead", "callout",
    "calloutlist", "caption", "caution", "chapter", "citation", "citebiblioid",
    "citerefentry", "citetitle", "city", "classname", "classsynopsis",
    "classsynopsisinfo", "cmdsynopsis", "co", "code", "col", "colgroup",
    "collab", "colophon", "colspec", "command", "computeroutput", "confdates",
    "confgroup", "confnum", "confsponsor", "conftitle", "constant",
    "constraint", "constraintdef", "constructorsynopsis", "contractnum",
    "contractsponsor", "contrib", "copyright", "coref", "country", "cover",
    "database", "date", "dedication", "destructorsynopsis", "edition",
    "editor", "email", "emphasis", "entry", "entrytbl", "envar", "epigraph",
    "equation", "errorcode", "errorname", "errortext", "errortype", "example",
    "exceptionname", "extendedlink", "fax", "fieldsynopsis", "figure",
    "filename", "firstname", "firstterm", "footnote", "footnoteref",
    "foreignphrase", "formalpara", "funcdef", "funcparams", "funcprototype",
    "funcsynopsis", "funcsynopsisinfo", "function", "glossary", "glossdef",
    "glossdiv", "glossentry", "glosslist", "glosssee", "glossseealso",
    "glossterm", "group", "guibutton", "guiicon", "guilabel", "guimenu",
    "guimenuitem", "guisubmenu", "hardware", "holder", "honorific",
    "imagedata", "imageobject", "imageobjectco", "important", "index",
    "indexdiv", "indexentry", "indexterm", "info", "informalequation",
    "informalexample", "informalfigure", "informaltable", "initializer",
    "inlineequation", "inlinemediaobject", "interfacename", "issuenum",
    "itemizedlist", "itermset", "jobtitle", "keycap", "keycode", "keycombo",
    "keysym", "keyword", "keywordset", "label", "legalnotice", "lhs",
    "lineage", "lineannotation", "link", "listitem", "literal",
    "literallayout", "locator", "manvolnum", "markup", "mathphrase",
    "mediaobject", "member", "menuchoice", "methodname", "methodparam",
    "methodsynopsis", "modifier", "mousebutton", "msg", "msgaud", "msgentry",
    "msgexplan", "msginfo", "msglevel", "msgmain", "msgorig", "msgrel",
    "msgset", "msgsub", "msgtext", "nonterminal", "note", "olink", "ooclass",
    "ooexception", "oointerface", "option", "optional", "orderedlist", "org",
    "orgdiv", "orgname", "otheraddr", "othercredit", "othername", "package",
    "pagenums", "para", "paramdef", "parameter", "part", "partintro", "person",
    "personblurb", "personname", "phone", "phrase", "pob", "postcode",
    "preface", "primary", "primaryie", "printhistory", "procedure",
    "production", "productionrecap", "productionset", "productname",
    "productnumber", "programlisting", "programlistingco", "prompt",
    "property", "pubdate", "publisher", "publishername", "qandadiv",
    "qandaentry", "qandaset", "question", "quote", "refclass", "refdescriptor",
    "refentry", "refentrytitle", "reference", "refmeta", "refmiscinfo",
    "refname", "refnamediv", "refpurpose", "refsect1", "refsect2", "refsect3",
    "refsection", "refsynopsisdiv", "releaseinfo", "remark", "replaceable",
    "returnvalue", "revdescription", "revhistory", "revision", "revnumber",
    "revremark", "rhs", "row", "sbr", "screen", "screenco", "screenshot",
    "secondary", "secondaryie", "sect1", "sect2", "sect3", "sect4", "sect5",
    "section", "see", "seealso", "seealsoie", "seeie", "seg", "seglistitem",
    "segmentedlist", "segtitle", "seriesvolnums", "set", "setindex",
    "shortaffil", "shortcut", "sidebar", "simpara", "simplelist",
    "simplemsgentry", "simplesect", "spanspec", "state", "step",
    "stepalternatives", "street", "subject", "subjectset", "subjectterm",
    "subscript", "substeps", "subtitle", "superscript", "surname", "symbol",
    "synopfragment", "synopfragmentref", "synopsis", "systemitem", "table",
    "tag", "task", "taskprerequisites", "taskrelated", "tasksummary", "tbody",
    "td", "term", "termdef", "tertiary", "tertiaryie", "textdata",
    "textobject", "tfoot", "tgroup", "th", "thead", "tip", "title",
    "titleabbrev", "toc", "tocdiv", "tocentry", "token", "tr", "trademark",
    "type", "uri", "userinput", "varargs", "variablelist", "varlistentry",
    "varname", "videodata", "videoobject", "void", "volumenum", "warning",
    "wordasword", "xref", "year",
)
