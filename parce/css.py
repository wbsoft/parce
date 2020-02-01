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
This modules provides StyleSheet, Style and a bunch of utility functions
that help reading from a tree structure parsed by the parce.lang.css module.

StyleSheet represents a list of rules and conditions (nested @-rules) from a
CSS file or string source.

Style represents a resulting list of rules, sorted on specificity, so that
by selecting rules the properties that apply in a certain situation can be
determined and read.

This module will be used by the theme module to provide syntax highlighting
themes based on CSS files.

Workflow:

    1. Instantiate a StyleSheet from a file or other source. If needed,
       combine multiple StyleSheets using the + operator.

    2. Filter conditions out using ``filter_conditions()``, like media,
       supports or document.

    3. Get a Style object through the ``style`` property of the StyleSheet.

    4. Use a ``select`` method (currently only ``select_class``, but more
       can be implemented) to select rules based on their selectors.

    5. Use ``properties()`` to combine the properties of the selected
       rules to get a dictionary of the CSS properties that apply.

Example::

    >>> from parce.css import *
    >>> style = StyleSheet.from_file("parce/themes/default.css").style
    >>> style.select_class("comment").combine_properties()
    {'font-style': [<Context Css.identifier at 1037-1043 (1 children)>],
    'color': [<Token '#666' at 1056:1060 (Literal.Color)>]}

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


def style_query(func):
    """Make a method result (generator) into a new Style object."""
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        return type(self)(list(func(self, *args, **kwargs)))
    return wrapper


