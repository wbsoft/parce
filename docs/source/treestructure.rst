Accessing the Tree Structure
============================

When you have parsed text, the result is a tree structure of Tokens,
nested in Contexts, which may be nested in other Contexts.

Let's look at the generated token tree of the simple example of the Getting
started section::

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
     ├╴<Context Nonsense.comment at 76-89 (1 children)>
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

Traversing the tree structure
------------------------------------

Both Token and Context have a ``parent`` atribute that points to its parent
Context. Only for the root context, ``parent`` is ``None``.

:py:class:`Token <parce.tree.Token>` and :py:class:`Context
<parce.tree.Context>` both inherit from :py:class:`NodeMixin
<parce.tree.NodeMixin>`, which defines a lot of useful methods to traverse
tree structure.

Members shared by Token and Context
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

These are the attributes Token and Context both provide:

    ``parent``
        The parent Context, the root context has ``parent`` ``None``.
    ``pos``, ``end``
        The starting resp. ending position of this node in the source text.
    ``is_token``
        False for Context, True for Token
    ``is_context``
        True for Context, False for Token

These are the methods Token and Context both provide:

    ``dump()``
        Display a graphical representation of the node
    ``right_sibling()``, ``left_sibling()``
        Return the left or right sibling, respectively (``None`` if not available)
    ``right_siblings()``
        Yield the right siblings in forward order
    ``left_siblings()``
        Yield the left siblings in backward order
    ``next_token()``, ``previous_token()``
        Return the Token closest to the right resp. to the left of this node.
        The returned Token can be in a parent or child Context.
    ``forward()``
        Yield Tokens in document order starting with the Token that
        ``next_token()`` returns.
    ``backward()``
        Yield Tokens in backward order starting with the Token that
        ``previous_token()`` returns.
    ``ancestors(upto=None)``
        Yield the parent of the token, and then the parent's parent, and so on
        till the root node is reached. If upto is given and it is one of the
        ancestors, stop after yielding that ancestor. Otherwise iteration stops
        at the root node.
    ``ancestors_with_index(upto=None)``
        Yield two-tuples (node, index) from ``ancestors()``, adding the index
        of the node in its parent.
    ``common_ancestor(other)``
        Return the nearest common ancestor with the other Context or Token.
    ``is_first()``, ``is_last()``
        Return True if the node is the first resp. the last in its Context.
    ``is_root()``
        Return True if the node is the root node, i.e. its ``parent`` is ``None``.
    ``query``
        Powerful property to find nodes in the tree structure. See below.

Members of Token
^^^^^^^^^^^^^^^^

Token has the following additional methods and attributes for node traversal:

    ``action``
        The action the Token was instantiated with
    ``group``
        The group the token belongs to. Normally None, but in some cases this
        attribute is a tuple of Tokens that form a group together. See below.
    ``equals(other)``
        True if the other Token has the same ``pos``, ``text`` and ``action``
        attributes and the same context ancestry (see ``state_matches()``).
    ``state_matches(other)``
        True if the other Token has the same lexicons in all the ancestors.
    ``backward_including(upto=None)``
        Yield all tokens from here in backward direction, including self
    ``forward_including(upto=None)``
        Yield all tokens from here in forward direction, including self.
    ``target()``
        Return the Context that was started from the rule that this token
        originated from. Normally this is the right sibling, but it can also
        be the right sibling of an ancestor.
    ``common_ancestor_with_trail(other)``
        Return a three-tuple (context, trail_self, trail_other).

        The ``context`` is the common ancestor such as returned by
        ``common_ancestor()``, if any. ``trail_self`` is a tuple of indices
        from the common ancestor upto self, and ``trail_other`` is a tuple of
        indices from the same ancestor upto the other Token.

        If there is no common ancestor, all three are ``None``. But normally,
        all nodes share the root context, so that will normally be the upmost
        common ancestor.

Members of Context
^^^^^^^^^^^^^^^^^^

Context builds on the Python ``list()`` builtin, so it has all the methods
``list()`` provides. And it has the following addtional methods and attributes
for node traversal:

    ``lexicon``
        The lexicon that created this Context
    ``first_token()``, ``last_token()``
        Return our first, resp last token. This token can be in a child context.
    ``find_token(pos)``
        Return the token at or right of position ``pos``. Always returns a token
        unless the root context is completely empty.
    ``find_token_left(pos)``
        Return the token at or left of position ``pos``. Always returns a token
        unless the root context is completely empty.
    ``find_token_after(pos)``
        Return the first token that is completely right from ``pos``. If there
        is no token right from ``pos``, ``None`` is returned.
    ``find_token_before(pos)``
        Return the last token completely left from pos. Returns ``None`` if
        there is no token left from ``pos``.
    ``source()``
        Return the first token, if any, when going to the left from this
        context. The returned token is the one that created us, that this
        context the ``target()`` is for. If the token is member of a group (see
        below), the first group member is returned.
    ``tokens()``
        Yield all tokens from this Context and its child contexts in document
        order.
    ``tokens_bw()``
        Yield all tokens from this Context and its child contexts in backward
        order.
    ``tokens_range(start, end=None)``
        Yield all tokens that completely fill this text range. This makes the
        most sense if used from the root Context. Note that the first and last
        tokens may overlap with the start and and positions. If end is left to
        None, all tokens from start are yielded.


