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
This modules provides StyleSheet, Style, Element and a bunch of utility
functions that help reading from a tree structure parsed by the
parce.lang.css module.

StyleSheet represents a list of rules and conditions (nested @-rules) from a
CSS file or string source.

Style represents a resulting list of rules, sorted on specificity, so that
by selecting rules the properties that apply in a certain situation can be
determined and read.

Element and AbstractElement describe elements in a HTML or XML document, and
can be used to select matching rules in a stylesheet. Element provides a
list-based helper, and AbstractElement can be inherited from to wrap any tree
structure to use with stylesheet rule selectors.

This module is used by the :py:mod:`theme <parce.theme>` module to provide
syntax highlighting themes based on CSS files.

Workflow:

    1. Instantiate a StyleSheet from a file or other source. If needed,
       combine multiple StyleSheets using the + operator.

    2. Filter conditions out using ``filter_conditions()``, like media,
       supports or document.

    3. Get a Style object through the ``style`` property of the StyleSheet.

    4. Use a ``select`` method to select rules based on their selectors.

    5. Use ``properties()`` to combine the properties of the selected
       rules to get a dictionary of the CSS properties that apply.

Example::

    >>> from parce.css import Element, StyleSheet
    >>> style = StyleSheet.from_file("parce/themes/default.css").style
    >>> e = css.Element(class_="comment", parent=css.Element(class_="parce"))
    >>> style.select_element(e).properties()
    {'color': [<Value text='dimgray'>], 'font-family': [<Value text='serif'>],
    'font-style': [<Value text='italic'>]}

