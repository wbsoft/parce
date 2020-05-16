# Calculator parce example

from parce import Language, lexicon, default_target, skip
from parce.action import Number, Operator, Delimiter
from parce.transform import Transform

skip_whitespace = (r'\s+', skip)


class Calculator(Language):
    @lexicon
    def root(cls):
        yield r'\d+', Number
        yield r'\-', Operator, cls.subtract
        yield r'\+', Operator, cls.add
        yield r'\*', Operator, cls.multiply
        yield r'/', Operator, cls.divide
        yield r'\(', Delimiter, cls.parens

    @lexicon
    def parens(cls):
        yield r'\)', Delimiter, -1
        yield from cls.root

    @lexicon
    def subtract(cls):
        yield r'\d+', Number
        yield r'\*', Operator, cls.multiply
        yield r'/', Operator, cls.divide
        yield r'\(', Delimiter, cls.parens
        yield skip_whitespace
        yield default_target, -1

    @lexicon
    def add(cls):
        yield from cls.subtract

    @lexicon
    def multiply(cls):
        yield r'\d+', Number
        yield r'\(', Delimiter, cls.parens
        yield skip_whitespace
        yield default_target, -1

    @lexicon
    def divide(cls):
        yield from cls.multiply


class CalculatorTransform(Transform):
    def root(self, items):
        result = 0
        for i in items:
            if i.is_token:
                if i.action is Number:
                    result = int(i.text)
            elif i.name == "add":
                result += i.obj
            elif i.name == "subtract":
                result -= i.obj
            elif i.name == "multiply":
                result *= i.obj
            elif i.name == "divide":
                result /= i.obj
            else:   # i.name == "parens":
                result = i.obj
        return result

    parens = add = subtract = multiply = divide = root

