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


"""A CSS parser.

| CSS3 Syntax:     https://www.w3.org/TR/css-syntax-3/
| Selector syntax: https://www.w3.org/TR/selectors-4/

We also use this parser inside parce, to be able to store default
highlighting formats in css files.

"""

__all__ = ('Css', 'CssTransform', 'Rule', 'Atrule', 'Color', 'Value')

import collections
import re

from parce import Language, lexicon, skip, default_action, default_target
from parce.action import (
    Bracket, Comment, Delimiter, Escape, Invalid, Keyword, Literal, Name,
    Number, Operator, String)
from parce.rule import TEXT, bygroup, ifmember, ifeq, anyof
from parce.transform import Transform


RE_CSS_ESCAPE = r"\\(?:[0-9A-Fa-f]{1,6} ?|.)"
RE_CSS_NUMBER = (
    r"[+-]?"               # sign
    r"(?:\d*\.)?\d+"       # mantisse
    r"(?:[Ee][+-]\d+)?")   # exponent
# match either 8, 6, 4 or 3 hex digits
RE_HEX_COLOR = r"#[0-9a-fA-F]{3}(?:[0-9a-fA-F]{5}|[0-9a-fA-F]{3}|[0-9a-fA-F]?)"


class Css(Language):
    @lexicon
    def root(cls):
        yield from cls.toplevel()

    @classmethod
    def toplevel(cls):
        yield r"@", Keyword, cls.atrule, cls.atrule_keyword
        yield r"/\*", Comment, cls.comment
        yield r"\s+", skip  # skip whitespace
        yield default_target, cls.prelude

    @lexicon
    def prelude(cls):
        yield r"\{", Bracket, -1, cls.rule
        yield r"(?=</)", None, -1   # back off if HTML </style> tag follows...
        yield from cls.selectors()

    @classmethod
    def selectors(cls):
        """Yield selectors, used in prelude and selector_list."""
        yield r"\s+", skip              # skip whitespace
        yield r"[>+~]|\|\|", Operator   # combinators
        yield r",", Delimiter           # comma
        yield r"/\*", Comment, cls.comment
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield default_target, cls.selector

    @lexicon
    def selector(cls):
        yield r"\*", Keyword    # "any" element
        yield r"\|", Keyword    # css selector namespace prefix separator
        yield r"#", Name.Identifier.Definition, cls.id_selector
        yield r"\.(?!\d)", Keyword, cls.class_selector
        yield r"::", Keyword, cls.pseudo_element
        yield r":", Keyword, cls.pseudo_class
        yield r"\[", Delimiter, cls.attribute_selector, cls.attribute
        yield from anyof(cls.element_selector)
        yield default_target, -1

    @lexicon
    def selector_list(cls):
        """The list of selectors in :is(bla, bla), etc."""
        yield r"\)", Delimiter, -2  # also leave the pseudo_class context
        yield from cls.selectors()

    @lexicon
    def rule(cls):
        """Declarations of a qualified rule between { and }."""
        yield r"\}", Bracket, -1
        yield from cls.inline()

    @lexicon
    def inline(cls):
        """CSS that would be in a rule block, but also in a HTML style attribute."""
        yield from anyof(cls.property, cls.declaration, cls.property)
        yield from cls.common()

    @lexicon
    def declaration(cls):
        """A property: value;  declaration."""
        yield r":", Delimiter
        yield r";", Delimiter, -1
        yield r"!important\b", Keyword, -1
        yield from cls.common()
        yield r"\s+", skip  # stay here on whitespace only
        yield default_target, -1

    @classmethod
    def common(cls):
        """Stuff that can be everywhere."""
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield r"\{", Bracket, cls.rule
        yield RE_CSS_NUMBER, Number, cls.unit
        yield RE_HEX_COLOR, Literal.Color
        yield r"(url)(\()", bygroup(Name, Delimiter), cls.url_function
        yield from anyof(cls.identifier)
        yield r"[:,;@%!]", Delimiter

    @lexicon
    def unit(cls):
        """Unit directly after a number, e.g. the ``px`` in 100px, also ``%``."""
        yield "%", Operator.Percent, -1
        yield from cls.identifier_common(Name.Unit)

    # ------------ selectors for identifiers in different roles --------------
    @classmethod
    def identifier_common(cls, action):
        """Yield an ident-token and give it the specified action."""
        yield RE_CSS_ESCAPE, Escape
        yield r"[\w-]+", action
        yield default_target, -1

    @lexicon(consume=True)
    def element_selector(cls):
        """A tag name used as selector."""
        yield from cls.identifier_common(Name.Tag)

    @lexicon(consume=True)
    def property(cls):
        """A CSS property."""
        from .css_words import CSS3_ALL_PROPERTIES
        action = ifmember(TEXT, CSS3_ALL_PROPERTIES, Name.Property.Definition, Name.Property)
        yield from cls.identifier_common(action)

    @lexicon
    def attribute(cls):
        """An attribute name."""
        yield from cls.identifier_common(Name.Attribute)

    @lexicon
    def id_selector(cls):
        """#id"""
        yield from cls.identifier_common(Name.Identifier.Definition)

    @lexicon
    def class_selector(cls):
        """.classname"""
        yield from cls.identifier_common(Name.Class)

    @lexicon
    def attribute_selector(cls):
        """Stuff between [ and ]."""
        yield r"\]", Delimiter, -1
        yield r"[~|^$*]?=", Operator
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield from anyof(cls.ident_token)
        yield r'\s+', skip
        yield default_action, Invalid

    @lexicon
    def pseudo_class(cls):
        """Things like :first-child etc."""
        yield r"\(", Delimiter, cls.selector_list
        yield from cls.identifier_common(Name.Class.Pseudo)

    @lexicon
    def pseudo_element(cls):
        """Things like ::first-letter etc."""
        yield from cls.identifier_common(Name.Tag.Pseudo)

    # --------------------- @-rule ------------------------
    @lexicon
    def atrule(cls):
        """Contents following '@'."""
        yield r"\{", Bracket, cls.atrule_block
        yield from cls.atrule_common()

    @lexicon
    def atrule_nested(cls):
        """An atrule that has nested toplevel contents (@media, etc.)"""
        yield r"\{", Bracket, cls.atrule_nested_block
        yield from cls.atrule_common()

    @lexicon
    def atrule_keyword(cls):
        """The first identifier word in an @-rule."""
        yield r"(media|supports|document)\b", Keyword, -1, cls.atrule_nested
        yield from cls.identifier_common(Keyword)

    @lexicon
    def atrule_block(cls):
        """a { } block from an @-rule."""
        yield r"\}", Bracket, -2  # immediately leave the atrule context
        yield from cls.inline()

    @lexicon
    def atrule_nested_block(cls):
        """a { } block from @media, @document or @supports."""
        yield r"\}", Bracket, -2  # immediately leave the atrule_nested context
        yield from cls.toplevel()

    @classmethod
    def atrule_common(cls):
        """Common stuff inside @-rules."""
        yield r";", Delimiter, -1
        yield r":", Keyword, cls.pseudo_class
        yield from cls.common()
        yield r'(?=</)', None, -1   # leave atrule when </style tag follows

    @lexicon(consume=True)
    def ident_token(cls):
        """An ident-token where quoted or unquoted text is allowed."""
        yield from cls.identifier_common(Name.Symbol)

    @lexicon(consume=True)
    def identifier(cls):
        """An ident-token that could be a color or a function()."""
        from .css_words import CSS3_NAMED_COLORS
        action = ifeq(TEXT, "transparent", Literal.Color,
            ifmember(TEXT, CSS3_NAMED_COLORS, Literal.Color, Name.Symbol))
        yield r"\(", Delimiter, cls.function
        yield from cls.identifier_common(action)

    @lexicon
    def function(cls):
        """Contents between identifier( ... )."""
        yield r"\)", Delimiter, -2  # go straight out of the identifier context
        yield r"\(", Delimiter, 1
        yield from cls.common()
        yield r"[*/+-]", Operator

    @lexicon
    def url_function(cls):
        """url(....)"""
        yield r"\)", Delimiter, -1
        yield r'"', String, cls.dqstring
        yield r"'", String, cls.sqstring
        yield r"/\*", Comment, cls.comment
        yield RE_CSS_ESCAPE, Escape
        yield default_action, Literal.Url

    @lexicon
    def dqstring(cls):
        """A double-quoted string."""
        yield r'"', String, -1
        yield from cls.string()

    @lexicon
    def sqstring(cls):
        """A single-quoted string."""
        yield r"'", String, -1
        yield from cls.string()

    @classmethod
    def string(cls):
        """Common rules for string."""
        yield default_action, String
        yield RE_CSS_ESCAPE, String.Escape
        yield r"\\\n", String.Escape
        yield r"\n", Invalid, -1

    @lexicon
    def comment(cls):
        """A comment."""
        yield r"\*/", Comment, -1
        yield from cls.comment_common()


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
        >>> transform_tree(root(Css.root, 'h1 { color: red; }'))
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
        if items and items[-1] == '{':
            items = items[:-1]
        prelude = []
        result = []
        for i in items:
            if i.is_token:
                if i == ',':
                    prelude.append(result)
                    result = []
                elif i.action is Operator:
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
                if i.action is Operator:
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
        if items and not items[-1].is_token and items[-1].name == "selector_list":
            selector_list = items[-1].obj
        return name, selector_list

    def pseudo_element(self, items):
        """Return the name of the pseudo element."""
        return self.get_ident_token(items)[0]

    def atrule(self, items):
        """Return a Atrule named tuple."""
        if items and not items[0].is_token and items[0].name == "atrule_keyword":
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
        if items and not items[-1].is_token and items[-1].name == "atrule_nested_block":
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
        if items and not items[-1].is_token and items[-1].name == "function":
            funcargs = items[-1].obj
            return self.get_css_function_call(text, funcargs)
        from .css_words import CSS3_NAMED_COLORS
        if action is Literal.Color or text in CSS3_NAMED_COLORS:
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
                    if i.action is Escape:
                        yield self.get_escape(i.text)
                    elif i.action is Literal.Url:
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
                if i.action is Number:
                    value = Value(text=i.text, number=self.get_number(i.text))
                    i = next(items, None)
                    if i and not i.is_token and i.name == "unit":
                        value.unit = i.obj
                        i = next(items, None)
                    yield value
                    continue
                elif i.action is Literal.Color:
                    # a hexadecimal color (a named color is an identifier)
                    color = self.get_hex_color(i.text[1:])
                    yield Value(color=color, text=i.text)
                elif i.action is Keyword or i.action in Delimiter:
                    yield i.text
                elif i.action is Name and i.text == "url":
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
            elif i.action is String.Escape:
                yield self.get_escape(i.text)

    def get_ident_token(self, items):
        """Return a two-tuple(name, action).

        Combines tokens in an identifier context, (see :meth:`Css.identifier_common`).

        """
        actions = [None]
        def gen():
            for i in items.tokens():
                if i.action is Escape:
                    yield self.get_escape(i.text)
                elif i.action not in Delimiter:
                    if i.action in Name:
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
            from .css_words import CSS3_NAMED_COLORS
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


#: An at-rule. For nested atrules the nested stylesheet is in a list ``block``,
#: for other at-rules that end with a rule with properties, the properties
#: dict is in ``block``; when there is no block, ``block`` is None.
Atrule = collections.namedtuple("Atrule", "keyword contents block")

#: A normal rule
Rule = collections.namedtuple("Rule", "prelude properties")

#: A named tuple holding the (r, g, b, a) value of a color.
Color = collections.namedtuple("Color", "r g b a")


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


