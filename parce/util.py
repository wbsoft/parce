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
Various utility classes and functions.
"""

import re
import codecs
import functools
import threading
import weakref


class Dispatcher:
    """Dispatches calls via an instance to methods based on the first argument.

    A Dispatcher is used as a decorator when defining a class, and then called
    via an instance to select a method based on the first argument (which must
    be hashable).

    If you override methods in a subclass that were dispatched, the
    dispatcher automatically dispatches to the new method. If you want to add
    new keywords in a subclass, just create a new Dispatcher with the same
    name. It will automatically inherit the references stored in the old
    dispatcher.

    Usage::

        class MyClass:
            dispatch = Dispatcher()

            @dispatch(1)
            def call_one(self, value):
                print("One called", value)

            @dispatch(2)
            def call_two(self, value):
                print("Two called", value)

            def handle_input(self, number, value):
                self.dispatch(number, value)

        >>> i = MyClass()
        >>> i.handle_input(2, 3)
        Two called 3

    Values of the first argument that are not handled are normally silently
    ignored, but you can also specify a default function, that is called when
    a value is not handled::

        class MyClass:
            @Dispatcher
            def dispatch(self, number, value):
                print("Default function called:", number, value)

            @dispatch(1)
            def call_one(self, value):
                print("One called", value)

            @dispatch(2)
            def call_two(self, value):
                print("Two called", value)

            def handle_input(self, number, value):
                self.dispatch(number, value)

        >>> i = MyClass()
        >>> i.handle_input(3, 10)
        Default function called: 3 10


    """

    def __init__(self, default_func=None):
        self._table = {}
        self._tables = weakref.WeakKeyDictionary()
        self._default_func = default_func

    def __call__(self, *args):
        def decorator(func):
            for a in args:
                self._table[a] = func.__name__
            return func
        return decorator

    def __get__(self, instance, owner):
        try:
            table = self._tables[owner]
        except KeyError:
            # find our name, and find Dispatchers in base classes with same name
            # if found, inherit their references
            if self._default_func:
                mro = iter(owner.mro()[1:])
                name = self._default_func.__name__
            else:
                mro = iter(owner.mro())
                def get_name():
                    for c in mro:
                        for n, v in c.__dict__.items():
                            if v is self:
                                return n
                name = get_name()
            dispatchers = []
            for c in mro:
                d = c.__dict__.get(name)
                if type(d) is type(self):
                    dispatchers.append(d)
            _table = {}
            for d in reversed(dispatchers):
                _table.update(d._table)
            _table.update(self._table)
            # now, store the actual functions instead of their names
            table = self._tables[owner] = {a: getattr(owner, name)
                        for a, name in _table.items()}
        def func(key, *args, **kwargs):
            f = table.get(key)
            if f:
                return f(instance, *args, **kwargs)
            if self._default_func:
                return self._default_func(instance, key, *args, **kwargs)
        return func


def cached_method(func):
    """Wrap a method and caches its return value.

    The method argument tuple should be hashable. Keyword arguments are not
    supported. The cache is tread-safe. Does not keep a reference to the
    instance.

    """
    _cache = weakref.WeakKeyDictionary()
    _lock = threading.Lock()
    @functools.wraps(func)
    def wrapper(self, *args):
        try:
            return _cache[self][args]
        except KeyError:
            with _lock:
                try:
                    return _cache[self][args]
                except KeyError:
                    v = _cache.setdefault(self, {})[args] = func(self, *args)
                    return v
    return wrapper


def cached_property(func):
    """Like property, but caches the computed value."""
    return property(cached_method(func))


def abbreviate_repr(s, length=30):
    """Elegantly abbreviate repr text."""
    if len(s) > length:
        return repr(s[:length-2]) + "..."
    return repr(s)


def merge_adjacent(stream, factory=tuple):
    """Yield items from a stream of tuples.

    The first two items of each tuple are regarded as pos and end.
    If they are adjacent, and the rest of the tuples compares the same,
    the items are merged.

    Instead of the default factory `tuple`, you can give a named tuple
    or any other type to wrap the streams items in.

    """
    stream = iter(stream)
    for pos, end, *rest in stream:
        for npos, nend, *nrest in stream:
            if nrest != rest or npos > end:
                yield factory(pos, end, *rest)
                pos, rest = npos, nrest
            end = nend
        yield factory(pos, end, *rest)


def merge_adjacent_actions(tokens):
    """Yield three-tuples (pos, end, action).

    Adjacent actions that are the same are merged into
    one range.

    """
    return merge_adjacent((t.pos, t.end, t.action) for t in tokens)


def merge_adjacent_actions_with_language(tokens):
    """Yield four-tuples (pos, end, action, language).

    Adjacent actions that are the same and occurred in the same language
    are merged into one range.

    """
    return merge_adjacent((t.pos, t.end, t.action, t.parent.lexicon.language)
                          for t in tokens)


def get_bom_encoding(data):
    """Get the BOM (Byte Order Mark) of data, if any.

    A two-tuple is returned (encoding, data). If the data starts with a BOM
    mark, its encoding is determined and the BOM mark is stripped off.
    Otherwise, the returned encoding is None and the data is returned
    unchanged.

    """
    for bom, encoding in (
        (codecs.BOM_UTF8, 'utf-8'),
        (codecs.BOM_UTF16_LE, 'utf_16_le'),
        (codecs.BOM_UTF16_BE, 'utf_16_be'),
        (codecs.BOM_UTF32_LE, 'utf_32_le'),
        (codecs.BOM_UTF32_BE, 'utf_32_be'),
            ):
        if data.startswith(bom):
            return encoding, data[len(bom):]
    return None, data


def split_list(l, separator):
    """Split list on items that compare equal to separator.

    Yields result lists that may be empty.

    """
    try:
        i = l.index(separator)
    except ValueError:
        yield l
    else:
        yield l[:i]
        yield from split_list(l[i+1:], separator)


def quote(s):
    """Like repr, but return s with double quotes, escaping " and \\."""
    return '"' + re.sub(r'([\\"])', r'\\\1', s) + '"'
