# -*- coding: utf-8 -*-
#
# This file is part of the livelex Python package.
#
# Copyright © 2019 by Wilbert Berendsen <info@wilbertberendsen.nl>
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
Editor defines a simple way to apply multiple changes
to a document at once.

"""



class Editor:
    def __init__(self, document):
        self._document = document
        self._changes = []

    def __setitem__(self, key, value):
        if isinstance(key, slice):
            start = key.start or 0
            end = key.stop
        else:
            start = key
            end = key + 1
        self._changes.append((start, end, value))

    def __delitem__(self, key):
        self[key] = ""


