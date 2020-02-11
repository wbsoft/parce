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
Formatter for HTML output.

This module is in development, and in pre-alpha stage :-)

"""

import parce.formatter


def escape(text):
    """Escape &, < and >."""
    return text.replace('&', "&amp;").replace('<', "&lt;").replace('>', "&gt;")


def attrescape(text):
    """Escape &, <, > and "."""
    return escape(text).replace('"', "&quot;")


def html(tokens, text, theme):
    """Test function to convert text to colored html using theme.

    The text must also be specified because not all text may be covered by
    the tokens.

    """
    f = parce.formatter.Formatter(theme, span_factory_inline)
    yield '<html>'
    yield '<div style="{}"><pre nowrap="nowrap">'.format(attrescape(f.window()))
    oldend = 0
    for pos, end, style, window in f.format_ranges(tokens):
        if pos > oldend:
            yield escape(text[oldend:pos])
        yield '<span style="{}">{}</span>'.format(attrescape(style), escape(text[pos:end]))
        oldend = end
    if oldend < len(text):
        yield escape(text[oldend:])
    yield '</pre></div>'
    yield '</html>'



def span_factory_inline(textformat):
    """Convert a TextFormat to an inline style string."""
    d = textformat.css_properties()
    if d:
        return ' '.join(sorted('{}: {};'.format(prop, value) for prop, value in d.items()))


