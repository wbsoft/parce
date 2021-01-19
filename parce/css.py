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
This modules provides StyleSheet, Style, Element and a some utility functions
that help write css properties.

:class:`StyleSheet` represents a list of rules and conditions (nested @-rules)
from a CSS file or string source. (The CSS format is parsed by the Css language
definition in :mod:`parce.lang.css` and transformed to a CSS structure by the
:class:`~parce.lang.css.CssTransform` transform class.)

:class:`Style` represents a resulting list of rules, sorted on specificity, so
that by selecting rules the properties that apply in a certain situation can be
determined and read.

:class:`Element` and :class:`AbstractElement` describe elements in a HTML or
XML document, and can be used to select matching rules in a stylesheet. Element
provides a list-based helper, and AbstractElement can be inherited from to wrap
any tree structure to use with stylesheet rule selectors.

This module is used by the :py:mod:`theme <parce.theme>` module to provide
syntax highlighting themes based on CSS files.

Workflow:

1. Instantiate a StyleSheet from a file or other source. If needed, combine
   multiple StyleSheets using the + operator.

2. Filter conditions out using ``filter_conditions()``, like media,
   supports or document.

3. Get a Style object through the ``style`` property of the StyleSheet.

4. Use a ``select`` method to select rules based on their selectors.

5. Use ``properties()`` to combine the properties of the selected rules to get
   a dictionary of the CSS properties that apply.

Example::

    >>> from parce.css import Element, StyleSheet
    >>> style = StyleSheet.from_file("parce/themes/default.css").style
    >>> e = Element(class_="comment", parent=Element(class_="parce"))
    >>> style.select_element(e).properties()
    {'color': [<Value text='dimgray', color=Color(r=105, g=105, b=105, a=1.0)>],
    'font-family': [<Value text='serif'>], 'font-style': [<Value text='italic'>]}

"""


import collections
import functools
import os
import re
import reprlib

from . import util
from .lang.css import Css, Atrule, Rule, Value
from .transform import transform_text


Condition = collections.namedtuple("Condition", "keyword node style")


def style_query(func):
    """Make a generator method return a new Style/StyleSheet/Atrules object."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return type(self)(list(func(self, *args, **kwargs)))
    return wrapper


