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
This module provides a registry for all the bundled languages.

External language definitions can at runtime also be added to this
registry.

You can find languages based on filename, mimetype, or guess the
language to use based on text contents.


"""

import importlib


# BEGIN REGISTRY
registry = {}
# END REGISTRY


def register(**kwargs):
    r'''Register a Language definition class.

    Use as a class decorator for Language classes you want to add to the
    registry::

        @register(
            name = "mylanguage",
            filenames = ["*.mylang"],
            mimetypes = ["text/x-mylang", "application/mylang"],
            guess = [(r"^#!.*?mylang\b", 1)],
        )
        class MyLanguage(Language):
            """Parses my stuff."""
            @lexicon
            def root(cls):
                pass # etc


    The following keyword arguments can be specified:

    ``name``
        the name, defaulting to the class name lowercased.
    ``description``
        a description, defaulting to the language class doc string
    ``filenames``
        a list of common filename patterns
    ``mimetypes``
        a list of mime types
    ``guess``
        a list of (regex, priority) tuples. All regular expressions are tried,
        and the highest priority wins (values in the 0..1 range).
    ``root``
        name of the root lexicon, defaulting to "root"

    Other keyword arguments are allowed and may find future use cases.

    '''
    def decorator(cls):
        d = dict(
            name = cls.__name__.lower(),
            description = cls.__doc__,
        )
        d.update(kwargs)
        key = cls.__module__ + '.' + cls.__name__
        registry[key] = d
        return cls
    return decorator


def root_lexicon(key):
    """Import Language class for the key and return the root lexicon."""
    root = registry[key].get('root', 'root')
    module, classname = key.rsplit('.', 1)
    mod = importlib.import_module(module)
    cls = getattr(mod, classname)
    return getattr(cls, root)


