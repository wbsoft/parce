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
This directory contains the CSS files for the bundled themes.

See the :doc:`theme <theme>` module for the supporting code.

"""


import glob
import os


def filename(name):
    """Convert theme name to the CSS file in this directory.

    E.g. "default" translates to "/usr/lib/python/3.x/parce/themes/default.css",
    depending on where parce was installed.

    """
    return os.path.join(__path__[0], name + '.css')


def get_all_themes():
    """Return the sorted list of CSS theme names in ``parce.themes``.

    Only the names are returned, without the '.css' extension.
    Files that start with an underscore are skipped.

    """
    names = []
    for filename in glob.glob(os.path.join(__path__[0], "*.css")):
        name = os.path.splitext(os.path.basename(filename))[0]
        if not name.startswith('_'):
            names.append(name)
    names.sort()
    return names


