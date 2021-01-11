Accessing the Tree Structure
============================

When you have parsed text, the result is a tree structure of Tokens,
contained by Contexts, which may be nested in other Contexts.

Let's look at the generated token tree of the simple example of the
:doc:`gettingstarted` section::

    >>> tree.dump()
    <Context Nonsense.root at 1-108 (19 children)>
     ├╴<Token 'Some' at 1:5 (Text)>
     ├╴<Token 'text' at 6:10 (Text)>
     ├╴<Token 'with' at 11:15 (Text)>
     ├╴<Token '3' at 16:17 (Literal.Number)>
     ├╴<Token 'numbers' at 18:25 (Text)>
     ├╴<Token 'and' at 26:29 (Text)>
     ├╴<Token '1' at 30:31 (Literal.Number)>
     ├╴<Token '"' at 32:33 (Literal.String)>
     ├╴<Context Nonsense.string at 33-67 (2 children)>
     │  ├╴<Token 'string inside\nover multiple '... at 33:66 (Literal.String)>
     │  ╰╴<Token '"' at 66:67 (Literal.String)>
     ├╴<Token ',' at 67:68 (Delimiter)>
     ├╴<Token 'and' at 69:72 (Text)>
     ├╴<Token '1' at 73:74 (Literal.Number)>
     ├╴<Token '%' at 75:76 (Comment)>
     ├╴<Context Nonsense.comment at 76-89 (1 child)>
     │  ╰╴<Token ' comment that' at 76:89 (Comment)>
     ├╴<Token 'ends' at 90:94 (Text)>
     ├╴<Token 'on' at 95:97 (Text)>
     ├╴<Token 'a' at 98:99 (Text)>
     ├╴<Token 'newline' at 100:107 (Text)>
     ╰╴<Token '.' at 107:108 (Delimiter)>


Token
-----

We see that the Token instances represent the matched text. Every Token has
the matched text in the ``text`` attribute, the position where it is in the
source text in the ``pos`` attribute, and the action it was given in the
``action`` attribute.  Besides that, Tokens also have an ``end`` attribute,
which is actually a property and basically returns ``self.pos +
len(self.text)``.

Although a Token is not a string, you can test for equality::

    if token == "bla":
        # do something

Also, you can check if some text is in some Context::

    if 'and' in tree:
        # do some_thing if 'and' is in the root context.


Context
-------

A Context is basically a Python list, and it has the lexicon that created it
in the ``lexicon`` attribute. The root of the tree is called the root
context, it carries the root lexicon. You can access its
child contexts and tokens with item or slice notation::

    >>> print(tree[2])
    <Token 'with' at 11:15 (Text)>

Besides that, Context has a ``pos`` and ``end`` attribute, which
refer to the ``pos`` value of the first Token in the context, and the ``end``
value of the last Token in the context (or a sub-context).

Just like is is possible with Token to compare with a string, a Context can be
compared to a Lexicon object. So it is possible to write::

    >>> tree[8] == Nonsense.string
    True
    >>> Nonsense.comment in tree
    True

A Context is never empty: if the parser switches to a new lexicon, but the
lexicon does not generate any Token, the empty Context is discarded. Only the
root context can be empty.


Traversing the tree structure
-----------------------------

Both Token and Context have a ``parent`` atribute that points to its parent
Context. Only for the root context, ``parent`` is ``None``.

:py:class:`Token <parce.tree.Token>` and :py:class:`Context
<parce.tree.Context>` both inherit from :py:class:`Node <parce.tree.Node>`,
which defines a lot of useful methods to traverse the tree structure.


Members shared by Token and Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These are the attributes Token and Context both provide:

:attr:`parent`
    The parent Context, the root context has ``parent`` ``None``.
:attr:`pos`, :attr:`end`
    The starting resp. ending position of this node in the source text.
:attr:`is_token`
    False for Context, True for Token
:attr:`is_context`
    True for Context, False for Token

These are the methods Token and Context both provide:

.. currentmodule:: parce.tree

.. autoclass:: Node
   :noindex:
   :members:


Members of Token
^^^^^^^^^^^^^^^^

Token has the following additional methods and attributes for node traversal:

