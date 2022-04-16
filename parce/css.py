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
:class:`~parce.css.CssTransform` transform class.)

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

from . import action as a
from . import util
from .lang.css import Css
from .transform import Transform, transform_text


#: An at-rule. For nested atrules the nested stylesheet is in a list ``block``,
#: for other at-rules that end with a rule with properties, the properties
#: dict is in ``block``; when there is no block, ``block`` is None.
Atrule = collections.namedtuple("Atrule", "keyword contents block")
Atrule.keyword.__doc__  = "The identifier directly after the ``@``."
Atrule.contents.__doc__ = "The tokens between de keyword and the block."
Atrule.block.__doc__    = "The block between ``{`` ... ``}``."

#: A normal rule
Rule = collections.namedtuple("Rule", "prelude properties")
Rule.prelude.__doc__    = "The list of selector lists, see :meth:`Css.prelude`."
Rule.properties.__doc__ = "The dictionary of Css properties."

#: A conditional at-rule
Condition = collections.namedtuple("Condition", "keyword node style")
Condition.keyword.__doc__ = "The keyword after the ``@``."
Condition.node.__doc__ = ("The contents after the keyword and before the block,"
    " or the query after the filename of an ``@import`` rule.")
Condition.style.__doc__ = "The :class:`Style` representing the rules in the block."

#: A named tuple holding the (r, g, b, a) value of a color.
Color = collections.namedtuple("Color", "r g b a")
Color.r.__doc__ = "The red value, integer in the range 0..255."
Color.g.__doc__ = "The green value, integer in the range 0..255."
Color.b.__doc__ = "The blue value, integer in the range 0..255."
Color.a.__doc__ = "The opacity, float in the range 0..1."


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
        return transform_text(Css.root, text, CssTransform())

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
        """Create a new StyleSheet by appending the other's rules."""
        new = type(self)(self.rules + other.rules)
        new._imported_filenames = list(set(self.filenames() + other.filenames()))
        return new

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

    If you wrap other objects, be sure to reimplement ``__eq__`` and
    ``__ne__``, to compare those objects and not the wrappers, which may be
    recreated each time.

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


