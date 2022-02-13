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
Tests for the docio module.
"""

## find parce

import sys
sys.path.insert(0, '.')

import parce




def test_main():
    """Write stuff to test here."""
    # detect utf-16 and then also detect xml :-)
    d = parce.Document.from_bytes(
        b'\xff\xfe<\x00?\x00x\x00m\x00l\x00 \x00v\x00e\x00r\x00s\x00i\x00o\x00'
        b'n\x00=\x00"\x001\x00.\x000\x00"\x00 \x00e\x00n\x00c\x00o\x00d\x00i\x00'
        b'n\x00g\x00=\x00"\x00u\x00t\x00f\x00-\x001\x006\x00"\x00?\x00>\x00<\x00'
        b'x\x00m\x00l\x00 \x00a\x00t\x00t\x00r\x00=\x00"\x00v\x00a\x00l\x00u\x00'
        b'e\x00"\x00/\x00>\x00')
    assert d.text() == '<?xml version="1.0" encoding="utf-16"?><xml attr="value"/>'

    d = parce.Document(parce.find('lilypond'), r'\header { composer = "Gabriël Fauré" }')
    assert d.to_bytes() == b'\\header { composer = "Gabri\xc3\xabl Faur\xc3\xa9" }'



if __name__ == "__main__":
    test_main()

