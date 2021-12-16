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
The parce Python module.

The main module provides the listed classes and functions, enough to build
a basic language definition or to use the bundled language definitions.

The standard actions that are used by the bundled language definitions to
specify the type of parsed text fragments are in the :mod:`~parce.action`
module. The helper functions for dynamic rule items are in the
:mod:`~parce.rule` module.

It is recommended to import *parce* like this::

    import parce

although in a language definition it can be easier to do this::

    from parce import Language, lexicon, skip, default_action, default_target
    from parce.rule import words, bygroup   # whichever you need
    import parce.action as a

Then you get the ``Language`` class and ``lexicon`` decorator from parce, and
all standard actions can be accessed via the ``a`` prefix, like ``a.Text``.

.. py:data:: version

   The version as a three-tuple(major, minor, patch). See :mod:`~parce.pkginfo`.

.. py:data:: version_string

   The version as a string.

"""

# imported when using from parce import *
__all__ = (
    # important classes
    'Document',
    'Cursor',

    # toplevel functions
    'events',
    'find',
    'root',
    'theme_by_name',
    'theme_from_file',

    # often used names when defining languages
    'Language',
    'default_action',
    'default_target',
    'lexicon',
    'skip',
)

from . import document, lexer, rule, ruleitem, treebuilder, work, util
from .language import Language
from .document import Cursor
from .pkginfo import version, version_string


def lexicon(rules_func=None, **kwargs):
    """Lexicon factory decorator.

    Use this decorator to make a function in a Language class definition a
    LexiconDescriptor object. The LexiconDescriptor is a descriptor, and when
    calling it via the Language class attribute, a Lexicon is created, cached
    and returned.

    You can specify keyword arguments, that will be passed on to the Lexicon
    object as soon as it is created.

    The following keyword arguments are supported:

    ``re_flags`` (0):
        The flags that are passed to the regular expression compiler

    ``consume`` (False):
        When set to True, tokens originating from a rule that pushed this
        lexicon are added to the target Context instead of the current.

    The code body of the function should return (yield) the rules of the
    lexicon, and is run with the Language class as first argument, as soon as
    the lexicon is used for the first time.

    You can also call the Lexicon object just as an ordinary classmethod, to
    get the rules, e.g. for inclusion in a different lexicon.

    """
    from parce.lexicon import LexiconDescriptor
    if rules_func and not kwargs:
        return LexiconDescriptor(rules_func)
    def lexicon(rules_func):
        return LexiconDescriptor(rules_func, **kwargs)
    return lexicon


class Document(work.WorkerDocumentMixin, document.Document):
    """A Document that automatically keeps its contents tokenized.

    A Document holds an editable text string and keeps the tokenized tree and
    (if a Transformer is used) the transformed result up to date on every text
    change. Arguments:

    ``root_lexicon``:
        The root lexicon to use (default None)

    ``text``:
        The initial text (default the empty string)

    ``worker``:
        Use the specified :class:`~.work.Worker`. By default, a
        :class:`~.work.BackgroundWorker` is used

    ``transformer``:
        Use the specified :class:`~.transform.Transformer`. By default, no
        Transformer is installed. As a convenience, you can specify ``True``,
        in which case a default Transformer is installed

    In addition to the events mentioned in the :class:`.document.Document` base
    class, the following events are emitted:

    ``"tree_updated" (start, end)``:
        emitted when the tokenized tree has been updated; the handler is called
        with two arguments: ``start``, ``end``, that denote the updated text
        range

    ``"tree_finished"``:
        emitted when the tokenized tree has been updated; the handler is called
        without arguments

    ``"transform_finished"``:
        emitted when a transform rebuild has finished; the handler is called
        without arguments

    Using the :meth:`~.util.Observable.connect` method you can connect to these
    events.

    With the :meth:`~.work.WorkerDocumentMixin.get_root` method you get the
    parsed tree. An example::

        >>> d = parce.Document(parce.find('xml'), '<xml>Hi!</xml>')
        >>> d.get_root(True).dump()
        <Context Xml.root at 0-14 (4 children)>
         ├╴<Token '<' at 0:1 (Delimiter)>
         ├╴<Token 'xml' at 1:4 (Name.Tag)>
         ├╴<Token '>' at 4:5 (Delimiter)>
         ╰╴<Context Xml.tag at 5-14 (4 children)>
            ├╴<Token 'Hi!' at 5:8 (Text)>
            ├╴<Token '</' at 8:10 (Delimiter)>
            ├╴<Token 'xml' at 10:13 (Name.Tag)>
            ╰╴<Token '>' at 13:14 (Delimiter)>
        >>> d[5:8] = "hello there!"             # replace the text "Hi!"
        >>> d.get_root(True).dump()
        <Context Xml.root at 0-23 (4 children)>
         ├╴<Token '<' at 0:1 (Delimiter)>
         ├╴<Token 'xml' at 1:4 (Name.Tag)>
         ├╴<Token '>' at 4:5 (Delimiter)>
         ╰╴<Context Xml.tag at 5-23 (4 children)>
            ├╴<Token 'hello there!' at 5:17 (Text)>
            ├╴<Token '</' at 17:19 (Delimiter)>
            ├╴<Token 'xml' at 19:22 (Name.Tag)>
            ╰╴<Token '>' at 22:23 (Delimiter)>

    If you use a Transformer, the transformed result is also kept up to date.
    The :meth:`~.work.WorkerDocumentMixin.get_transform` method gives you the
    transformed result. For example::

        >>> import parce
        >>> d = parce.Document(parce.find('json'), '{"key": [1, 2, 3, 4, 5, 6, 7, 8, 9]}', transformer=True)
        >>> d.get_transform(True)
        {'key': [1, 2, 3, 4, 5, 6, 7, 8, 9]}

    """
    def __init__(self, root_lexicon=None, text="", worker=None, transformer=None):
        document.Document.__init__(self, text)
        if transformer is True:
            from . import transform
            transformer = transform.Transformer()
        if worker is None:
            worker = work.BackgroundWorker(treebuilder.TreeBuilder(root_lexicon), transformer)
        else:
            root = worker.builder().root
            root.clear()
            root.lexicon = root_lexicon
            if transformer:
                worker.set_transformer(transformer)
        work.WorkerDocumentMixin.__init__(self, worker)
        if text:
            worker.update(text)
        worker.connect("tree_finished", self._slot_tree_finished)
        worker.connect("transform_finished", self._slot_transform_finished)

    def _slot_tree_finished(self):
        b = self.builder()
        self.emit("tree_updated", b.start, b.end)
        self.emit("tree_finished")

    def _slot_transform_finished(self):
        self.emit("transform_finished")


def find(name=None, *, filename=None, mimetype=None, contents=None):
    """Find a root lexicon, either by language name, or by filename, mimetype
    and/or contents.

    If you specify a name, tries to find the language with that name, ignoring
    the other arguments.

    If you don't specify a name, but instead one or more of the other (keyword)
    arguments, tries to find the language based on filename, mimetype or
    contents.

    If a language is found, returns the root lexicon. If no language could be
    found, None is returned (which can also be used as root lexicon, resulting
    in an empty token tree).

    Examples::

        >>> import parce
        >>> parce.find("xml")
        Xml.root
        >>> parce.find(contents='{"key": 123;}')
        Json.root
        >>> parce.find(filename="style.css")
        Css.root

    This function uses the :mod:`~parce.registry` module and by default it
    finds all bundled languages. See the module's documentation to find out how
    to add your own languages to a registry.

    """
    from . import registry
    if name:
        lexicon_name = registry.find(name)
    else:
        for lexicon_name in registry.suggest(filename, mimetype, contents):
            break
        else:
            return
    if lexicon_name:
        return registry.root_lexicon(lexicon_name)


def root(root_lexicon, text):
    """Return the root context of the tree structure of all tokens from text."""
    return treebuilder.build_tree(root_lexicon, text)


def events(root_lexicon, text):
    """Convenience function that yields all the events from the text."""
    return lexer.Lexer([root_lexicon]).events(text)


def theme_by_name(name="default"):
    """Return a Theme from the default themes in the themes/ directory."""
    from . import theme, themes
    return theme.Theme(themes.filename(name))


def theme_from_file(filename):
    """Return a Theme loaded from the specified CSS filename."""
    from .theme import Theme
    return Theme(filename)


# these can be used in rules where a pattern is expected
default_action = util.Symbol("default_action")   #: denotes a default action for unmatched text
default_target = util.Symbol("default_target")   #: denotes a default target when no text matches


#: A dynamic action that yields no tokens, thereby ignoring the matched text.
skip = ruleitem.SkipAction()