class StyleSheet:
    """Represents a list of style rules and conditions.

    Normal CSS rules are translated into a Rule tuple, nested rules
    such as @media, @document and @supports are translated into Condition
    tuples, and other @-rules are put in Atrule tuples.

    A Rule consists of ``selectors`` and ``properties``. The ``selectors``
    are the tokens in a rule before the {. The ``properties`` is a dict
    mapping css property names to the list of tokens representing their
    value.

    A Condition consists of ``keyword``, ``node`` and ``style``; the ``node``
    is Css.atrule context containing all text from the @ upto the opening {.
    The ``style`` is another StyleSheet object representing the nested
    style sheet.

    An Atrule tuple consists of ``keyword`` and ``node``, where the node is the
    Css.atrule context.

    You can combine stylesheets from different files or sources using the +
    operator.

    The ``style`` property returns the Style object representing all combined
    rules, and allowing further queries.  The ``at`` property returns an
    Atrules instance containing the atrules that do not belong to the nested
    at-rules.

    """
    filename = ""   #: our filename, if we were loaded from a file

    def __init__(self, rules=None, filename=""):
        """Initialize a StyleSheet, empty of with the supplied rules/conditions."""
        self.rules = rules or []
        self.filename = filename
        self._imported_filenames = []

    def __repr__(self):
        fnames = ', '.join(map(os.path.basename, self.filenames()))
        return '<{} [{}]>'.format(self.__class__.__name__, fnames)

    @classmethod
    def load_from_data(cls, data):
        """Return a Css.root tree from data, handling the encoding."""
        encoding, data = util.get_bom_encoding(data)
        if not encoding:
            m = re.match(rb'^@charset\s*"(.*?)"', data)
            encoding = m.group(1).decode('latin1') if m else "utf-8"
        try:
            text = data.decode(encoding)
        except (LookupError, UnicodeError):
            text = data.decode('utf-8', 'replace')
        return cls.load_from_text(text)

    @staticmethod
    def load_from_text(text):
        """Return a CSS structure from text."""
        return transform_text(Css.root, text)

    @classmethod
    def load_from_file(cls, filename):
        """Return a CSS structure from filename, handling the encoding."""
        return cls.load_from_data(open(filename, 'rb').read())

    @classmethod
    def from_file(cls, filename, path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a local filename.

        The ``path`` argument is currently unused. If ``allow_import`` is
        False, the @import atrule is ignored.

        """
        css = cls.load_from_file(filename)
        return cls.from_css(css, filename, path, allow_import)

    @classmethod
    def from_text(cls, text, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a string.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        css = cls.load_from_text(text)
        return cls.from_css(css, filename, path, allow_import)

    @classmethod
    def from_data(cls, data, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a bytes string.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        css = cls.load_from_data(data)
        return cls.from_css(css, filename, path, allow_import)

    @classmethod
    def from_css(cls, css, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a CSS structure.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        filenames = {filename}

        def get_import_rules(values):
            """Yield rules from an @import at-rule.

            If the @import rule has a media query after the filename/url,
            one Condition is yielded.

            """
            for n, v in enumerate(values):
                if isinstance(v, Value) and v.text or v.url:
                    fname = v.text or v.url
                    fname = os.path.join(os.path.dirname(filename), fname)
                    # avoid circular @import references
                    if fname not in filenames:
                        filenames.add(fname)
                        icss = cls.load_from_file(fname)
                        values = values[n+1:]
                        if values:
                            # there is probably a media query after the filename
                            s = cls.from_css(icss, fname, path, allow_import)
                            yield Condition("import", values, s)
                        else:
                            self._imported_filenames.append(fname)
                            yield from get_rules(icss)
                    return

        def get_rules(css):
            """Get all CSS rules from the CSS structure, either as Rule or
            as Condition.

            The latter is used when rules can be selected or not depending
            on media, document, supports or import at-rules.

            """
            rules = []

            for rule in css:
                if isinstance(rule, Atrule):
                    # @-rule
                    if rule.keyword == "import":
                        if allow_import:
                            rules.extend(get_import_rules(rule.contents))
                        continue
                    elif isinstance(rule.block, list):
                        # nested @-rule
                        rule = Condition(rule.keyword, rule.contents, cls.from_css(rule.block))
                rules.append(rule)
            return rules

        return cls(get_rules(css), filename)

    def __add__(self, other):
        return type(self)(self.rules + other.rules)

    @style_query
    def filter_conditions(self, keyword, predicate):
        """Return a new StyleSheet object where conditions are filtered out.

        For Condition instances with the specified keyword, the predicate is
        called with the contents of the ``rule`` (the full Atrule) of
        each Condition, and if the return value doesn't evaluate to True, the
        Condition is removed from the resulting set. Conditions with other
        keywords are kept.

        Currently (CSS3), Conditions have the "media", "supports" or "document"
        keyword. @import rules that have a media query after the filename
        are also stored as a Condition.

        For example, this is a crude way to only get the @media rules for
        "screen"::

            filter_conditions("media", lambda rule: "screen" in rule.contents)

        Of course, a better parser for @media expressions could be written :-)

        """
        for r in self.rules:
            if isinstance(r, Condition) and r.keyword == keyword:
                if predicate(r):
                    yield r
            else:
                yield r

    def filenames(self):
        """Return a list of filenames the currently selected rules depend on.

        Our own filename will be the first in the list, and filenames of
        ``@import``-ed rules that are still selected are appended to the list.

        """
        def get_filenames(sheet):
            if sheet.filename:
                yield sheet.filename
            yield from sheet._imported_filenames
            for r in sheet.rules:
                if isinstance(r, Condition) and r.keyword == "import":
                    yield from get_filenames(r.style)
        return list(get_filenames(self))

    @property
    def style(self):
        """Return a Style object with the remaining rules.

        All rules that still are behind a condition, are let through.
        The rules are sorted on specificity.

        """
        def get_rules(rules):
            for r in rules:
                if isinstance(r, Condition):
                    yield from get_rules(r.style.rules)
                elif isinstance(r, Rule):
                    yield r
        rules = sorted(get_rules(self.rules),
            key=lambda rule: calculate_specificity(rule.prelude))
        rules.reverse()
        return Style(rules)

    @property
    def at(self):
        """Return an Atrules object containing the remaining at-rules.

        All rules that still are behind a condition, are let through.

        """
        def get_rules(rules):
            for r in rules:
                if isinstance(r, Condition):
                    yield from get_rules(r.style.rules)
                elif isinstance(r, Atrule):
                    yield r
        return Atrules(list(get_rules(self.rules)))


class Style:
    """Represents the list of rules created by the StyleSheet object.

    All ``select``-methods/properties return a new Style object with the
    narrowed-down selection of rules.

    Use ``properties()`` to get the dictionary of combined properties that
    apply to the selected rules.

    """
    def __init__(self, rules):
        self.rules = rules

    def __repr__(self):
        return '<{} ({} rules)>'.format(self.__class__.__name__, len(self.rules))

    @style_query
    def select_element(self, element):
        """Select the rules that match with Element."""
        for rule in self.rules:
            if element.match(rule.prelude):
                yield rule

    @style_query
    def select_lxml_element(self, element):
        """Select the rules that match with lxml.etree.Element."""
        return self.select_element(LxmlElement(element))

    def properties(self):
        """Return the combined properties of the current set of rules. (Endpoint.)

        Returns a dictionary with the properties. The value of each property
        is a list of Value instances.

        """
        result = {}
        important_properties = set()
        for rule in self.rules:
            for key, value in rule.properties.items():
                important = False
                if value[-1] == '!important':
                    value = value[:-1]
                    important = True
                if key not in result:
                    result[key] = value
                elif important and key not in important_properties:
                    result[key] = value
                    important_properties.add(key)
        return result


class Atrules:
    """Represents the @rules that are not nested, e.g. @page etc."""
    def __init__(self, rules):
        self.rules = rules

    def __repr__(self):
        return '<{} ({} rules)>'.format(self.__class__.__name__, len(self.rules))

    @style_query
    def select(self, *keywords):
        for r in self.rules:
            if r.keyword in keywords:
                yield r


class AbstractElement:
    """Base implementation for an Element object that Style uses for matching.

    You may reimplement this to wrap any tree structure you want to use with
    the css module. You should then implement:

    * ``__init__()``
    * ``get_name()``
    * ``get_parent()``
    * ``get_attributes()``
    * ``get_pseudo_classes()`` (if needed)
    * ``get_pseudo_elements()`` (if needed)
    * ``children()``
    * ``get_child_count()``
    * ``previous_siblings()``
    * ``next_siblings()``

    If you wrap other objects, be sure to reimplement __eq__ and __ne__, to
    compare those objects and not the wrappers, which may be recreated each
    time.

    """

    _pseudo_class = util.Dispatcher()

    def __bool__(self):
        """Always return True."""
        return True

    def __repr__(self):
        attrs = reprlib.repr(self.get_attributes())
        count = self.get_child_count()
        return "<Element {} {} ({} children)>".format(self.get_name(),
            attrs, count)

    def get_name(self):
        """Implement to return the element's name."""
        return ""

    def get_parent(self):
        """Implement to return the parent Element or None."""
        return None

    def get_attributes(self):
        """Implement to return a dictionary of attributes, keys and values are str."""
        return {}

    def get_pseudo_classes(self):
        """Implement to return a list of pseudo classes."""
        return []

    def get_pseudo_elements(self):
        """Implement to return a list of pseudo elements."""
        return []

    def children(self):
        """Implement to yield our children."""
        yield from ()

    def get_child_count():
        """Implement to return the number of children."""
        return 0

    def previous_siblings(self):
        """Implement to yield our previous siblings in backward order."""
        yield from ()

    def next_siblings(self):
        """Implement to yield our next siblings in forward order."""
        yield from ()

    def get_classes(self):
        """Return a tuple of classes, by default from the 'class' attribute.

        The returned tuple may be empty, when there are no class names.

        """
        d = self.get_attributes()
        if d:
            return d.get("class", "").split()
        return ()

    def get_id(self):
        """Return the id or None, by default read from the 'id' attribute."""
        d = self.get_attributes()
        if d:
            return d.get("id")

    def next_sibling(self):
        """Return the next sibling."""
        for e in self.next_siblings():
            return e

    def previous_sibling(self):
        """Return the previous sibling."""
        for e in self.previous_siblings():
            return e

    @_pseudo_class('first-child')
    def is_first_child(self):
        """Return True if we are the first child."""
        return not self.previous_sibling()

    @_pseudo_class('last-child')
    def is_last_child(self):
        """Return True if we are the last child."""
        return not self.next_sibling()

    @_pseudo_class('only-child')
    def is_only_child(self):
        """Return True if we are the only child."""
        return not self.next_sibling() and not self.previous_sibling()

    @_pseudo_class('first-of-type')
    def is_first_of_type(self):
        """Return True if we are the first of our type."""
        name = self.get_name()
        return not any(e.get_name() == name for e in self.previous_siblings())

    @_pseudo_class('last-of-type')
    def is_last_of_type(self):
        """Return True if we are the last of our type."""
        name = self.get_name()
        return not any(e.get_name() == name for e in self.next_siblings())

    @_pseudo_class('empty')
    def is_empty(self):
        """Return True if we have no child elements."""
        return not self.get_child_count()

    def match(self, prelude):
        """Match with a compound selector expression (``prelude`` part of Rule)."""
        return any(self.match_selectors(selectors) for selectors in prelude)

    def match_selectors(self, selectors):
        """Match with a list of selectors with operators in between."""
        selectors = iter(reversed(selectors))
        sel = next(selectors, None)
        if not sel or not self.match_selector(sel):
            return False
        element = self
        operator = next(selectors, None)
        sel = next(selectors, None)
        while operator and sel:
            if operator == ">":
                # parent should match
                element = element.get_parent()
                if element is None or not element.match_selector(sel):
                    return False
            elif operator == " ":
                # an ancestor should match
                element = element.get_parent()
                while element is not None:
                    if element.match_selector(sel):
                        break
                    element = element.get_parent()
                else:
                    return False
            elif operator == "+":
                # immediate sibling should match
                for element in element.previous_siblings():
                    if element.match_selector(sel):
                        break
                    return False
                else:
                    return False
            else: # operator == "~":
                # a sibling should match
                for element in element.previous_siblings():
                    if element.match_selector(sel):
                        break
                else:
                    return False
            operator = next(selectors, None)
            sel = next(selectors, None)
        return True

    def match_selector(self, selector):
        """Match with a single CSS selector dictionary.

        Returns True if the element matches with the selector.

        """
        # class
        classes = self.get_classes()
        if any(c not in classes for c in selector.get('class_selector', ())):
            return False
        # element name?
        if any(n != self.get_name() for n in selector.get('element_selector', ())):
            return False
        # id?
        if any(i != self.get_id() for i in selector.get('id_selector', ())):
            return False
        # attrs?
        attributes = self.get_attributes()
        for attrname, operator, text, flag in selector.get('attribute_selector', ()):
            try:
                value = attributes[attrname]
            except KeyError:
                return False
            if operator and text:
                if flag in ('i', 'I'):
                    text = text.lower()
                    value = value.lower()
                if operator == "=":
                    if text != value:
                        return False
                elif operator == "~=":
                    if text not in value.split():
                        return False
                elif operator == "|=":
                    if text != value and not value.startswith(text + "-"):
                        return False
                elif operator == "^=":
                    if not value.startswith(text):
                        return False
                elif operator == "$=":
                    if not value.endswith(text):
                        return False
                elif operator == "*=":
                    if text not in value:
                        return False

        # pseudo_class?
        pseudo_classes = self.get_pseudo_classes()
        for c, selector_list in selector.get('pseudo_class', ()):
            result = self._pseudo_class(c)
            if result is None:
                if c not in pseudo_classes:
                    return False
            elif result is False:
                return False

        # pseudo_element?
        pseudo_elements = self.get_pseudo_elements()
        for c in selector.get('pseudo_element', ()):
            if c not in pseudo_elements:
                return False
        return True


