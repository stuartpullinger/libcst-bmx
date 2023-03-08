import typing

from libcst._nodes.expression import DictElement, Name
from libcst._parser.production_decorator import with_production
from libcst._parser.types.config import ParserConfig
from libcst._parser.types.partials import (
    WithLeadingWhitespace,
)
from libcst._parser.whitespace_parser import parse_parenthesizable_whitespace

# bmx: bmx_selfclosing | bmx_openclose | bmx_fragment
# TODO

# bmx_selfclosing: '<' dotted_name [bmx_attribute]* '/>'
@with_production( "bmx_selfclosing", "'<' dotted_name [bmx_attribute]* '/' '>'")
def convert_bmx_selfclosing(
    config: ParserConfig, children: typing.Sequence[typing.Any]
) -> typing.Any:
    l_angle, child, *attributes, slash, r_angle = children
    return WithLeadingWhitespace(Name(child.string), child.whitespace_before)

# bmx_openclose: '<' dotted_name [bmx_attribute]* '>' [atom]* '</' dotted_name '>'
# TODO

# bmx_attribute: (NAME | atom_string) ['=' atom]
@with_production( "bmx_attribute", "(NAME | atom_string) ['=' atom]")
def convert_bmx_attribute(
    config: ParserConfig, children: typing.Sequence[typing.Any]
) -> typing.Any:
    key, eq, value = children
    # TODO: if key is a NAME token, convert it to a string token
    # TODO: if eq and value are missing (how is this represented?), assign True token to value
    # OR: create a new node type for single name attributes (what are these called?), then do the conversion in the codemod
    element = DictElement(
        key.value,
        value.value,
        whitespace_before_colon=parse_parenthesizable_whitespace(
            config, eq.whitespace_before
        ),
        whitespace_after_colon=parse_parenthesizable_whitespace(
            config, eq.whitespace_after
        ),
    )
    return WithLeadingWhitespace(element, key.whitespace_before)


# bmx_fragment: '<>' [atom]* '</>'
# TODO


