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
This module supports highlighting styles using Cascading Style Sheets (CSS).

Also contains some utility functions to further digest a tree structure
originating from the Css parser in the parce.lang.css module.

"""


import collections

from . import *
from .lang.css import *
from .query import Query



Rule = collections.namedtuple("Rule", "selectors properties")


def css_classes(action):
    """Return a tuple of lower-case CSS class names for the specified standard action."""
    return tuple(a._name.lower() for a in action)


def remove_comments(nodes):
    """Yield the nodes with comments removed."""
    for n in node:
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


def get_rules(tree):
    """Get all the CSS rules from the tree.

    Every rule is a two-tuple(selectors, declarations), where selectors
    is a list of nodes containing all the selectors, and declarations a dictionary
    mapping property name to a list of nodes representing the value.

    Empty rules, i.e. rules with no declarations between the { } are skipped.

    """
    for rule in tree.query.all(Css.rule):
        if len(rule) > 1:
            # get the selectors:
            selectors = []
            for node in rule.source().left_siblings():
                if node.is_context:
                    if node.lexicon is Css.rule:
                        break
                    elif node.lexicon is Css.comment:
                        continue
                elif node.action is Comment:
                    continue
                selectors.append(node)
            selectors.reverse()
            # get the property declarations:
            properties = {}
            for declaration in rule.query.children(Css.declaration):
                propname = get_ident_token(declaration[0])
                value = declaration[2:] if declaration[1] == ":" else declaration[1:]
                properties[propname] = value
            yield Rule(selectors, properties)


def calculate_specificity(selectors):
    """Calculate the specificity of the list of selectors.

    Returns a three-tuple (ids, clss, elts), where ids is the number of ID
    selectors, clss the number of class, attribute or pseudo-class selectors,
    and elts the number of element or pseudo-elements.

    Currently, does not handle functions like :not(), :is(), although that
    would not be difficult to implement.

    """
    q = Query.from_nodes(selectors)
    ids = q.all(Css.id_selector).count()
    clss = q.all(Css.attribute_selector, Css.class_selector, Css.pseudo_class).count()
    elts = q.all(Css.selector, Css.pseudo_element).count()
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

    Just looks at class names, does not use combinators.
    (Enough for internal styling :-).

    """
    for rule in rules:
        for c in Query.from_nodes(rule.selectors).all(Css.class_selector):
            if get_ident_token(c) in classes:
                yield rule
                break