.. py:class:: Token
   :noindex:

   .. py:attribute:: action
      :noindex:

      The action the Token was instantiated with

   .. py:attribute:: group
      :noindex:

      The group the token belongs to. Normally None, but in some cases this
      attribute is a tuple of Tokens that form a group together. See below.

   .. automethod:: Token.equals
      :noindex:

   .. automethod:: Token.state_matches
      :noindex:

   .. automethod:: Token.forward_including
      :noindex:

   .. automethod:: Token.forward_until_including
      :noindex:

   .. automethod:: Token.backward_including
      :noindex:

   .. automethod:: Token.common_ancestor_with_trail
      :noindex:


Members of Context
^^^^^^^^^^^^^^^^^^

Context builds on the Python ``list()`` builtin, so it has all the methods
``list()`` provides. And it has the following addtional methods and attributes
for node traversal:

.. py:class:: Context
   :noindex:

   .. py:attribute:: lexicon
      :noindex:

      The lexicon that created this Context

   .. automethod:: Context.first_token
      :noindex:

   .. automethod:: Context.last_token
      :noindex:

   .. automethod:: Context.find_token
      :noindex:

   .. automethod:: Context.find_token_left
      :noindex:

   .. automethod:: Context.find_token_after
      :noindex:

   .. automethod:: Context.find_token_before
      :noindex:

   .. automethod:: Context.tokens
      :noindex:

   .. automethod:: Context.tokens_bw
      :noindex:

Often, when dealing with the tree structure, you want to know whether we have
a Token or a Context. Instead of calling::

    if isinstance(node, parce.tree.Token):
        do_something()

two readonly attributes are available, `is_token` and `is_context`. The first
is only and always true in Token instances, the other in Context instances::

    if node.is_token:
        do_something()


Grouped Tokens
--------------

When a dynamic action is used in a rule, and it generates more than one Token
from the same regular expression match, these Tokens form a group, each having
their index in the group in the ``group`` attribute. That attribute is
read-only and ``None`` for normal Tokens. Grouped tokens are always adjacent
and in the same Context.

Normally you don't have to do much with this information, but *parce* needs
to know this, because if you edit a text, *parce* can't start reparsing
at a token that is not the first of its group, because the whole group was
created from one regular expression match.

But just in case, if you want to be sure you have the first member of a Token
group::

    if token.group:
        # group is not None or 0
        for token in token.left_siblings():
            if not token.group:
                break


Querying the tree structure
---------------------------

Besides the various `find` methods, there is another powerful way to search
for Tokens and Contexts in the tree, the ``query`` property of every Token or
Context.

The ``query`` property of both Token and Context returns a ``Query`` object
which is a generator initially yielding just that Token or Context::

    >>> for node in tree.query:
    ...     print(node)
    ...
    <Context Nonsense.root at 1-108 (19 children)>

But the Query object has powerful methods that modify the stream of nodes
yielded by the generator. All these methods return a new Query object, so
queries can be chained in an XPath-like fashion. For example::


    >>> for node in tree.query[:3]:
    ...     print (node)
    ...
    <Token 'Some' at 1:5 (Text)>
    <Token 'text' at 6:10 (Text)>
    <Token 'with' at 11:15 (Text)>

The ``[:3]`` operator picks the first three nodes of every node yielded
by the previous generator. You can use ``[:]`` or ``.children`` to get
all children of every node::

    >>> for node in tree.query.children:
    ...     print(node)
    ...
    <Token 'Some' at 1:5 (Text)>
    <Token 'text' at 6:10 (Text)>
    <Token 'with' at 11:15 (Text)>
    <Token '3' at 16:17 (Literal.Number)>
    <Token 'numbers' at 18:25 (Text)>
    <Token 'and' at 26:29 (Text)>
    <Token '1' at 30:31 (Literal.Number)>
    <Token '"' at 32:33 (Literal.String)>
    <Context Nonsense.string at 33-67 (2 children)>
    <Token ',' at 67:68 (Delimiter)>
    <Token 'and' at 69:72 (Text)>
    <Token '1' at 73:74 (Literal.Number)>
    <Token '%' at 75:76 (Comment)>
    <Context Nonsense.comment at 76-89 (1 child)>
    <Token 'ends' at 90:94 (Text)>
    <Token 'on' at 95:97 (Text)>
    <Token 'a' at 98:99 (Text)>
    <Token 'newline' at 100:107 (Text)>
    <Token '.' at 107:108 (Delimiter)>

