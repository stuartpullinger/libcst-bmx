import typing

from libcst._nodes.expression import Name
from libcst._parser.production_decorator import with_production
from libcst._parser.types.config import ParserConfig
from libcst._parser.types.partials import (
    WithLeadingWhitespace,
)


@with_production( "bmx_selfclosing", "'<' NAME '/' '>'")
def convert_bmx_selfclosing(
    config: ParserConfig, children: typing.Sequence[typing.Any]
) -> typing.Any:
    l_angle, child, slash, r_angle = children
    return WithLeadingWhitespace(Name(child.string), child.whitespace_before)

