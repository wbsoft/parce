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
Validates all languages with pytest.
"""

import importlib
import os
import glob
import sys

sys.path.insert(0, ".")

import parce.lang
import parce.validate

def get_all_languages():
    filenames = [
        os.path.splitext(os.path.basename(filename))[0]
        for filename in glob.glob(os.path.join(parce.lang.__path__[0], "*.py"))]

    for f in filenames:
        modname = 'parce.lang.' + f
        mod = importlib.import_module(modname)
        for name, obj in mod.__dict__.items():
            if isinstance(obj, type) and issubclass(obj, parce.Language) and obj.__module__ == modname:
                yield obj


for lang in get_all_languages():
    assert parce.validate.validate_language(lang) is True


