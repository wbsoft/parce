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
This module contains utility functions to further digest a tree structure
originating from the Css parser in the parce.lang.css module.

The module will be used by the theme module.

Workflow:

    1. load a mixed list of Rule or Condition instances from a file, using
       ``load_rules()``, or create one from a tree using ``get_rules()``

       You can chain multiple lists from different sources.

    2. filter out the Condition instances, either using or ignoring the rules
       in the conditions. Currently filter_rules lets everything through; but
       filters to implement @media, @document, @supports queries could be
       written.

    3. Use ``sort_rules()`` to sort the rules on specificity. You can store
       the resulting list of rules to use it multiple times.

    4. Use a ``select`` method (currently only ``select_class``, but more
       can be implemented) to select rules based on their selectors.

    5. Use ``combine_properties()`` to combine the properties of the selected
       rules to get a dictionary of the CSS properties that apply.

Example::

    >>> import parce.css
    >>> rules = parce.css.load_rules("parce/themes/default.css")
    >>> rules = parce.css.filter_rules(rules)
    >>> combine_properties(select_class(sort_rules(rules), 'comment'))
    {'font-style': [<Context Css.identifier at 1037-1043 (1 children)>],
     'color': [<Token '#666' at 1056:1060 (Literal.Color)>]}


"""


import collections
import os

from . import *
from .lang.css import Css
from .query import Query


Rule = collections.namedtuple("Rule", "selectors properties")
Condition = collections.namedtuple("Condition", "condition rules")


def css_classes(action):
    """Return a tuple of lower-case CSS class names for the specified standard action."""
    return tuple(a._name.lower() for a in action)


def remove_comments(nodes):
    """Yield the nodes with comments removed."""
    for n in nodes:
        if (n.is_token and n.action is Comment) or (
            n.is_context and n.lexicon is Css.comment):
            continue
        yield n


def unescape(text):
    """Return the unescaped character, text is the contents of an Escape token."""
    value = text[1:]
    if value == '\n':
        return ''
    try:
        codepoint = int(value, 16)
    except ValueError:
        return value
    return chr(codepoint)


def get_ident_token(context):
    """Return the ident-token represented by the context.

    The context can be a selector, property, attribute, id_selector or
    class_selector, containing Name and/or Escape tokens.

    """
    def gen():
        for t in context:
            yield unescape(t.text) if t.action is Escape else t.text
    return ''.join(gen())


def get_string(context):
    """Get the string contexts represented by context (dqstring or sqstring)."""
    def gen():
        for t in context[:-1]:  # closing quote is not needed
            yield unescape(t.text) if t.action is String.Escape else t.text
    return ''.join(gen())


def get_url(context):
    """Get the url from the context, which is an url_function context."""
    def gen():
        for n in context[:-1]:
            if n.is_token:
                if t.action is Escape:
                    yield unescape(t.text)
                elif action is Literal.Url:
                    yield t.text
                elif action is String:
                    yield get_string(n.right_sibling())
    return ''.join(gen())


def calculate_specificity(selectors):
    """Calculate the specificity of the list of selectors.

    Returns a three-tuple (ids, clss, elts), where ids is the number of ID
    selectors, clss the number of class, attribute or pseudo-class selectors,
    and elts the number of element or pseudo-elements.

    Currently, does not handle functions like :not(), :is(), although that
    would not be difficult to implement.

    """
    # selector list?
    try:
        i = selectors.index(",")
    except ValueError:
        pass
    else:
        return max(calculate_specificity(selectors[:i]), calculate_specificity(selectors[i+1:]))
    q = Query.from_nodes(selectors).all
    ids = q(Css.id_selector).count()
    clss = q(Css.attribute_selector, Css.class_selector, Css.pseudo_class).count()
    elts = q(Css.element_selector, Css.pseudo_element).count()
    return (ids, clss, elts)


def sort_rules(rules):
    """Stable-sorts the rules with least specific first and then reverses.

    So the most specific is first. When a rule sets a property it should
    not be overridden by another one, unless it has its !important flag set.

    The rules argument may be a generator or iterable aggregating rules from
    multiple sources. A single rule is a two-tuple(selectors, properties) as
    returned by get_rules().

    """
    rules = list(rules)
    rules.sort(key=lambda rule: calculate_specificity(rule.selectors))
    rules.reverse()
    return rules


def combine_properties(rules):
    """Combine the properties of the supplied iterable of rules.

    Returns a dictionary with the properties. Comments, closing delimiters and
    "!important" flags are removed from the property values.

    The most specific property dicts are assumed to be first.

    """
    result = {}
    for rule in rules:
        for key, value in rule.properties.items():
            if key not in result or (
                 "!important" in value and "!important" not in result[key]):
                result[key] = list(remove_comments(value))
    for value in result.values():
        while value and value[-1] in (";", "!important"):
            del value[-1]
    return result


def select_class(rules, *classes):
    """Selects the rules from the list that match at least one of the class names.

    Just looks at the last class name in a selector, does not use combinators.
    (Enough for internal styling :-).

    """
    for rule in rules:
        c = Query.from_nodes(rule.selectors).all(Css.class_selector).pick_last()
        if c and get_ident_token(c) in classes:
            yield rule


def get_rules(tree, filename=None, path=None):
    """Evaluate a parsed CSS file and return a list of Rules or Condition instances.

    A Rule represents one CSS rule with its selectors and its properties.
    A Condition represent an @-rule condition and its nested Rules

    Loads @import files from the local file system.

    """
    rules = []
    for node in tree.query.children(Css.atrule, Css.prelude):
        if node.lexicon is Css.atrule:
            # handle @-rules
            keyword = node[0][0]
            if keyword == "import":
                for s in node.query.children(Css.dqstring, Css.sqstring):
                    fname = get_string(s)
                    fname = os.path.join(os.path.dirname(filename), fname)
                    rules.extend(load_rules(fname, path))
                    break
            elif node[-1].lexicon is Css.atrule_nested:
                rules.append(Condition(node, get_rules(node[-1][-1], filename, path)))
        elif len(node) > 1:   # Css.prelude
            # get the selectors (without ending { )
            selectors = list(remove_comments(node[:-1]))
            if selectors:
                for rule in node.query.right:
                    # get the property declarations:
                    properties = {}
                    for declaration in rule.query.children(Css.declaration):
                        propname = get_ident_token(declaration[0])
                        value = declaration[2:] if declaration[1] == ":" else declaration[1:]
                        properties[propname] = value
                    rules.append(Rule(selectors, properties))
                    break
    return rules


def load_rules(filename, path=None):
    """Load a CSS file and return a list of Rules or Condition instances.

    A Rule represents one CSS rule with its selectors and its properties.
    A Condition represent an @-rule condition and its nested Rules.

    Only loads from the local file system.

    """
    return get_rules(root(Css.root, open(filename).read()), filename, path)


def filter_rules(rules, media=None, supports=None, document=None):
    """Filter out Conditions from the iterable of rules.

    Currently just lets through all nested rules. The media, supports, and
    document arguments are currently unused.

    """
    for r in rules:
        if isinstance(r, Condition):
            yield from filter_rules(r.rules, media, supports, document)
        else:
            yield r

