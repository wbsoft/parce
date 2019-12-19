from livelex import (
    Language, lexicon,
    Words, Subgroup, Text,
    default_action, skip,
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
        yield default_action, "TEXT"

    @lexicon
    def blo(cls):
        yield r'\s+', skip      # this text is skipped
        yield r'1', '1 in blo'
        yield r'4', '4 in blo, end', -1
        yield r'[0-9]', Text(lambda t: "has 3" if '3' in t else 'no 3')
        yield default_action, "unparsed"


from livelex import Lexer
from pprint import pprint
s = "bla pythonBLA blub blablo b39la 1 4 ble"
l = Lexer(MyLang.root)
pprint(list(l.tokens(s)))
