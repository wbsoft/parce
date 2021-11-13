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
This module provides the Theme class, which provides text formatting
properties based on the action (standard action) of a Token.

These properties can be used to colorize text according to a language
definition.

By default, the properties are read from a normal CSS (Cascading StyleSheets)
file and presented to the user of the Theme module through TextFormat objects,
although other storage backends could be devised.

A Theme provides a ``textformat()`` for standard actions, and a
``baseformat()`` for general roles, such as ``"window"``, which denotes an
editor window (or an encompassing DIV or PRE block in HTML), ``"selection"``,
which is used for selected text, ``"current-line"``, which can highlight the
current line the cursor is in in an editor.

From the TextFormat returned by ``baseformat("selection")`` and
``"current-line"``, in most cases only the background color will be used.

For the roles ``"window"``, ``"selection"`` and ``"current-line"``, the
``baseformat()`` method also accepts a state argument, which can be
``"default"``, ``"focus"`` or ``"disabled"``. A theme always supports the
``"default"`` state, but can provide separate colors for the ``"focus"`` or
``"disabled"`` state, which can be used to change the basic formatting in an
editor window based on its state (in keyboard focus or disabled). If a theme
does not support the ``"disabled"`` and/or ``"focus"`` state, the default
scheme is used.

A Theme is loaded from a CSS file using::

    >>> from parce.theme import Theme
    >>> th = Theme('/path/to/my/custom.css')

Get a TextFormat for an action, use e.g.::

    >>> f = th.textformat(String)
    >>> f
    <TextFormat color=Color(r=192, g=0, b=0, a=255)>

Multiple CSS files can be combined into one theme, and CSS rules can also
be provided as plain text when instantiating a Theme.


Mapping actions to CSS classes
------------------------------

Standard actions are mapped to one or more CSS class names using
:func:`css_class`; it uses the action itself and the actions it descends from.
All CSS rules are combined, the one with the most matches comes first.

For example, ``Comment`` maps to the ``"comment"`` CSS class, and ``Number``
maps to ``"literal number"`` because Number is a descendant action of Literal.

Some actions might have the same name, e.g. ``Escape`` and ``String.Escape``.
Both match CSS rules with the ``.escape`` class selector, but a rule with
``.string.escape`` will have a higher precedence.

The order of the action names does not matter. E.g. an action ``Text.Comment``
will match exactly the same CSS rules as an action ``Comment.Text``. So you
should take some care when designing you action hierachy and not add too much
base action types.