class Element(AbstractElement, list):
    """Mimic an Element CSS selector rules are matched with.

    Use "class\_" when specifying the class with a keyword argument.
    You can also manipulate the attributes after instantiating.

    """
    def __init__(self, name="", parent=None, pseudo_classes=None, pseudo_elements=None, **attrs):
        super().__init__()
        self.name = name
        self.parent = parent
        self.pseudo_classes = pseudo_classes or []
        self.pseudo_elements = pseudo_elements or []
        self.attrs = attrs
        if "class" not in attrs and "class_" in attrs:
            attrs["class"] = attrs["class_"]
            del attrs["class_"]
        if parent:
            parent.append(self)

    def __eq__(self, other):
        return self is other

    def __ne__(self, other):
        return self is not other

    def get_name(self):
        """Implemented to return the element's name."""
        return self.name

    def get_parent(self):
        """Implemented to return the parent Element or None."""
        return self.parent

    def get_attributes(self):
        """Implemented to return a dictionary of attributes."""
        return self.attrs

    def get_pseudo_classes(self):
        """Implemented to return a list of pseudo classes."""
        return self.pseudo_classes

    def get_pseudo_elements(self):
        """Implemented to return a list of pseudo elements."""
        return self.pseudo_elements

    def children(self):
        """Implemented to yield our children."""
        yield from self

    def get_child_count(self):
        """Implemented to return the number of children."""
        return len(self)

    def previous_siblings(self):
        """Yield our previous siblings in backward order."""
        if self.parent is not None:
            i = self.parent.index(self)
            if i:
                yield from self.parent[i-1::-1]

    def next_siblings(self):
        """Yield our next siblings in forward order."""
        if self.parent is not None:
            i = self.parent.index(self)
            yield from self.parent[i+1:]


