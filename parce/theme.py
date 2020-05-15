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

A Theme provides a ``textformat()`` for standard actions, and for three
general situations: ``window()``, which denotes an editor window (or an
encompassing DIV or PRE block in HTML), ``selection()``, which is used for
selected text, and ``currentline()``, which can highlight the current line
the cursor is in in an editor.

From the TextFormat returned by ``selection()`` and ``currentline()``, in
most cases only the background color will be used.

The methods ``window()``, ``selection()`` and ``currentline()`` also accept a
state argument, which can be "default", "focus" or "disabled". A theme always
supports the default state, but can provide separate colors for the "focus"
or "disabled" state, which can be used to change the basic formatting in an
editor window based on its state (in keyboard focus or disabled). If a theme
does not support the "disabled" and/or "focus" state, the default scheme is
used.

In the ``themes/`` directory are bundled CSS themes that can be used.
Instantiate a bundled theme with::

    >>> from parce.theme import Theme
    >>> th = Theme.byname("default")

To use a custom CSS theme file, load it using::

    >>> th = Theme('/path/to/my/custom.css')

Get a TextFormat for an action, use e.g.::

    >>> f = th.textformat(String)
    >>> f
    <TextFormat color=Color(r=192, g=0, b=0, a=255)>


Mapping actions to CSS classes
------------------------------

Standard actions are mapped to a tuple of CSS class names: the action itself
and the actions it descends from. All CSS rules are combined, the one with the
most matches comes first.

For example, Comment maps to the "comment" CSS class, and Number maps
to ("literal", "number") because Number is a descendant action of Literal.

Some actions might have the same name, e.g. Escape and String.Escape.
Both match CSS rules with the ``.escape`` class selector, but a rule
with ``.string.escape`` will have higher precedence.

The order of the action names does not matter. E.g. an action Text.Comment
will match exactly the same CSS rules as an action Comment.Text. So you
should take some care when designing you action hierachy and not add too much
base action types.

