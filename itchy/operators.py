"""Scratch operators builders."""
from __future__ import annotations
from itchy.game import (
    Arithmetic, Comparison, Logic, Not, Condition, NativeCondition, NativeReporter, Number,
    NumberExpression, RandomNumber, Value, predicate, reporter,
)


def random_number(low: Number, high: Number) -> NumberExpression:
    return RandomNumber(low, high)


def join(left: Value, right: Value, *parts: Value) -> NativeReporter:
    """Concatenate values using left-nested Scratch join blocks."""
    result = reporter("operator_join", inputs={"STRING1": left, "STRING2": right})
    for part in parts:
        result = reporter("operator_join", inputs={"STRING1": result, "STRING2": part})
    return result


def letter(index: Value, text: Value) -> NativeReporter:
    return reporter("operator_letter_of", inputs={"LETTER": index, "STRING": text})


def length(text: Value) -> NativeReporter:
    return reporter("operator_length", inputs={"STRING": text})


def contains(text: Value, part: Value) -> NativeCondition:
    return predicate("operator_contains", inputs={"STRING1": text, "STRING2": part})


def modulo(left: Number, right: Number) -> NativeReporter:
    return reporter("operator_mod", inputs={"NUM1": left, "NUM2": right})


def round_number(value: Number) -> NativeReporter:
    return reporter("operator_round", inputs={"NUM": value})


def math_op(operation: str, value: Number) -> NativeReporter:
    return reporter("operator_mathop", inputs={"NUM": value}, fields={"OPERATOR": operation})


def abs_number(value: Number) -> NativeReporter:
    return math_op('abs', value)


def floor(value: Number) -> NativeReporter:
    return math_op('floor', value)


def ceil(value: Number) -> NativeReporter:
    return math_op('ceiling', value)


def sqrt(value: Number) -> NativeReporter:
    return math_op('sqrt', value)


def sin(value: Number) -> NativeReporter:
    """Scratch sin; angles are in degrees."""
    return math_op('sin', value)


def cos(value: Number) -> NativeReporter:
    """Scratch cos; angles are in degrees."""
    return math_op('cos', value)


def tan(value: Number) -> NativeReporter:
    """Scratch tan; angles are in degrees."""
    return math_op('tan', value)


def asin(value: Number) -> NativeReporter:
    """Scratch asin; angles are in degrees."""
    return math_op('asin', value)


def acos(value: Number) -> NativeReporter:
    """Scratch acos; angles are in degrees."""
    return math_op('acos', value)


def atan(value: Number) -> NativeReporter:
    """Scratch atan; angles are in degrees."""
    return math_op('atan', value)


def ln(value: Number) -> NativeReporter:
    return math_op('ln', value)


def log10(value: Number) -> NativeReporter:
    return math_op('log', value)


def exp(value: Number) -> NativeReporter:
    return math_op('e ^', value)


def pow10(value: Number) -> NativeReporter:
    return math_op('10 ^', value)


def math_function(function: str, value: Number) -> NativeReporter:
    return reporter("operator_mathop", inputs={"NUM": value}, fields={"OPERATOR": function})


def add(left: Number, right: Number) -> NumberExpression:
    return Arithmetic("add", left, right)


def subtract(left: Number, right: Number) -> NumberExpression:
    return Arithmetic("subtract", left, right)


def multiply(left: Number, right: Number) -> NumberExpression:
    return Arithmetic("multiply", left, right)


def divide(left: Number, right: Number) -> NumberExpression:
    return Arithmetic("divide", left, right)


def less_than(left: Value, right: Value) -> Condition:
    return Comparison("lt", left, right)


def greater_than(left: Value, right: Value) -> Condition:
    return Comparison("gt", left, right)


def equals(left: Value, right: Value) -> Condition:
    return Comparison("equals", left, right)


def and_(left: Condition, right: Condition) -> Condition:
    return Logic("and", left, right)


def or_(left: Condition, right: Condition) -> Condition:
    return Logic("or", left, right)


def not_(value: Condition) -> Condition:
    return Not(value)