The main use of ``query`` is of course to narrow down a list of nodes to the
ones we're really looking for. You can use a query to find Tokens with a
certain action::

    >>> for node in tree.query.children.action(Comment):
    ...     print(node)
    ...
    <Token '%' at 75:76 (Comment)>

Instead of ``children``, we can use ``all``, which descends in all child
contexts::

    >>> for node in tree.query.all.action(Comment):
    ...     print(node)
    ...
    <Token '%' at 75:76 (Comment)>
    <Token ' comment that' at 76:89 (Comment)>

Now it also reaches the token that resides in the Nonsense.comment Context.
Let's find tokens with certain text::

    >>> for node in tree.query.all.containing('o'):
    ...     print(node)
    ...
    <Token 'Some' at 1:5 (Text)>
    <Token 'string inside\nover multiple '... at 33:66 (Literal.String)>
    <Token ' comment that' at 76:89 (Comment)>
    <Token 'on' at 95:97 (Text)>

Besides ``containing()``, we also have ``startingwith()``, ``endingwith()``
and ``matching()`` which can find tokens matching a regular expression.

The real power of ``query`` is to combine things. The following query selects
tokens with action Number, but only if they are immediately followed by a Text
token::

    >>> for node in tree.query.all.action(Text).left.action(Number):
    ...     print(node)
    ...
    <Token '3' at 16:17 (Literal.Number)>

.. currentmodule:: parce.query

Here is a list of all the queries that navigate:

:attr:`~Query.all`,
:attr:`~Query.children`,
:attr:`~Query.parent`,
:attr:`~Query.ancestors`,
:attr:`~Query.next`,
:attr:`~Query.previous`,
:attr:`~Query.forward`,
:attr:`~Query.backward`,
:attr:`~Query.right`,
:attr:`~Query.left`,
:attr:`~Query.right_siblings`,
:attr:`~Query.left_siblings`,
:attr:`[n] <Query.__getitem__>`,
:attr:`[n:m] <Query.__getitem__>`,
:attr:`~Query.first`,
:attr:`~Query.last`, and
:meth:`~Query.map`,

And this is a list of the queries that narrow down the result set:

:attr:`~Query.tokens`,
:attr:`~Query.contexts`,
:attr:`~Query.uniq`,
:attr:`~Query.remove_ancestors`,
:attr:`~Query.remove_descendants`,
:meth:`~Query.slice` and
:meth:`~Query.filter`.

The special :attr:`~Query.is_not` operator inverts the meaning of the
next query, e.g.::

    n.query.all.is_not.startingwith("text")

The following query methods can be inverted by prepending `is_not`:

:meth:`~Query.len`,
:meth:`~Query.in_range`,
:meth:`(lexicon) <Query.__call__>`,
:meth:`(lexicon, lexicon2, ...) <Query.__call__>`,
:meth:`("text") <Query.__call__>`,
:meth:`("text", "text2", ...) <Query.__call__>`,
:meth:`~Query.startingwith`,
:meth:`~Query.endingwith`,
:meth:`~Query.containing`,
:meth:`~Query.matching`,
:meth:`~Query.action` and
:meth:`~Query.in_action`.

For convenience, there are some "endpoint" methods for a query that make
it easier in some cases to process the results:

:meth:`~Query.dump`
    for debugging, dumps all resulting nodes to standard output
:meth:`~Query.list`
    aggregates the result set in a list.
:meth:`~Query.count`
    returns the number of nodes in the result set.
:meth:`~Query.pick`
    picks the first result, or returns the default if the result set was
    empty.
:meth:`~Query.pick_last`
    exhausts the query generator and returns the last result, or the
    default if there are no results.
:meth:`~Query.range`
    returns the text range as a tuple (pos, end) the result set
    encompasses

Finally, there is one method that actually changes the tree:

:meth:`~Query.delete`
    deletes all selected nodes from their parents. If a context would
    become empty, it is deleted as well, instead of its children.

Additional information can be found in the :mod:`~parce.query` module's
documentation.