class CssTransform(Transform):
    r"""Transform a CSS stylesheet into a simpler data structure.

    The data structure created by this Transform only contains plain Python
    strings, lists, (named) tuples, dictionaries and :class:`Value` objects.
    :class:`Value` represents any item from a property value list. Most
    notably, a CSS color (hexadecimal, named or via the CSS
    ``rgb()``/``rgba()`` functions) is converted to a named :class:`Color`
    four-tuple.

    A tree created by the Css.root lexicon becomes a list of tuples
    that are either a Rule or an Atrule named tuple.

    An :class:`Atrule` named tuple corresponds to an @-rule and consists of
    three items, the ``keyword`` which contains the name, the ``contents``,
    which contains all items after the name, and the ``block`` which contains
    the part between { and }.

    There are three at-rule types:

    1. Nested at-rule: the ``keyword`` is either ``"media"``, ``"supports"`` or
       ``"document"``, the ``contents`` contains the query strings and Value
       instances; the ``block`` contains the list of nested Rule/Atrule tuples.

    2. At-rules with a properties block, like ``@page:left { ... }``: the
       keyword can be anything, the block is a dictionary of properties like
       the ``properties`` dictionary of a normal Rule (see below). The
       ``contents`` contains the stuff between the block and the initial
       keyword.

    3. At-rules without a block; like ``@import url("filename.css");``, the
       ``block`` is None for these at-rules.

    A :class:`Rule` named tuple corresponds to a normal CSS rule and consists
    of two items, the ``prelude``, which contains the selectors, and the
    ``properties`` dictionary.

    The *prelude* is a list of selector groups. Each selector group is also
    a list, containing at least one selector dictionary and optionally
    operator strings and more selector dictionaries. See the :meth:`prelude`
    method.

    The *properties* is a dictionary mapping property names to lists of
    :class:`Value` instances. A Value can express any CSS property value, like
    a quoted string, unquoted name, number with or without unit, url, etc. It
    also recognizes named, `rgb/rgba` and hexadecimal colors, which can be
    found as a :class:`Color` tuple in the :attr:`Value.color` attribute. It
    does not yet parse ``calc()`` function calls.

    For example::

        >>> from parce import root
        >>> from parce.transform import transform_tree
        >>> from parce.lang.css import Css
        >>> from parce.css import CssTransform
        >>> transform_tree(root(Css.root, 'h1 { color: red; }'), CssTransform())
        [Rule(prelude=[[{'element_selector': ['h1']}]], properties={'color':
        [<Value text='red', color=Color(r=255, g=0, b=0, a=1.0)>]})]

    """
    def root(self, items):
        """Return a list of Rule or Atrule tuples."""
        result = []
        prelude = None
        for name, obj in items.items():
            if name == "prelude":
                prelude = obj
            elif name == "rule":
                result.append(Rule(prelude, obj))
                prelude = None
            elif name == "atrule":
                result.append(obj)
        return result

    def prelude(self, items):
        r"""Return a Css prelude.

        A prelude is a list of selector lists. A Css prelude that contains a
        comma has more than one selector lists.

        A selector list is a list of selector dictionaries with possible
        combinator operators in between. The operators can be: ``" "`` (space),
        ``">"``, ``"~"``, ``"+"``, or ``"||"``.

        Every selector is a dictionary, and inbetween are operator strings. A
        comma in the selector causes the prelude to contain more than one list.
        Every selector list consists of selector dicts with an operator or
        whitespace in between.

        """
        # skip the { that starts the rule which is normally there
        if items.peek(-1, a.Bracket):
            items = items[:-1]
        prelude = []
        result = []
        for i in items:
            if i.is_token:
                if i == ',':
                    prelude.append(result)
                    result = []
                elif i.action is a.Operator:
                    if result and isinstance(result[-1], dict):
                        # dont append operator at start, or two operators
                        result.append(i.text)
            elif i.name == "selector":
                if result and isinstance(result[-1], dict):
                    # append descendant combinator if no operator was there
                    result.append(" ")
                result.append(i.obj)
        if result:
            prelude.append(result)
        # cleanup prelude: remove operators that are at the end of a selector
        # list
        for selectors in prelude:
            if selectors and not isinstance(selectors[-1], dict):
                del selectors[-1]
        # remove empty selector lists
        prelude = [selectors for selectors in prelude if selectors]
        return prelude

    def selector(self, items):
        """Return a dictionary object.

        The possible keys are: "element_selector", "id_selector",
        "class_selector", "pseudo_class", "pseudo_element",
        "attribute_selector".

        If present, the value is a list of objects created by that context.
        Most objects are simple strings, but for pseudo_class it is a (name,
        selector_list) tuple, and for attribute_selector it is a four-tuple of
        the contents between the ``[`` and ``]``.

        "*" is ignored, '|' is not yet handled.

        """
        d = collections.defaultdict(list)
        for name, obj in items.items():
            d[name].append(obj)
        return dict(d)

    def selector_list(self, items):
        """Stuff inside :not(), :is(), etc."""
        # skip the closing ) which is normally there
        if items and items[-1] == ')':
            items = items[:-1]
        return self.prelude(items)

    def rule(self, items):
        """A Css rule, between { ... }."""
        return self.inline(items)

    def inline(self, items):
        """Return a dictionary of the property values."""
        d = {}
        for i in items.items("declaration"):
            if i.obj:
                prop, values = i.obj
                d[prop] = values
        return d

    def declaration(self, items):
        """Return a two-tuple(property, value).

        The value is a list of Value instances from :meth:`common`.

        """
        items = iter(items)
        for i in items:
            if not i.is_token and i.name == "property":
                propname = i.obj
                values = list(self.common(i
                        for i in items if i not in (':', ';')))
                return propname, values

    def unit(self, items):
        """Return the name of the unit in itens."""
        if items and items[0] == "%":
            return '%'
        return self.get_ident_token(items)[0]

    def element_selector(self, items):
        """Return the name of the element_selector."""
        return self.get_ident_token(items)[0]

    def property(self, items):
        """Return the name of the property."""
        return self.get_ident_token(items)[0]

    def attribute(self, items):
        """Return the name of the attribute."""
        return self.get_ident_token(items)[0]

    def id_selector(self, items):
        """Return the name of the id_selector."""
        return self.get_ident_token(items)[0]

    def class_selector(self, items):
        """Return the name of the class_selector."""
        return self.get_ident_token(items)[0]

    def attribute_selector(self, items):
        """Return a four-tuple representing the contents between [ and ].

        The tuple: (attribute, operator, value, flag).

        """
        attr = op = val = flag = None
        for i in items:
            if i.is_token:
                if i.action is a.Operator:
                    op = i.text
            elif i.name in ('sqstring', 'dqstring'):
                val = i.obj
            elif i.name == 'attribute':
                attr = i.obj
            elif i.name == 'ident_token':
                if val:
                    flag = i.obj
                else:
                    val = i.obj
        return  attr, op, val, flag

    def pseudo_class(self, items):
        """Return a tuple(name, selector_list).

        The ``name`` is the name of the pseudo class, the selector_list
        is a list of selectors like the ``prelude`` of a rule. For pseudo
        classes without arguments, the selector_list is None.

        """
        name = self.get_ident_token(items)[0]
        selector_list = None
        if items.peek(-1, "selector_list"):
            selector_list = items[-1].obj
        return name, selector_list

    def pseudo_element(self, items):
        """Return the name of the pseudo element."""
        return self.get_ident_token(items)[0]

    def atrule(self, items):
        """Return a Atrule named tuple."""
        if items.peek(0, "atrule_keyword"):
            keyword = items.pop(0).obj
        else:
            keyword = None
        block = None
        for n, i in enumerate(items):
            if not i.is_token:
                if i.name == "atrule_nested":
                    contents, block = i.obj
                    break
                elif i.name == "atrule_block":
                    block = i.obj   # the properties dict
                    contents = tuple(self.common(items[:n-1]))  # skip {
                    break
            elif i == ';':
                contents = tuple(self.common(items[:n]))
                break
        else:
            contents = tuple(self.common(items))
        return Atrule(keyword, contents, block)

    def atrule_nested(self, items):
        """Return a two-tuple: the stuff before the nested block and the nested block."""
        nested = None
        if items.peek(-1, "atrule_nested_block"):
            nested = items.pop().obj
            items.pop() # skip {
        return tuple(self.common(items)), nested

    def atrule_keyword(self, items):
        """Return the name of the atrule keyword."""
        return self.get_ident_token(items)[0]

    def atrule_block(self, items):
        """Return the properties dict in an atrule block."""
        return self.inline(items)

    def atrule_nested_block(self, items):
        """Return a list of Rule or Atrule tuples."""
        return self.root(items)

    def ident_token(self, items):
        """Return the ident_token."""
        return self.get_ident_token(items)[0]

    def identifier(self, items):
        """Return a Value.

        For a color name, returns a Value with a color, otherwise
        a Value with the text.

        If the identifier also has a function sub-context, a Value representing
        a function call is returned (this is done by the
        :func:`get_css_function_call` function, which is capable of
        interpreting ``url``, ``rgb`` and ``rgba`` function calls).

        """
        text, action = self.get_ident_token(items)
        if items.peek(-1, "function"):
            funcargs = items[-1].obj
            return self.get_css_function_call(text, funcargs)
        from .lang.css_words import CSS3_NAMED_COLORS
        if action is a.Literal.Color or text in CSS3_NAMED_COLORS:
            color = self.get_named_color(text)
            return Value(color=color, text=text)
        return Value(text=text)

    def function(self, items):
        """Return a list of Value instances and delimiting tokens."""
        # skip the closing ) which is normally there
        if items and items[-1] == ')':
            items = items[:-1]
        return tuple(self.common(items))

    def url_function(self, items):
        """Return a Value with the url."""
        def gen():
            for i in items:
                if i.is_token:
                    if i.action is a.Escape:
                        yield self.get_escape(i.text)
                    elif i.action is a.Literal.Url:
                        yield i.text
                elif i.name in ('dqstring', 'sqstring'):
                    yield i.obj
        return Value(url=''.join(gen()))

    def dqstring(self, items):
        """Return the contents of a double-quoted string."""
        if items and items[-1] == '"':
            items = items[:-1]
        return ''.join(self.get_string(items))

    def sqstring(self, items):
        """Return the contents of a single-quoted string."""
        if items and items[-1] == "'":
            items = items[:-1]
        return ''.join(self.get_string(items))

    ### we don't implement comment, so all comments are ignored
    comment = None

    ### helper methods
    def common(self, items):
        """Yield any values, see Css.common().

        Every item is either a Value instance or a delimiting token.
        If an ``identifier`` context is followed by a ``function`` context,
        they are combined into a Value with funcname and arguments by the
        :meth:`get_css_function_call` method.

        """
        items = iter(items)
        i = next(items, None)
        while i is not None:
            if i.is_token:
                if i.action is a.Number:
                    value = Value(text=i.text, number=self.get_number(i.text))
                    i = next(items, None)
                    if i and not i.is_token and i.name == "unit":
                        value.unit = i.obj
                        i = next(items, None)
                    yield value
                    continue
                elif i.action is a.Literal.Color:
                    # a hexadecimal color (a named color is an identifier)
                    color = self.get_hex_color(i.text[1:])
                    yield Value(color=color, text=i.text)
                elif i.action is a.Keyword or i.action in a.Delimiter:
                    yield i.text
                elif i.action is a.Name and i.text == "url":
                    next(items, None)   # skip (
            elif i.name in ('sqstring', 'dqstring'):
                yield Value(text=i.obj, quoted=True)
            elif i.name in (
                    'url_function',
                    'identifier',
                    'pseudo_class',
                    'attribute',
                    'selector_list',
                 ):
                yield i.obj
            i = next(items, None)

    def get_css_function_call(self, name, arguments):
        """Return a Value for a CSS function call. Handles rgb/rgba."""
        if name in ('rgb', 'rgba'):
            return Value(color=self.get_rgba_color(arguments))
        elif name == "url":
            # normally handled by url_function
            text = ''.join(v.text for v in arguments
                    if isinstance(v, Value) and v.text is not None)
            return Value(url=text)
        return Value(funcname=name, arguments=arguments)

    def get_number(self, text):
        """Get the value of a Number."""
        num = float(text)
        if num.is_integer():
            num = int(num)
        return num

    def get_escape(self, text):
        """Get the value of escaped text."""
        value = text[1:]
        if value == '\n':
            return ''
        try:
            codepoint = int(value, 16)
        except ValueError:
            return value
        return chr(codepoint)

    def get_string(self, items):
        """Yield the parts of a string.

        Called by :meth:`sqstring` and :meth:`dqstring`.

        """
        for i in items.tokens():
            if i.action is String:
                yield i.text
            elif i.action is a.String.Escape:
                yield self.get_escape(i.text)

    def get_ident_token(self, items):
        """Return a two-tuple(name, action).

        Combines tokens in an identifier context, (see :meth:`Css.identifier_common`).

        """
        actions = [None]
        def gen():
            for i in items.tokens():
                if i.action is a.Escape:
                    yield self.get_escape(i.text)
                elif i.action not in a.Delimiter:
                    if i.action in a.Name:
                        actions.append(i.action)
                    yield i.text
        name = ''.join(gen())
        return name, actions[-1]

    def get_hex_color(self, text):
        """Return a named four-tuple Color(r, g, b, a) describing color and alpha.

        The ``text`` is a hexadecimal color without the hash, like "FA0042".
        The r, g, b values are in the range 0..255, a in 0..1; 1.0 is fully
        opaque.

        """
        r, g, b, a = -1, -1, -1, 1.0
        l = len(text)
        c = int(text, 16)
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
        return Color(r, g, b, a)

    def get_named_color(self, text):
        """Return a named four-tuple Color(r, g, b, a) describing color and alpha.

        The ``text`` is a CSS3 color name.
        The r, g, b values are in the range 0..255, a in 0..1; 1.0 is fully
        opaque.

        """
        if text == "transparent":
            r, g, b, a = 0, 0, 0, 0
        else:
            r, g, b, a = -1, -1, -1, 1.0
            from .lang.css_words import CSS3_NAMED_COLORS
            try:
                r, g, b = CSS3_NAMED_COLORS[text]
            except KeyError:
                pass
        return Color(r, g, b, a)

    def get_rgba_color(self, func_args):
        """Convert the arguments to a rgba(1 2 3 4) call to a Color."""
        values = (v for v in func_args if isinstance(v, Value) and v.number)
        r = next(values, -1)
        if r != -1: r = self.get_number_value(r, 255)
        g = next(values, -1)
        if g != -1: g = self.get_number_value(g, 255)
        b = next(values, -1)
        if b != -1: b = self.get_number_value(b, 255)
        a = next(values, 1.0)
        if a != 1.0: a = self.get_number_value(a, 1.0)
        return Color(r, g, b, a)

    def get_number_value(self, value, maximum):
        """Return a numeric value from the Value object.

        If the value object has a percentage, apply it so 100% yields the
        maximum value. Otherwise, the number is constrained to be in the
        0..maximum range.

        """
        n = value.number
        if value.unit == "%":
            n = n * maximum // 100
        if n < 0: n = 0
        if n > maximum: n = maximum
        return n