"""


import collections
import itertools
import functools

from . import css
from . import themes
from . import util


class Theme:
    """A Theme maps a StandardAction to a TextFormat with CSS properties."""
    def __init__(self, filename="", stylesheet=""):
        """Instantiate Theme from a CSS file or text.

        If the ``stylesheet`` text is given, it is used as the stylesheet. Only
        if the text is empty, the filename is used to read the stylesheet from.

        """
        self._filename = filename
        self._css_text = stylesheet
        self.TextFormat = TextFormat

    @classmethod
    def byname(cls, name="default"):
        """Create Theme by name.

        The name is a CSS file in the themes/ directory, without the ".css"
        extension.

        """
        return cls(themes.filename(name))

    @util.cached_property
    def _stylesheet(self):
        """Load and cache the StyleSheet."""
        if self._css_text or not self._filename:
            return css.StyleSheet.from_text(self._css_text, self._filename)
        else:
            return css.StyleSheet.from_file(self._filename)

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

        The role may be any string that maps to a CSS class in the theme
        CSS file that is available there together with the 'parce' class.

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
        ``"trialing-whitespace"``
            The TextFormat (use only the *background*) to highlight trialing
            whitespace, if desired.
        ``"eol-marker"``
            The *color* to draw a "end-of-line" marker with, if desired

        The state argument may be "default", "focus", or "disabled", and
        reflects the state of the user interface the style variant is used for.

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
        class_ = repr(action).lower().replace('.', ' ')
        e = css.Element(class_=class_, parent=css.Element(class_="parce"))
        return self.TextFormat(self.style.select_element(e).properties())

    def tokens(self, theme_context, tree, start=0, end=None):
        """Yield tokens from ``tree.tokens_range(start, end)``.

        If a context is entered, ``theme_context.push(language)`` is called
        with the language of the context's lexicon. If the context is left,
        ``theme_context.pop()`` is called.

        In Theme, the ``theme_context`` argument is unused.

        """
        yield from tree.tokens_range(start, end)


class MetaTheme:
    """A Theme that encapsulates a default Theme and per-language sub-Themes."""
    def __init__(self, theme):
        """Instantiate with default theme."""
        self._theme = theme
        self._themes = {}
        self._add_window = {theme: False}

    def add_theme(self, language, theme, add_window=False):
        """Add a specific Theme for the specified Language.

        If ``add_window`` is set to True, the formatter will render text from
        the specified language with its own ``window`` default style added to
        all formats. A formatter will also need to take care to render
        untokenized ranges with the ``window()`` style of the sub-theme.

        """
        self._themes[language] = theme
        self._add_window[theme] = add_window

    def get_theme(self, language):
        """Return the tuple(theme, add_window) for the language.

        If the exact language was not found, the base classes of the Language are
        tried. If still no luck, self is returned.

        """
        try:
            return self._themes[language]
        except KeyError:
            pass
        for lang in language.mro()[:-2]:    # don't test Language and object
            try:
                return self._themes[lang]
            except KeyError:
                pass
        return self

    def get_add_window(self, theme):
        """Return the ``add_window`` value that was set when adding this sub-theme."""
        return self._add_window.get(theme, False)

    def baseformat(self, role="window", state="default"):
        """Return the base TextFormat for the rold and state of the default theme."""
        return self._theme.baseformat(state)

    def textformat(self, action):
        """Return the TextFormat for the specified action of the default theme."""
        return self._theme.textformat(action)

    def tokens(self, theme_context, tree, start=0, end=None):
        """Yield tokens from ``tree.tokens_range(start, end)``.

        If a context is entered, ``theme_context.push(language)`` is called
        with the language of the context's lexicon. If the context is left,
        ``theme_context.pop()`` is called.

        The theme_context can switch the theme, based on the current language.

        """
        for context, slice_ in tree.context_slices(start, end):
            theme_context.push(context.lexicon.language)
            for n in context[slice_]:
                stack = []
                i = 0
                while True:
                    for i in range(i, len(n)):
                        m = n[i]
                        if m.is_token:
                            yield m
                        else:
                            stack.append(i)
                            i = 0
                            n = m
                            theme_context.push(n.lexicon.language)
                            break
                    else:
                        if stack:
                            theme_context.pop()
                            n = n.parent
                            i = stack.pop() + 1
                        else:
                            break
            theme_context.pop()


class TextFormat:
    """Simple textformat that reads CSS properties and supports a subset of those.

    This factory is used by default by Theme, but you can implement your own.
    Such a factory only needs to implement an ``__init__`` method that reads
    the dictionary of property Value lists returned by Style.properties().

    A TextFormat has a False boolean value if no single property is set.

    You can add and subtract TextFormats::

        >>> import parce
        >>> t = parce.theme_by_name()
        >>> f = t.window()
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

    dispatch = util.Dispatcher()

    def __repr__(self):
        return "<{} {}>".format(self.__class__.__name__,
            ", ".join("{}={}".format(key, repr(value))
                                for key, value in sorted(self.__dict__.items())))

    def __init__(self, properties):
        for prop, values in properties.items():
            self.dispatch(prop, values)

    def __bool__(self):
        """Return True if at least one property is set."""
        return bool(self.__dict__)

    def __sub__(self, other):
        """Return a new TextFormat with the properties removed that are the same in ``other``."""
        new = type(self)({})
        for props in (
            ('color',),
            ('background_color',),
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

    @dispatch("color")
    def read_color(self, values):
        for v in values:
            if v.color:
                self.color = v.color
                return

    @dispatch("background-color")
    def read_background_color(self, values):
        for v in values:
            if v.color:
                self.background_color = v.color
                return

    @dispatch("background")
    def read_background(self, values):
        self.read_background_color(values)

    @dispatch("text-decoration-color")
    def read_text_decoration_color(self, values):
        for v in values:
            if v.color:
                self.text_decoration_color = v.color
                return

    @dispatch("text-decoration-line")
    def read_text_decoration_line(self, values):
        decos = []
        for v in values:
            if v.text in ("underline", "overline", "line-through"):
                decos.append(v.text)
            elif v.text == "none":
                decos.clear()
        self.text_decoration_line = decos

    @dispatch("text-decoration-style")
    def read_text_decoration_style(self, values):
        for v in values:
            if v.text in ("solid", "double", "dotted", "dashed", "wavy"):
                self.text_decoration_style = v.text
                return

    @dispatch("text-decoration")
    def read_text_decoration(self, values):
        self.read_text_decoration_color(values)
        self.read_text_decoration_line(values)
        self.read_text_decoration_style(values)

    @dispatch("font-family")
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

    @dispatch("font-kerning")
    def read_font_kerning(self, values):
        for v in values:
            if v.text in ("auto", "normal", "none"):
                self.font_kerning = v.text
                return

    @dispatch("font-size")
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

    @dispatch("font-stretch")
    def read_font_stretch(self, values):
        for v in values:
            if v.text in ("ultra-condensed", "extra-condensed", "condensed",
                          "semi-condensed", "semi-expanded", "expanded",
                          "extra-expanded", "ultra-expanded"):
                self.font_stretch = v.text
            elif v.number is not None and v.unit == "%":
                self.font_stretch = v.number

    @dispatch("font-style")
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

    @dispatch("font-variant-caps")
    def read_font_variant_caps(self, values):
        for v in values:
            if v.text in ("normal", "small-caps", "all-small-caps", "petite-caps",
                          "all-petite-caps", "unicase", "titling-caps"):
                self.font_variant_caps = v.text
                return

    @dispatch("font-variant-position")
    def read_font_variant_position(self, values):
        for v in values:
            if v.text in ("normal", "sub", "super"):
                self.font_variant_position = v.text
                return

    @dispatch("font-weight")
    def read_font_weight(self, values):
        for v in values:
            if v.text in ("normal", "bold", "lighter", "bolder"):
                self.font_weight = v.text
                return
            elif v.number is not None:
                self.font_weight = v.number
                return

    @dispatch("font")
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