Token, Context and NodeMixin have some more methods, but those have to do with
tree structure modification while (re)parsing text. See the :doc:`tree module's
documentation <tree>` if you are interested in those.

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
the tuple of all group members in the ``group`` attribute. That attribute is
read-only and ``None`` for normal Tokens. Grouped tokens are always adjacent
and in the same Context.

Normally you don't have to do much with this information, but ``parce`` needs
to know this, because if you edit a text, ``parce`` can't start reparsing
at a token that is not the first of its group, because the whole group was
created from one regular expression match.

But just in case, if you want to be sure you have the first member of a Token
group::

    if token.group:
        token = token.group[0]


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

But the Query object has poweful methods that modify the stream of nodes
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
    <Context Nonsense.comment at 76-89 (1 children)>
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

Here is an overview of all the queries that navigate:

    ``all``
        yield all descendant nodes, depth-first, in order. First it yields the
        context, then its children.
    ``children``
        yield all the direct children of the current nodes
    ``parent``
        yield the parent of all current nodes. This can yield double
        occurrences of nodes in the list. (Use ``uniq`` to fix that.)
    ``next``, ``previous``
        yield the next or previous Token from the current node, if any
    ``right``, ``left``
        yield the right or left sibling of every current node, if any
    ``right_siblings``
        yield the right siblings of every node in the current node list. This
        can lead to long result sets with many occurrences of the same nodes.
    ``left_siblings``
        yield the left siblings of every node in the current node list, in
        backward order. Only use ``right_siblings`` and ``left_siblings`` when
        you want to find one node in the result set.
    ``[n]``
        yield the nth child (if available) of each Context node (supports
        negative indices)
    ``[slice]``
        yield from the specified slice of each Context node
    ``first``, ``last``
        yield the first resp. the last child of every Context node. Same as
        ``[0]`` or ``[-1]``.
    ``target``
        yield the target context for a token, if any. See
        :py:meth:`Token.target() <parce.tree.Token.target>`.
    ``source``
        yield the source token for a context, if any. See
        :py:meth:`Context.source() <parce.tree.Context.source>`.

And this is an overview of the queries that narrow down the result set:

    ``tokens``
        select only the tokens
    ``contexts``
        select only the contexts
    ``uniq``
        Removes double occurrences of Tokens or Contexts, which can happen
        e.g. when selecting the parent of all nodes
    ``remove_ancestors``
        remove Context nodes from the current node list that have descendants
        in the list.
    ``remove_descendants``
        remove nodes from the current list if any of their ancestors is also
        in the list.
    ``slice(stop)``

    ``slice(start, stop [, step])``
        Slice the full result set, using itertools.islice(). This can help
        narrowing down the result set. For example::

            root.query.all("blaat").slice(1).right_siblings.slice(3) ...

        will continue the query with only the first occurrence of a token
        "blaat", and then look for at most three right siblings. If the
        ``slice(1)`` were not there, all the right siblings would become one large
        result set because you wouldn't know how many tokens "blaat" were
        matched.
    ``remove_ancestors``
        Remove nodes that have descendants in the current node list.
    ``remove_descendants``
        Remove nodes that have ancestors in the current node list.
    ``filter(predicate)``
        select nodes for which the predicate function returns a value that
        evaluates to True
    ``map(function)``
        call function on every node and yield its results, which should be
        nodes as well.
    ``is_not``
        inverts the meaning of the following query, e.g. is_not.startingwith()

    The following query methods are inverted by ``is_not``:

    ``in_range(start=0, end=None)``
        select only the nodes that fully fit in the text range. If preceded
        by ``is_not``, selects the nodes that are outside the specified text
        range.
    ``(lexicon), (lexicon, lexicon2, ...)``
        select the Contexts with that lexicon (or one of the lexicons)
    ``("text"), ("text", "text2", ...)``
        select the Tokens with exact that text (or one of the texts)
    ``startingwith("text")``
        select the Tokens that start with the specified text
    ``endingwith("text")``
        select the Tokens that end with the specified text
    ``containing("text")``
        select the Tokens that contain specified text
    ``matching("regex"), matching(regex)``
        select the Tokens that match the specified regular epression
        (using ``re.search``, the expression can match anywhere unless you use
        ``^`` or ``$`` characters).
    ``action(*actions)``
        select the Tokens that have one of the specified actions
    ``in_action(*actions)``
        select tokens if their action belongs in the realm of one of the
        specified StandardActions

For convenience, there are four "endpoint" methods for a query that make
it easier in some cases to process the results:

    ``dump()``
        for debugging, dumps all resulting nodes to standard output
    ``list()``
        aggregates the result set in a list.
    ``count()``
        just returns the number of nodes in the result set.
    ``pick(default=None)``
        picks the first result, or returns the default if the result set was
        empty.

Additional information can be found in the :doc:`query module's
documentation <query>`.