class Value:
    """Any value that can occur in a CSS property declaration.

    The value of a CSS property is always a list of Value instances.

    For a *numerial* value, the ``number`` attribute contains the numeric value,
    and the ``text`` attribute the textual representation as present in the CSS
    file. A unit (or "``%``") that was specified, is in the ``unit`` attribute.

    For a *color* value, the color is in the ``color`` attribute as a
    :class:`Color` four-tuple. When a CSS3 named color was specified, the name
    of the color is in the ``text`` attribute, or when a hexadecimal color was
    specified, the hexadecimal notation is also in the ``text`` attribute.

    For a value that can either be a *quoted string* or an *ident_token*, the
    value is in the ``text`` attribute. If it originally was a quoted string,
    the ``quoted`` attribute is set to True.

    If the value represents a *URL* specified via the ``url()`` function, the
    URL is in the ``url`` attribute.

    If the value represents a *function call*, the name of the function is in
    the ``funcname`` attribute, and the argument list in the ``arguments``
    attribute. Except for the ``url()``, the ``rgb()`` and ``rgba()``
    functions, which are handled by the CssTransform class.

    """
    def __init__(self,
            text = None,
            number = None,
            unit = None,
            url = None,
            color = None,
            funcname = None,
            quoted = None,
            arguments = (),
            ):
        self.text = text
        self.number = number
        self.unit = unit
        self.url = url
        self.color = color
        self.funcname = funcname
        self.quoted = quoted
        self.arguments = list(arguments)

    def __repr__(self):
        def gen():
            for name, value in self.__dict__.items():
                if value not in (None, []):
                    yield '{}={}'.format(name, repr(value))
        return '<{} {}>'.format(self.__class__.__name__, ', '.join(gen()))


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

