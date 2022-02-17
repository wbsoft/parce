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
Parse XSLT.

"""

__all__ = ('Xslt',)

from parce.lang.xml import Xml
from parce.rule import TEXT, ifeq, ifmember
from parce.action import Keyword


class Xslt(Xml):
    """Xslt is also valid Xml, give Xslt tags the Keyword action."""
    @classmethod
    def tag_action(cls):
        """Reimplemented to return Keyword for known Xslt tag names."""
        default = super().tag_action()
        return ifeq(TEXT[:4], "xsl:",
            ifmember(TEXT[4:], XSLT_ELEMENTS, Keyword, default), default)


XSLT_ELEMENTS = (
    'apply-imports', 'apply-templates', 'attribute', 'attribute-set',
    'call-template', 'choose', 'comment', 'copy', 'copy-of', 'decimal-format',
    'element', 'fallback', 'for-each', 'if', 'import', 'include', 'key',
    'message', 'namespace-alias', 'number', 'otherwise', 'output', 'param',
    'preserve-space', 'processing-instruction', 'sort', 'strip-space',
    'stylesheet', 'template', 'text', 'transform', 'value-of', 'variable',
    'when', 'with-param'
)