"""


import collections
import functools
import os
import re

from . import *
from . import util
from .lang.css import Css
from .query import Query


Atrule = collections.namedtuple("Atrule", "keyword node")
Condition = collections.namedtuple("Condition", "keyword node style")
Rule = collections.namedtuple("Rule", "selectors properties")
Color = collections.namedtuple("Color", "r g b a")


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
        """Return a Css.root tree from text."""
        return root(Css.root, text)

    @classmethod
    def load_from_file(cls, filename):
        """Return a Css.root tree from filename, handling the encoding."""
        return cls.load_from_data(open(filename, 'rb').read())

    @classmethod
    def from_file(cls, filename, path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a local filename.

        The ``path`` argument is currently unused. If ``allow_import`` is
        False, the @import atrule is ignored.

        """
        tree = cls.load_from_file(filename)
        return cls.from_tree(tree, filename, path, allow_import)

    @classmethod
    def from_text(cls, text, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a string.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        tree = cls.load_from_text(text)
        return cls.from_tree(tree, filename, path, allow_import)

    @classmethod
    def from_data(cls, data, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a bytes string.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        tree = cls.load_from_data(data)
        return cls.from_tree(tree, filename, path, allow_import)

    @classmethod
    def from_tree(cls, tree, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a parsed tree.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        filenames = {filename}

        def get_properties(rule):
            """Get the properties dict from a Css.rule context node.

            The returned dict maps keys to (important, value) tuples,
            where important is True when !important was encountered in the
            property declaration, and value is a list of Value instances
            representing the value of the property.

            """
            properties = {}
            for declaration in rule.query.children(Css.declaration):
                propname = get_ident_token(declaration[0])
                value = declaration[2:] if declaration[1] == ":" else declaration[1:]
                important = "!important" in value
                value = list(Value.read(value))
                if value:
                    properties[propname] = (important, value)
            return properties

        def get_import_rules(node):
            """Yield rules from an @import at-rule.

            If the @import rule has a media query after the filename/url,
            one Condition is yielded.

            """
            for s in node.query.children(Css.dqstring, Css.sqstring, Css.url_function):
                fname = get_url(s) if s == Css.url_function else get_string(s)
                fname = os.path.join(os.path.dirname(filename), fname)
                # avoid circular @import references
                if fname not in filenames:
                    filenames.add(fname)
                    itree = cls.load_from_file(fname)
                    if any(n !=';' for n in remove_comments(s.next_siblings())):
                        # there is probably a media query after the filename
                        s = cls.from_tree(itree, fname, path, allow_import)
                        yield Condition("import", node, s)
                    else:
                        self._imported_filenames.append(fname)
                        yield from get_rules(itree)
                return

        def get_rules(tree):
            """Get all CSS rules from the tree, either as Rule or as Condition.

            The latter is used when rules can be selected or not depending
            on media, document, supports or import at-rules.

            """
            rules = []
            for node in tree.query.children(Css.atrule, Css.prelude):
                if node.lexicon is Css.atrule:
                    # handle @-rules
                    if node and node[0].is_context and node[0].lexicon is Css.atrule_keyword:
                        keyword = get_ident_token(node[0])
                        if keyword == "import":
                            if allow_import:
                                rules.extend(get_import_rules(node))
                        elif node[-1].lexicon is Css.atrule_nested:
                            s = cls.from_tree(node[-1][-1], filename, path, allow_import)
                            rules.append(Condition(keyword, node, s))
                        else:
                            # other @-rule
                            rules.append(Atrule(keyword, node))
                elif len(node) > 1:   # Css.prelude
                    # get the selectors (without ending { )
                    selectors = list(remove_comments(node[:-1]))
                    rule = node.right_sibling()
                    if selectors and rule:
                        properties = get_properties(rule)
                        if properties:
                            rules.append(Rule(selectors, properties))
            return rules
        return cls(get_rules(tree), filename)

    def __add__(self, other):
        return type(self)(self.rules + other.rules)

    @style_query
    def filter_conditions(self, keyword, predicate):
        """Return a new StyleSheet object where conditions are filtered out.

        For Condition instances with the specified keyword, the predicate is
        called with the contents of the ``node`` (the full Css.atrule node) of
        each Condition, and if the return value doesn't evaluate to True, the
        Condition is removed from the resulting set. Conditions with other
        keywords are kept.

        Currently (CSS3), Conditions have the "media", "supports" or "document"
        keyword. @import rules that have a media query after the filename
        are also stored as a Condition.

        For example, this is a crude way to only get the @media rules for
        "screen"::

            filter_conditions("media", lambda node: any(node.query.all("screen")))

        Of course, a better parser for @media expressions could be written :-)

        """
        for r in self.rules:
            if isinstance(r, Condition) and r.keyword == keyword:
                if predicate(r.node):
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
            key=lambda rule: calculate_specificity(rule.selectors))
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

    @style_query
    def select_element(self, element):
        """Select the rules that match with Element."""
        for rule in self.rules:
            if element.match(rule.selectors):
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
            for key, (important, value) in rule.properties.items():
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

    def match_selector(self, selector):
        """Match with a single CSS selector (Css.selector Context).

        Returns True if the element matches with the selector.

        """
        q = selector.query.children
        # class?
        classes = self.get_classes()
        for c in q(Css.class_selector):
            if get_ident_token(c) not in classes:
                return False
        # element name?
        c = q(Css.element_selector).pick()
        if c and get_ident_token(c) != self.get_name():
            return False
        # id?
        c = q(Css.id_selector).pick()
        if c and get_ident_token(c) != self.get_id():
            return False
        # attrs?
        attributes = self.get_attributes()
        for c in q(Css.attribute_selector):
            if c and c[0].lexicon is Css.attribute:
                attrname = get_ident_token(c[0])
                try:
                    value = attributes[attrname]
                except KeyError:
                    return False
                operator = c.query.children.action(Delimiter.Operator).pick()
                if operator:
                    v = operator.right_sibling()
                    if v:
                        if v.is_context:
                            v = get_ident_token(v)
                        elif v in ("'", '"') and v.right_sibling():
                            v = get_string(v.right_sibling())
                        else:
                            v = v.text
                        if len(c) > 4 and c[-2].is_context and \
                                get_ident_token(c[-2]).lower() == "i":
                            # case insensitive
                            v = v.lower()
                            value = value.lower()
                        if operator == "=":
                            if v != value:
                                return False
                        elif operator == "~=":
                            if v not in value.split():
                                return False
                        elif operator == "|=":
                            if v != value and not value.startswith(v + "-"):
                                return False
                        elif operator == "^=":
                            if not value.startswith(v):
                                return False
                        elif operator == "$=":
                            if not value.endswith(v):
                                return False
                        elif operator == "*=":
                            if v not in value:
                                return False
        # pseudo_class?
        pseudo_classes = self.get_pseudo_classes()
        switch = {
            "first-child": self.is_first_child,
            "last-child": self.is_last_child,
            "only-child": self.is_only_child,
            "first-of-type": self.is_first_of_type,
            "last-of-type": self.is_last_of_type,
            "empty": self.is_empty,
        }
        for c in q(Css.pseudo_class):
            v = get_ident_token(c)
            method = switch.get(v)
            if method:
                if not method():
                    return False
            elif v not in pseudo_classes:
                return False
        # pseudo_element?
        pseudo_elements = self.get_pseudo_elements()
        for c in q(Css.pseudo_element):
            if get_ident_token(c) not in pseudo_elements:
                return False
        return True

    def is_first_child(self):
        """Return True if we are the first child."""
        return not self.previous_sibling()

    def is_last_child(self):
        """Return True if we are the last child."""
        return not self.next_sibling()

    def is_only_child(self):
        """Return True if we are the only child."""
        return not self.next_sibling() and not self.previous_sibling()

    def is_first_of_type(self):
        """Return True if we are the first of our type."""
        name = self.get_name()
        return not any(e.get_name() == name for e in self.previous_siblings())

    def is_last_of_type(self):
        """Return True if we are the last of our type."""
        name = self.get_name()
        return not any(e.get_name() == name for e in self.next_siblings())

    def is_empty(self):
        """Return True if we have no child elements."""
        return not self.get_child_count()

    def match(self, selectors):
        """Match with a compound selector expression (``selectors`` part of Rule)."""
        if not selectors:
            return True
        # selector list?
        try:
            i = selectors.index(",")
        except ValueError:
            pass
        else:
            return self.match(selectors[:i]) or self.match(selectors[i+1:])
        selectors = iter(reversed(selectors))
        sel = next(selectors)
        if not sel.is_context or not self.match_selector(sel):
            return False
        element = self
        operator = next(selectors, None)
        while operator:
            if operator.is_context:
                sel = operator
                operator = " "
            else:
                sel = next(selectors, None)
                if not sel:
                    return False
            # handle operator
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
    def __init__(self, e):
        self.element = e

    def get_name(self):
        """Implement to return the element's name."""
        return self.e.tag

    def get_parent(self):
        """Implement to return the parent Element or None."""
        return type(self)(self.e.getparent())

    def get_attributes(self):
        """Implement to return a dictionary of attributes, keys and values are str."""
        return self.e.attrib

    def get_pseudo_classes(self):
        """Implement to return a list of pseudo classes."""
        return []

    def get_pseudo_elements(self):
        """Implement to return a list of pseudo elements."""
        return []

    def children(self):
        """Implemented to yield our children."""
        for n in self.e:
            yield type(self)(n)

    def get_child_count(self):
        """Implemented to return the number of children."""
        return len(self.e)

    def previous_siblings(self):
        """Implement to yield our previous siblings in backward order."""
        for n in self.e.itersiblings(preceding=True):
            yield type(self)(n)

    def next_siblings(self):
        """Implement to yield our next siblings in forward order."""
        for n in self.e.itersiblings():
            yield type(self)(n)


class Value:
    """A value read from a property.

    A Value can represent a:

        * ``text``  (an ident-token or a quoted string (``quoted`` is True then))
        * a ``number`` with an optional unit (like 210px)
        * a ``url``
        * a color  (named, hex or function; use ``get_color()`` to get it)
        * a function (``funcname`` has the name, ``arguments`` the arg Value instances)
        * an ``operator`` (``'+'``, ``'-'`` * or ``'/'``, only as function arguments.
          Or ``'('``, in which case the arguments have the values that were
          between the parentheses.)

    Most value types can be directly read from the corresponding attribute.
    When the value should represent a color, call ``get_color()``

    ``calc()`` or ``var()`` evaluation is not yet implemented.

    """
    def __init__(self,
            text = None,
            number = None,
            unit = None,
            url = None,
            color = None,
            funcname = None,
            operator = None,
            quoted = None,
            arguments = (),
            ):
        self.text = text
        self.number = number
        self.unit = unit
        self.url = url
        self.color = color
        self.funcname = funcname
        self.operator = operator
        self.quoted = quoted
        self.arguments = list(arguments)

    def __repr__(self):
        def gen():
            for name, value in self.__dict__.items():
                if value not in (None, []):
                    yield '{}={}'.format(name, repr(value))
        return '<{} {}>'.format(self.__class__.__name__, ', '.join(gen()))

    @classmethod
    def read(cls, nodes):
        """Read zero or more properties from the specified nodes."""
        nodes = iter(nodes)
        n = next(nodes, None)
        while n:
            if n.is_token:
                if n == ')':
                    return
                elif n == '(':
                    # inside a function we can find parentheses
                    n = next(nodes, None)
                    if n == Css.function:
                        yield cls(operator='(', arguments=cls.read(n))
                elif n.action is String:
                    val = get_string(next(nodes))
                    yield cls(text=val, quoted=True)
                elif n.action is Number:
                    val = float(n.text)
                    if val.is_integer():
                        val = int(val)
                    n = next(nodes, None)
                    if n == Css.unit:
                        unit = get_ident_token(n)
                        yield cls(number=val, unit=unit)
                    else:
                        yield cls(number=val)
                        continue
                elif n == "url":
                    if next(nodes, None): # (
                        target = next(nodes, None)
                        if target:
                            yield cls(url=get_url(target))
                elif n.action is Literal.Color:
                    yield cls(color=n.text)
                elif n.action is Delimiter.Operator:
                    yield cls(operator=n.text)
            elif n == Css.identifier:
                t = get_ident_token(n)
                if t.endswith('('):
                    n = next(nodes, None)
                    yield cls(funcname=t[:-1], arguments=cls.read(n) if n == Css.function else ())
                else:
                    yield cls(text=t)
            n = next(nodes, None)

    def get_num_color_value(self, max_value=255):
        """Return our color num value 0-255 or percentage value. -1 on failure."""
        if self.number is not None:
            num = self.number
            if self.unit == "%":
                num = num * max_value // 100
            if 0 <= num <= max_value:
                return num
        return -1

    def get_color(self):
        """Return a named four-tuple Color(r, g, b, a) describing color and alpha.

        The r, g, b values are in the range 0..255, a in 0..1; 1.0 is fully
        opaque. None is returned if the color was not valid.

        """
        r, g, b, a = -1, -1, -1, 1.0
        if self.color:
            # hexadecimal color like "#FA0042"
            l = len(self.color) - 1
            c = int(self.color[1:], 16)
            if l == 3:
                # 17F -> 1177FF
                r = (c // 256 & 15) * 17
                g = (c // 16 & 15) * 17
                b = (c & 15) * 17
            elif l == 4:
                # fourth digit is alpha value
                r = (c // 4096 & 15) * 17
                g = (c // 256 & 15) * 17
                b = (c // 16 & 15) * 17
                a = (c & 15) * 17 / 255
            elif l == 6:
                # six digits
                r = c // 65536 & 255
                g = c // 256 & 255
                b = c & 255
            else: # l == 8:
                # eight digits: last two is alpha value
                r = c // 16777216 & 255
                g = c // 65536 & 255
                b = c // 256 & 255
                a = (c & 255) / 255
        elif self.text:
            # named color like "dodgerblue"
            if self.text == "transparent":
                r, g, b, a = 0, 0, 0, 0
            else:
                import parce.lang.css_words
                try:
                    r, g, b = parce.lang.css_words.CSS3_NAMED_COLORS[self.text]
                except KeyError:
                    pass
        elif self.funcname in ("rgb", "rgba"):
            # rgb() or rgba()
            if len(self.arguments) > 3:
                a = self.arguments[-1].get_num_color_value(1.0)
            r = self.arguments[0].get_num_color_value()
            g = self.arguments[1].get_num_color_value()
            b = self.arguments[2].get_num_color_value()
        # TODO: implement hsl/hsla (using colorsys)
        c = Color(r, g, b, a)
        if -1 not in c:
            return c


def remove_comments(nodes):
    """Yield the nodes with comments removed."""
    for n in nodes:
        if (n.is_token and n.action is Comment) or (
            n.is_context and n.lexicon is Css.comment):
            continue
        yield n


def escape(char):
    """Escape the specified character for CSS."""
    return "".join(r"\{:x} ".format(ord(c)) for c in char)


def unescape(text):
    """Return the unescaped character, text is the contents of an Escape token."""
    value = text[1:]
    if value == '\n':
        return ''
    try:
        codepoint = int(value, 16)
    except ValueError:
        return value
    return chr(codepoint)


def get_ident_token(context):
    """Return the ident-token represented by the context.

    The context can be a selector, property, attribute, id_selector or
    class_selector, containing Name and/or Escape tokens.

    """
    def gen():
        for t in context:
            yield unescape(t.text) if t.action is Escape else t.text
    return ''.join(gen())


def get_string(context):
    """Get the string contexts represented by context (dqstring or sqstring)."""
    def gen():
        for t in context[:-1]:  # closing quote is not needed
            yield unescape(t.text) if t.action is String.Escape else t.text
    return ''.join(gen())


def get_url(context):
    """Get the url from the context, which is an url_function context."""
    def gen():
        for t in context[:-1]:
            if t.is_token:
                if t.action is Escape:
                    yield unescape(t.text)
                elif t.action is Literal.Url:
                    yield t.text
                elif t.action is String:
                    yield get_string(t.right_sibling())
    return ''.join(gen())


def calculate_specificity(selectors):
    """Calculate the specificity of the list of selectors.

    Returns a three-tuple (ids, clss, elts), where ids is the number of ID
    selectors, clss the number of class, attribute or pseudo-class selectors,
    and elts the number of element or pseudo-elements.

    Currently, does not handle functions like :not(), :is(), although that
    would not be difficult to implement.

    """
    # selector list?
    try:
        i = selectors.index(",")
    except ValueError:
        pass
    else:
        return max(calculate_specificity(selectors[:i]), calculate_specificity(selectors[i+1:]))
    q = Query.from_nodes(selectors).all
    ids = q(Css.id_selector).count()
    clss = q(Css.attribute_selector, Css.class_selector, Css.pseudo_class).count()
    elts = q(Css.element_selector, Css.pseudo_element).count()
    return (ids, clss, elts)


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


