from contextlib import contextmanager
from dataclasses import dataclass
import typing

from libcst._nodes.expression import DictElement, Name

from libcst._add_slots import add_slots
from libcst._nodes.base import CSTNode, CSTVisitorT
from libcst._nodes.expression import (
    LeftParen,
    RightParen,
    #List,
    BaseElement,
    _BaseParenthesizedNode,
)
from libcst._nodes.internal import (
    CodegenState,
    visit_required,
    visit_sequence,
)
from libcst._nodes.op import (
    LeftShift,
    RightShift
)

from libcst._nodes.expression import Name
from libcst._parser.production_decorator import with_production
from libcst._parser.types.config import ParserConfig
from libcst._parser.types.partials import (
    WithLeadingWhitespace,
)
from libcst._parser.whitespace_parser import parse_parenthesizable_whitespace

@add_slots
@dataclass(frozen=True)
class BMX(_BaseParenthesizedNode, CSTNode):
    """
    A BMX literal
    """

    #: A sequence containing all the :class:`Element` and :class:`StarredElement` nodes
    #: in the list.
    elements: typing.Sequence[BaseElement]

    lbracket: LeftShift = LeftShift.field()
    #: Brackets surrounding the list.
    rbracket: RightShift = RightShift.field()

    lpar: typing.Sequence[LeftParen] = ()
    #: Sequence of parenthesis for precedence dictation.
    rpar: typing.Sequence[RightParen] = ()

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "BMX":
        return BMX(
            lpar=visit_sequence(self, "lpar", self.lpar, visitor),
            lbracket=visit_required(self, "lbracket", self.lbracket, visitor),
            elements=visit_sequence(self, "elements", self.elements, visitor),
            rbracket=visit_required(self, "rbracket", self.rbracket, visitor),
            rpar=visit_sequence(self, "rpar", self.rpar, visitor),
        )

    @contextmanager
    def _bracketize(self, state: CodegenState) -> typing.Generator[None, None, None]:
        self.lbracket._codegen(state)
        yield
        self.rbracket._codegen(state)

    def _codegen_impl(self, state: CodegenState) -> None:
        with self._parenthesize(state), self._bracketize(state):
            elements = self.elements
            for idx, el in enumerate(elements):
                el._codegen(
                    state,
                    default_comma=(idx < len(elements) - 1),
                    default_comma_whitespace=True,
                )


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