class StyleSheet:
    """Represents a list of style rules and conditions.

    Normall CSS rules are translated into a Rule tuple, and nested rules
    such as @media, @document and @supports are translated into Condition
    tuples.

    A Rule consists of ``selectors`` and ``properties``. The ``selectors``
    are the tokens in a rule before the {. The ``properties`` is a dict
    mapping css property names to the list of tokens representing their
    value.

    A Condition consists of ``condition`` and ``style``; the ``condition``
    is a list of tokens representing all text between the @ and the opening {.
    The ``style`` is another StyleSheet object representing the nested
    style sheet.

    You can combine stylesheets from different files or sources using the +
    operator.

    The ``style`` property returns the Style object representing all combined
    rules, and allowing further queries.

    """
    def __init__(self, rules=None):
        """Initialize a StyleSheet, empty of with the supplied rules/conditions."""
        self.rules = rules or []

    @classmethod
    def from_file(cls, filename, path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a local filename.

        The ``path`` argument is currently unused. If ``allow_import`` is
        False, the @import atrule is ignored.

        """
        encoding, data = util.get_bom_encoding(open(filename, 'rb').read())
        if not encoding:
            m = re.match(rb'^@charset\s*"(.*?)"', data)
            encoding = m.group(1).decode('latin1') if m else "utf-8"
        try:
            text = data.decode(encoding)
        except (LookupError, UnicodeError):
            text = data.decode('utf-8', 'replace')
        return cls.from_text(text, filename, path, allow_import)

    @classmethod
    def from_text(cls, text, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a string.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        tree = root(Css.root, text)
        return cls.from_tree(tree, filename, path, allow_import)

    @classmethod
    def from_tree(cls, tree, filename='', path=None, allow_import=True):
        """Return a new StyleSheet adding Rules and Conditions from a parsed tree.

        The ``filename`` argument is used to handle @import rules
        correctly. The ``path`` argument is currently unused. If
        ``allow_import`` is False, the @import atrule is ignored.

        """
        rules = []
        for node in tree.query.children(Css.atrule, Css.prelude):
            if node.lexicon is Css.atrule:
                # handle @-rules
                if node and node[0].is_context and node[0].lexicon is Css.atrule_keyword:
                    keyword = get_ident_token(node[0])
                    if keyword == "import":
                        if allow_import:
                            for s in node.query.children(Css.dqstring, Css.sqstring):
                                fname = get_string(s)
                                fname = os.path.join(os.path.dirname(filename), fname)
                                rules.extend(cls.from_file(fname, path, True).rules)
                                break
                    elif node[-1].lexicon is Css.atrule_nested:
                        s = cls.from_tree(node[-1][-1], filename, path, allow_import)
                        rules.append(Condition(keyword, node, s))
                    else:
                        # other @-rule
                        rules.append(Atrule(keyword, node))
            elif len(node) > 1:   # Css.prelude
                # get the selectors (without ending { )
                selectors = list(remove_comments(node[:-1]))
                if selectors:
                    for rule in node.query.right:
                        # get the property declarations:
                        properties = {}
                        for declaration in rule.query.children(Css.declaration):
                            propname = get_ident_token(declaration[0])
                            value = declaration[2:] if declaration[1] == ":" else declaration[1:]
                            properties[propname] = value
                        rules.append(Rule(selectors, properties))
                        break
        return cls(rules)

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
        keyword.

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
    def select_class(self, *classes):
        """Select the rules that match at least one of the class names.

        Just looks at the last class name in a selector, does not use combinators.
        (Enough for internal styling :-).

        """
        for rule in self.rules:
            c = Query.from_nodes(rule.selectors).all(Css.class_selector).pick_last()
            if c and get_ident_token(c) in classes:
                yield rule

    def properties(self):
        """Return the combined properties of the current set of rules. (Endpoint.)

        Returns a dictionary with the properties. Comments, closing delimiters and
        "!important" flags are removed from the property values.

        """
        result = {}
        for rule in self.rules:
            for key, value in rule.properties.items():
                if key not in result or (
                     "!important" in value and "!important" not in result[key]):
                    result[key] = list(remove_comments(value))
        for value in result.values():
            while value and value[-1] in (";", "!important"):
                del value[-1]
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


class CssElement:
    """Mimic an element CSS selector rules are matched with.

    Use "class_" when specifying the class with a keyword argument.
    You can also manipulate the attributes after instantiating.

    """
    def __init__(self, name="", parent=None, pseudo_classes=None, pseudo_elements=None, **attrs):
        self.name = name
        self.parent = parent
        self.siblings = []
        self.pseudo_classes = pseudo_classes
        self.pseudo_elements = pseudo_elements
        self.attrs = attrs
        self.id = attrs.get("id")
        if "class" not in attrs and "class_" in attrs:
            attrs["class"] = attrs["class_"]
        self.class_ = attrs.get("class", "").split()

    def match(self, selectors):
        """Match with a compound selector expression (``selectors`` part of Rule)."""
        # selector list?
        try:
            i = selectors.index(",")
        except ValueError:
            pass
        else:
            return self.match(selectors[:i]) or self.match(selectors[i+1:])
        if not selectors:
            return True
        selectors = iter(reversed(selectors))
        sel = next(selectors)
        if not sel.is_context or not self.match_selector(sel):
            return False
        parent = self.parent
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
                if not parent or not parent.match_selector(sel):
                    return False
                parent = parent.parent
                element = parent
            elif operator == " ":
                pass # an ancestor should match
            elif operator == "+":
                pass # immediate sibling should match
            else: # operator == "~":
                pass # a sibling should match
            operator = next(selectors, None)
        return True

    def match_selector(self, selector):
        """Match with a single CSS selector (Css.selector Context).

        Returns True if the element matches with the selector.

        """
        q = selector.query.children
        # class?
        for c in q(Css.class_selector):
            if get_ident_token(c) not in self.class_:
                return False
        # element name?
        c = q(Css.element_selector).pick()
        if c and get_ident_token(c) != self.name:
            return False
        # id?
        c = q(Css.id_selector).pick()
        if c and get_ident_token(c) != self.id:
            return False
        # attrs?
        for c in q(Css.attribute_selector):
            if c and c[0].lexicon is Css.attribute:
                attrname = get_ident_token(c[0])
                if attrname not in self.attrs:
                    return False
                value = self.attrs[attrname]
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
        for c in q(Css.pseudo_class):
            if get_ident_token(c) not in self.pseudo_classes:
                return False
        # pseudo_element?
        for c in q(Css.pseudo_element):
            if get_ident_token(c) not in self.pseudo_elements:
                return False
        return True


def css_classes(action):
    """Return a tuple of lower-case CSS class names for the specified standard action."""
    return tuple(a._name.lower() for a in action)


def remove_comments(nodes):
    """Yield the nodes with comments removed."""
    for n in nodes:
        if (n.is_token and n.action is Comment) or (
            n.is_context and n.lexicon is Css.comment):
            continue
        yield n


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
        for n in context[:-1]:
            if n.is_token:
                if t.action is Escape:
                    yield unescape(t.text)
                elif action is Literal.Url:
                    yield t.text
                elif action is String:
                    yield get_string(n.right_sibling())
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


