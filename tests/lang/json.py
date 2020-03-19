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


from parce.lang.json import Json

def examples():
    yield Json.root, r"""{
  "title": "Frescobaldi",
  "background": "background.png",
  "icon-size": 80,
  "contents": [
    { "x": 449, "y": 320, "type": "link", "path": "/Applications"},
    { "x": 188, "y": 320, "type": "file", "path": "../dist/Frescobaldi.app"},
    { "x": 100, "y": 70, "type": "file", "path": "../README.txt" },
    { "x": 100, "y": 185, "type": "file", "path": "../ChangeLog.txt" },
    { "x": 540, "y": 70, "type": "file", "path": "../COPYING.txt" }
  ]
}
"""
