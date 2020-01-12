# run this to test:
# python3 test.py


import sys
import re
# pick the livelex module from the source tree
sys.path.insert(0, '..')


import livelex

from livelex import (
    Language, lexicon,
    words, bygroup, bymatch, bytext,
    default_action,
    default_target,
    skip,
    tomatch,
)

class MyLang(Language):
    """A Language represents a set of Lexicons comprising a specific language.

    A Language is never instantiated. The class itself serves as a namespace
    and can be inherited from.



    """

    @lexicon(re_flags=0)
    def root(cls):
        yield r'"', "string", cls.string
        yield r'\(', "paren", cls.parenthesized
        yield r'\d+', "number"
        yield r'%', "comment", cls.comment
        yield r'[,.!?]', "punctuation"
        yield r'\w+', "word"

    @lexicon
    def string(cls):
        yield r'\\[\\"]', 'string escape'
        yield r'"', "string", -1
        yield default_action, "string"

    @lexicon(re_flags=re.MULTILINE)
    def comment(cls):
        yield r'$', "comment", -1
        yield r'XXX|TODO', "todo"
        yield default_action, "comment"

    @lexicon
    def parenthesized(cls):
        yield r'\)', "paren", -1
        yield from cls.root()


s = r"""
This is (an example) text with 12 numbers
and "a string with \" escaped characters",
and a % comment that TODO lasts until the end
of the line.
"""


if __name__ == "__main__":
    import livelex.pkginfo
    print("livelex version:", livelex.pkginfo.version_string)

    print("Validate:")
    from livelex.validate import validate_language
    validate_language(MyLang)

    print("Tree:")
    from livelex import Document
    Document(MyLang.root, s).get_root(True).dump()

