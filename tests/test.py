# run this to test:
# python3 test.py


import sys
# pick the livelex module from the source tree
sys.path.insert(0, '..')


import livelex

from livelex import (
    Language, lexicon,
    Words, Subgroup, Text,
    default_action,
    default_target,
    skip,
)

class MyLang(Language):
    """A Language represents a set of Lexicons comprising a specific language.

    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.



    """

    @lexicon(re_flags=0)
    def root(cls):
        yield Words(('bla', 'BLA')), 'bla action'
        yield r'ble', 'ble action'
        yield r'\s+', skip      # this text is skipped
        yield r'(bl)(ub)', Subgroup('bl act', 'ub act')
        yield r'blo', 'blo action', cls.blo
        yield r'X', 'x action in root', cls.xxxxs
        yield default_action, "TEXT"

    @lexicon
    def blo(cls):
        yield r'\s+', skip      # this text is skipped
        yield r'1', '1 in blo'
        yield r'4', '4 in blo, end', -1
        yield r'[0-9]', Text(lambda t: "has 3" if '3' in t else 'no 3')
        yield default_action, "unparsed"

    @lexicon
    def xxxxs(cls):
        yield r'X', 'x action in xxxs', 1
        yield r'Y', 'Y action', cls.blo
        yield default_target, -1


s = "bla pythonBLA blub blablo b39la 1 4 ble XXXblo4p"
from livelex import Lexer
l = Lexer(MyLang.root)
tokens = list(l.tokens(s))

if __name__ == "__main__":
    print("livelex version:", livelex.version())

    from pprint import pprint
    pprint(tokens)

    #print("Tree:")
    #from livelex.lex import tree
    #pprint(tree(tokens))

    print("Tree from tree:")
    from livelex.tree import tree
    pprint(tree(tokens))