class LxmlElement(AbstractElement):
    """An Element wrapping an element from a lxml.etree tree."""
    def __init__(self, element):
        self.e = element

    def get_name(self):
        """Return the element's name."""
        return self.e.tag

    def get_parent(self):
        """Return the parent Element or None."""
        return type(self)(self.e.getparent())

    def get_attributes(self):
        """Return a dictionary of attributes, keys and values are str."""
        return self.e.attrib

    def get_pseudo_classes(self):
        """Implement to return a list of pseudo classes."""
        return []

    def get_pseudo_elements(self):
        """Implement to return a list of pseudo elements."""
        return []

    def children(self):
        """Yield our children."""
        for n in self.e:
            yield type(self)(n)

    def get_child_count(self):
        """Return the number of children."""
        return len(self.e)

    def previous_siblings(self):
        """Yield our previous siblings in backward order."""
        for n in self.e.itersiblings(preceding=True):
            yield type(self)(n)

    def next_siblings(self):
        """Yield our next siblings in forward order."""
        for n in self.e.itersiblings():
            yield type(self)(n)


def calculate_specificity(prelude):
    """Calculate the specificity of the Css rule prelude.

    Returns a three-tuple (ids, clss, elts), where ids is the number of ID
    selectors, clss the number of class, attribute or pseudo-class selectors,
    and elts the number of element or pseudo-elements.

    Currently, does not handle functions like :not(), :is(), although that
    would not be difficult to implement.

    """
    specificities = []
    total = lambda *names: sum(len(selector.get(n, ())) for n in names)
    for selectors in prelude:
        ids = clss = elts = 0
        for selector in selectors:
            if isinstance(selector, dict):
                ids += total('id_selector')
                clss += total('attribute_selector', 'class_selector', 'pseudo_class')
                elts += total('element_selector', 'pseudo_element')
        specificities.append((ids, clss, elts))
    return max(specificities)


def color2hex(color):
    """Return a hexadecimal string with '#' prepended for the Color instance."""
    r, g, b, a = color
    x = "#{:06x}".format(r*65536 + g*256 + b)
    if a < 1:
        x += format(int(a * 255), '02x')
    return x


def quote_if_needed(s):
    """Double-quote the string for CSS if it is not a valid ident-token."""
    if not re.fullmatch(r'[\w-]+', s):
        s = re.sub(r'[\\"]', lambda m: escape(m.group()), s)
        return '"' + s + '"'
    return s


def escape(char):
    """Escape the specified character for CSS."""
    return "".join(r"\{:x} ".format(ord(c)) for c in char)