"""


import collections
import itertools
import functools
import os

from . import css
from . import util


class AbstractTheme:
    """Defines the interface of a Theme as used by a formatter."""

    def baseformat(self, role="window", state="default"):
        """Should return a text format for a specific role and a state."""
        raise NotImplementedError

    def textformat(self, action):
        """Should return a text format for the specified action."""
        raise NotImplementedError


class Theme(AbstractTheme):
    """A Theme maps a StandardAction to a TextFormat with CSS properties.

    Zero or more ``filenames`` can be given, which are loaded after another. If
    the ``stylesheet`` text is given, it is added to the stylesheets loaded
    from the filename(s). (If the ``basename`` is given, it is used to resolve
    ``@import`` rules in the ``stylesheet`` text.)

    """

    def __init__(self, *filenames, stylesheet="", basename=""):
        """Instantiate the Theme from CSS file(s) and/or text."""
        self._filenames = filenames
        self._css_text = stylesheet
        self._css_base = basename
        self.TextFormat = TextFormat

    def __repr__(self):
        fnames = ', '.join(map(os.path.basename, self.filenames()))
        return '<{} [{}]>'.format(self.__class__.__name__, fnames)

    @util.cached_property
    def _stylesheet(self):
        """Load and cache the StyleSheet."""
        sheets = [css.StyleSheet.from_file(f) for f in self._filenames]
        if self._css_text or not self._filenames:
            sheets.append(css.StyleSheet.from_text(self._css_text, self._css_base))
        return sum(sheets[1:], sheets[0])

    @util.cached_property
    def style(self):
        """The stylesheet style rules (see :py:class:`css.Style <parce.css.Style>`)."""
        return self._stylesheet.style

    def filenames(self):
        """Return the list of filenames of the used stylesheet when instantiated"""
        return self._stylesheet.filenames()

    @util.cached_method
    def baseformat(self, role="window", state="default"):
        """Return a TextFormat for a specific role and a state.

        The ``role`` may be any string that maps to a CSS class in the theme
        CSS file that is available there together with the ``parce`` class.

        The following roles are recognized and used by parce, but you may
        also define your own roles in your (applications') theme CSS files:

        ``"window"``
            The TextFormat for the editor window or the encompassing DIV when
            formatting HTML. Corresponds to the "parce" CSS class alone in the
            theme file. You can set color, background and, if desired, font
            preferences.
        ``"selection"``
            The TextFormat to use for selected text. Uses the ``::selection``
            pseudo element.
        ``"current-line"``
            The TextFormat for the current line. If you use it, set only the
            *background* color in your theme file.

        The state argument may be "default", "focus", or "disabled", and
        reflects the state of the user interface the style variant is used for.
        If the state is "focus" or "disabled", it is added as a pseudo class.

        """
        if role == "window":
            e = css.Element(class_="parce")
        elif role == "selection":
            e = css.Element(class_="parce", pseudo_elements=["selection"])
        else:
            e = css.Element(class_="parce {}".format(role))
        if state in ("focus", "disabled"):
            e.pseudo_classes = [state]
        return self.TextFormat(self.style.select_element(e).properties())

    @util.cached_method
    def textformat(self, action):
        """Return the TextFormat for the specified action."""
        class_ = css_class(action)
        e = css.Element(class_=class_, parent=css.Element(class_="parce"))
        return self.TextFormat(self.style.select_element(e).properties())


class TextFormat:
    """Simple textformat that reads CSS properties and supports a subset of those.

    This factory is used by default by Theme, but you can implement your own.
    Such a factory only needs to implement an ``__init__`` method that reads
    the dictionary of property Value lists returned by Style.properties().

    A TextFormat has a False boolean value if no single property is set.

    You can add and subtract TextFormats::

        >>> import parce
        >>> t = parce.theme_by_name()
        >>> f = t.baseformat()
        >>> f
        <TextFormat background_color=Color(r=255, g=255, b=240, a=1.0), color=
        Color(r=0, g=0, b=0, a=1.0), font_family=['monospace'], font_size=12,
        font_size_unit='pt'>
        >>> f2 = t.textformat(parce.Comment)
        >>> f2
        <TextFormat color=Color(r=105, g=105, b=105, a=1.0), font_family=['serif'],
        font_style='italic'>
        >>> f + f2
        <TextFormat background_color=Color(r=255, g=255, b=240, a=1.0), color=
        Color(r=105, g=105, b=105, a=1.0), font_family=['serif'], font_size=12,
        font_size_unit='pt', font_style='italic'>
        >>> f - f2
        <TextFormat background_color=Color(r=255, g=255, b=240, a=1.0), color=
        Color(r=0, g=0, b=0, a=1.0), font_family=['monospace'], font_size=12,
        font_size_unit='pt'>
        >>>

    Adding a TextFormat returns a new format with our properties set and then
    the properties of the other. This is useful when it is not possible to
    overlay properties with underlying window properties.

    Subtracting a TextFormat returns a new format with the properties removed
    that are the same in the other format. This is useful when properties of
    a certain action happen to be the same as the underlying window properties;
    it is not needed to set these again in such cases.

    """
    color = None                    #: the foreground color as Color(r, g, b, a) tuple
    background_color = None         #: the background color (id)
    caret_color = None              #: the color for the text cursor
    text_decoration_color = None    #: the color for text decoration
    text_decoration_line = ()       #: underline, overline and/or line-through
    text_decoration_style = None    #: solid, double, dotted, dashed or wavy
    font_family = ()                #: family or generic name
    font_kerning = None             #: font kerning
    font_size = None                #: font size
    font_size_unit = None           #: font size unit if given
    font_stretch = None             #: font stretch value (keyword or float, 1.0 is normal)
    font_style = None               #: normal, italic or oblique
    font_style_angle = None         #: oblique slant if given
    font_style_angle_unit = None    #: oblique slant unit if given
    font_variant_caps = None        #: all kind of small caps
    font_variant_position = None    #: normal, sub or super
    font_weight = None              #: 100 - 900 or keyword like ``bold``

    _dispatch = util.Dispatcher()

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__,
            ", ".join("{}={}".format(key, repr(value))
                                for key, value in sorted(self.__dict__.items())))

    def __init__(self, properties):
        for prop, values in properties.items():
            self._dispatch(prop, values)

    def __bool__(self):
        """Return True if at least one property is set."""
        return bool(self.__dict__)

    def __sub__(self, other):
        """Return a new TextFormat with the properties removed that are the same in ``other``."""
        new = type(self)({})
        for props in (
            ('color',),
            ('background_color',),
            ('caret_color',),
            ('text_decoration_color', 'text_decoration_line', 'text_decoration_style'),
            ('font_family',),
            ('font_kerning',),
            ('font_size', 'font_size_unit'),
            ('font_stretch',),
            ('font_style', 'font_style_angle', 'font_style_angle_unit'),
            ('font_variant_caps',),
            ('font_variant_position',),
            ('font_weight',),
        ):
            if any(prop in self.__dict__ for prop in props) and \
                    any(self.__dict__.get(prop) != other.__dict__.get(prop) for prop in props):
                for prop in props:
                    try:
                        new.__dict__[prop] = self.__dict__[prop]
                    except KeyError:
                        pass
        return new

    def __add__(self, other):
        """Return a new TextFormat adding the other's properties."""
        new = type(self)({})
        new.__dict__.update(self.__dict__)
        new.__dict__.update(other.__dict__)
        return new

    def __eq__(self, other):
        """Return True if other has the same properties."""
        return self.__dict__ == other.__dict__

    def __ne__(self, other):
        """Return True if other has different properties."""
        return self.__dict__ != other.__dict__

    def css_properties(self):
        """Return a dict usable to write out a CSS rule with our properties."""
        return dict(itertools.chain(
            self.write_color(),
            self.write_text_decoration(),
            self.write_font(),
        ))

    def write_color(self):
        """Yield color and background color as CSS properties, if set."""
        if self.color:
            yield "color", css.color2hex(self.color)
        if self.background_color:
            yield "background-color", css.color2hex(self.background_color)
        if self.caret_color:
            yield "caret-color", css.color2hex(self.caret_color)

    def write_text_decoration(self):
        """Yield a text-decoration property, if set."""
        props = []
        props.extend(self.text_decoration_line)
        if self.text_decoration_style:
            props.append(self.text_decoration_style)
        if self.text_decoration_color:
            props.append(css.color2hex(self.text_decoration_color))
        if props:
            yield "text-decoration", " ".join(props)

    def write_font(self):
        """Yield all font-xxxx properties, if set."""
        if self.font_family:
            yield "font-family", ", ".join(map(css.quote_if_needed, self.font_family))
        if self.font_size:
            yield "font-size", "{}{}".format(
                self.font_size, self.font_size_unit or "")
        if self.font_style == "oblique" and self.font_style_angle:
            slant = self.font_style_angle
            unit = self.font_style_angle_unit or ""
            yield "font-style", "oblique {}{}".format(slant, unit)
        elif self.font_style:
            yield "font-style", self.font_style
        if self.font_stretch:
            yield "font-stretch", format(self.font_stretch)
        if self.font_kerning:
            yield "font-kerning", self.font_kerning
        if self.font_variant_caps:
            yield "font-variant-caps", self.font_variant_caps
        if self.font_variant_position:
            yield "font-variant-position", self.font_variant_position
        if self.font_weight:
            yield "font-weight", format(self.font_weight)

    @_dispatch("color")
    def read_color(self, values):
        for v in values:
            if v.color:
                self.color = v.color
                return

    @_dispatch("background-color")
    def read_background_color(self, values):
        for v in values:
            if v.color:
                self.background_color = v.color
                return

    @_dispatch("background")
    def read_background(self, values):
        self.read_background_color(values)

    @_dispatch("caret-color")
    def read_caret_color(self, values):
        for v in values:
            if v.color:
                self.caret_color = v.color
                return

    @_dispatch("text-decoration-color")
    def read_text_decoration_color(self, values):
        for v in values:
            if v.color:
                self.text_decoration_color = v.color
                return

    @_dispatch("text-decoration-line")
    def read_text_decoration_line(self, values):
        decos = []
        for v in values:
            if v.text in ("underline", "overline", "line-through"):
                decos.append(v.text)
            elif v.text == "none":
                decos.clear()
        self.text_decoration_line = decos

    @_dispatch("text-decoration-style")
    def read_text_decoration_style(self, values):
        for v in values:
            if v.text in ("solid", "double", "dotted", "dashed", "wavy"):
                self.text_decoration_style = v.text
                return

    @_dispatch("text-decoration")
    def read_text_decoration(self, values):
        self.read_text_decoration_color(values)
        self.read_text_decoration_line(values)
        self.read_text_decoration_style(values)

    @_dispatch("font-family")
    def read_font_family(self, values):
        families = []
        for v in values:
            if v.text and (v.quoted or v.text in (
                "serif",
                "sans-serif",
                "monospace",
                "cursive",
                "fantasy",
                "system-ui",
                "math",
                "emoji",
                "fangsong",
            )):
                families.append(v.text)
        self.font_family = families

    @_dispatch("font-kerning")
    def read_font_kerning(self, values):
        for v in values:
            if v.text in ("auto", "normal", "none"):
                self.font_kerning = v.text
                return

    @_dispatch("font-size")
    def read_font_size(self, values):
        for v in values:
            if v.text in ("xx-small", "x-small", "small", "medium",
                          "large", "x-large", "xx-large", "xxx-large",
                          "larger", "smaller"):
                self.font_size = v.text
                return
            elif v.number is not None:
                self.font_size = v.number
                self.font_size_unit = v.unit
                return

    @_dispatch("font-stretch")
    def read_font_stretch(self, values):
        for v in values:
            if v.text in ("ultra-condensed", "extra-condensed", "condensed",
                          "semi-condensed", "semi-expanded", "expanded",
                          "extra-expanded", "ultra-expanded"):
                self.font_stretch = v.text
            elif v.number is not None and v.unit == "%":
                self.font_stretch = v.number

    @_dispatch("font-style")
    def read_font_style(self, values):
        v = values[0]
        for n in values[1:] + [None]:
            if v.text in ("normal", "italic"):
                self.font_style = v.text
                return
            elif v.text == "oblique":
                self.font_style = v.text
                if n and n.number is not None:
                    self.font_style_angle = n.number
                    self.font_style_angle_unit = n.unit
                    return
            v = n

    @_dispatch("font-variant-caps")
    def read_font_variant_caps(self, values):
        for v in values:
            if v.text in ("normal", "small-caps", "all-small-caps", "petite-caps",
                          "all-petite-caps", "unicase", "titling-caps"):
                self.font_variant_caps = v.text
                return

    @_dispatch("font-variant-position")
    def read_font_variant_position(self, values):
        for v in values:
            if v.text in ("normal", "sub", "super"):
                self.font_variant_position = v.text
                return

    @_dispatch("font-weight")
    def read_font_weight(self, values):
        for v in values:
            if v.text in ("normal", "bold", "lighter", "bolder"):
                self.font_weight = v.text
                return
            elif v.number is not None:
                self.font_weight = v.number
                return

    @_dispatch("font")
    def read_font(self, values):
        self.read_font_style(values)
        numvalues = []
        for v in values:
            if v.text in ("caption", "icon", "menu", "message-box",
                          "small-caption", "status-bar"):
                self.font_family = [v.text]
                return
            elif v.text in ("normal", "small-caps"):
                self.font_variant_caps = v.text
            elif v.text in ("ultra-condensed", "extra-condensed", "condensed",
                            "semi-condensed", "semi-expanded", "expanded",
                            "extra-expanded", "ultra-expanded"):
                self.font_stretch = v.text
            elif v.text in ("bold", "lighter", "bolder"):
                self.font_weight = v.text
            elif v.number is not None:
                numvalues.append((v.number, v.unit))
        self.read_font_family(values)
        # if more than one size was given, weight is the first
        if len(numvalues) == 1:
            self.font_size, self.font_size_unit = numvalues[0]
        elif len(numvalues) > 1:
            if self.font_weight is None:
                self.font_weight = numvalues[0][0]
            self.font_size, self.font_size_unit = numvalues[1]


def css_class(action):
    """Return a CSS class string for the specified standard action.

    The class names are simply the name of the action and all its ancestor
    actions. Class names are lowercase and space-separated. For example::

        >>> from parce.action import Number
        >>> Number
        Literal.Number
        >>> css_class(Number)
        'literal number'

    """
    return repr(action).lower().replace('.', ' ')


