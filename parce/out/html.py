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


r"""
Formatter for HTML output.

This module contains two formatters that can create HTML output:
:class:`HtmlFormatter` and :class:`SimpleHtmlFormatter`. The first converts
format settings from a theme to inline CSS style attributes; the latter just
puts the class names in the HTML and you should link to a CSS file yourself.

Usage example::

    >>> from parce import Cursor, Document, find, theme_by_name
    >>> from parce.out.html import HtmlFormatter
    >>> d = Document(find("xml"), '''<xml attr="value">text</xml>\n''')
    >>> f = HtmlFormatter(theme_by_name('dark'))
    >>> print(f.full_html(Cursor(d, 0, None)))
    <!DOCTYPE html>
    <html>
      <head>
        <meta charset="utf-8"/>
      </head>
      <body>
        <div class="parce">
    <pre style="white-space: pre; background-color: #000000; color: #fffff0; fon
    t-family: monospace; font-size: 12pt;">&lt;<span style="color: #87cefa; font
    -weight: bold;">xml</span> <span style="color: #1e90ff;">attr</span>=<span s
    tyle="color: #cd5c5c;">"value"</span>&gt;text&lt;/<span style="color: #87cef
    a; font-weight: bold;">xml</span>&gt;
    </pre>
        </div>
      </body>
    </html>


"""

import parce.formatter

FULL_HTML_TEMPLATE = """<!DOCTYPE html>
<html>
  <head>
    <meta charset="{charset}"/>
  </head>
  <body>
    <div class="parce">
<pre style="white-space: pre; {baseformat}">{html}</pre>
    </div>
  </body>
</html>
"""



class HtmlMixin:
    """Helper class containing extra methods to generate HTML output."""
    def full_html(self, cursor, charset="utf-8"):
        """Returns the selected text as a complete HTML document.

        The charset is included in the HTML header, but the returned string is
        still a Python string; you should take care of the encoding yourself
        when writing the HTML to an output device.

        """
        return FULL_HTML_TEMPLATE.format(
            charset = charset,
            baseformat = self.baseformat() or "",
            html = self.html(cursor))


class HtmlFormatter(HtmlMixin, parce.formatter.Formatter):
    """A Formatter to output HTML."""
    def __init__(self, theme=None, factory=None):
        if factory is None:
            factory = lambda tf: inline_css(tf) or None
        super().__init__(theme, factory)

    def html(self, cursor):
        """Return HTML output for the selected range of the cursor.

        The text pieces that have some textformat are wrapped in ``<span
        style="">...</span>`` tags with inline CSS attributes. The returned
        HTML expects to be wrapped in a <pre> tag.

        Example::

            >>> from parce.out.html import HtmlFormatter
            >>> from parce import Cursor, Document, find, theme_by_name
            >>> d = Document(find('css'), "h1 { color: red; }")
            >>> f = HtmlFormatter(theme_by_name())
            >>> f.html(Cursor(d, 0, None))
            '<span style="color: #00008b; font-weight: bold;">h1</span> <span sty
            le="font-weight: bold;">{</span> <span style="color: #4169e1; font-we
            ight: bold;">color</span>: <span style="color: #2e8b57;">red</span>;
            <span style="font-weight: bold;">}</span>'

        """
        span = '<span style="{}">{}</span>'.format
        return "".join(
            span(attrescape(fmt), escape(text)) if fmt else escape(text)
            for text, fmt in self.format_document(cursor))


class SimpleHtmlFormatter(HtmlMixin, parce.formatter.SimpleFormatter):
    """A simple Formatter that produces HTML with classes.

    This HTML should then be used with a css file to see the
    highlighting.

    """
    def html(self, cursor):
        """Return HTML output for the selected range of the cursor.

        The text pieces that have a standard action are wrapped in ``<span
        class="xxx">..</span>`` tags, where the class names correspond with
        the standard actions.

        The returned HTML expects to be wrapped in a <div> or <pre> with class
        ``"parce"``, so that the CSS rules match with the contents.

        An example::

            >>> from parce.out.html import SimpleHtmlFormatter
            >>> from parce import Cursor, Document, find, theme_by_name
            >>> d = Document(find('css'), "h2 { color: blue; }")
            >>> f = SimpleHtmlFormatter()
            >>> f.html(Cursor(d, 0, None))
            '<span class="name tag">h2</span> <span class="delimiter bracket">{</
            span> <span class="name property definition">color</span><span class=
            "delimiter">:</span> <span class="literal color">blue</span><span cla
            ss="delimiter">;</span> <span class="delimiter bracket">}</span>'

        """
        span = '<span class="{}">{}</span>'.format
        return "".join(
            span(attrescape(fmt), escape(text)) if fmt else escape(text)
            for text, fmt in self.format_document(cursor))


def escape(text):
    r"""Escape &, < and > to use text in HTML."""
    return text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")


def attrescape(text):
    r"""Escape &, <, > and ", to use text in HTML."""
    return escape(text).replace('"', "&quot;")


def inline_css(textformat):
    """Convert a textformat to an inline CSS string.

    The resulting string can be used in a Html ``style`` attribute.

    """
    props = textformat.css_properties()
    return " ".join("{}: {};".format(prop, value)
        for prop, value in sorted(props.items()))

