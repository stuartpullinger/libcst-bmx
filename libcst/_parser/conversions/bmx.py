from contextlib import contextmanager
from dataclasses import dataclass
import keyword
import typing

from libcst._nodes.expression import Dict, DictElement, Element, List, Name, SimpleString, Tuple

from libcst._add_slots import add_slots
from libcst._nodes.base import CSTNode, CSTVisitorT
from libcst._nodes.expression import (
    Attribute,
    LeftParen,
    RightParen,
    #List,
    BaseElement,
    _BaseParenthesizedNode,
    BaseParenthesizableWhitespace,
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
from libcst._parser.parso.python.py_token import TokenType
from libcst._parser.production_decorator import with_production
from libcst._parser.types.config import ParserConfig
from libcst._parser.types.partials import (
    WithLeadingWhitespace,
    SimpleWhitespace,
)
from libcst._parser.whitespace_parser import parse_parenthesizable_whitespace

# bmx: bmx_selfclosing | bmx_openclose | bmx_fragment
@with_production("bmx", "bmx_fragment | bmx_tag (bmx_selfclosing | bmx_openclose)")
def convert_bmx(config: ParserConfig, children: typing.Sequence[typing.Any]) -> typing.Any:
    if len(children) == 1:
        return children[0]
    tag, rest = children
    l_angle, child, *attributes = tag
    if len(rest) == 2:
        return WithLeadingWhitespace(
                Tuple((
                    Element(child), 
                    Element(Dict(tuple(attributes))), 
                    Element(Name("None")))), 
                l_angle.whitespace_before)
    close_opentag, *contents, open_closetag, close_name, close_closetag = rest
    return WithLeadingWhitespace(
            Tuple((
                Element(child), 
                Element(Dict(tuple(attributes))), 
                Element(List([Element(val.value) for val in contents])))), 
            l_angle.whitespace_before)


# bmx_openclose: '<' dotted_name [bmx_attribute]* '>' atom* '</' dotted_name '>'
@with_production( "bmx_openclose", "'>' atom* '</' dotted_name '>'")
def convert_bmx_openclose(
    config: ParserConfig, children: typing.Sequence[typing.Any]
) -> typing.Any:
    return children


# bmx_selfclosing: '<' dotted_name [bmx_attribute]* '/>'
@with_production( "bmx_selfclosing", "'/>'")
def convert_bmx_selfclosing(
    config: ParserConfig, children: typing.Sequence[typing.Any]
) -> typing.Any:
    return children

# bmx_tag: '<' dotted_name bmx_attribute*
@with_production("bmx_tag", "'<' dotted_name bmx_attribute*")
def convert_bmx_tag(config: ParserConfig, children: typing.Sequence[typing.Any]) -> typing.Any:
    return children

# bmx_attribute: (NAME | atom_string) ['=' atom]
# Allow attribute keys to be python keywords eg. 'class', etc
# TODO: maybe just list them as below may produce different output on different versions of python
keyword_attributes = ' | '.join(f"'{kw}'" for kw in keyword.kwlist if kw.islower())
@with_production( "bmx_attribute", f"({keyword_attributes} | NAME | atom_string) ['=' atom]")
def convert_bmx_attribute(
    config: ParserConfig, children: typing.Sequence[typing.Any]
) -> typing.Any:
    key, eq, value = children
    if key.type.name == "NAME":
        key_node = SimpleString(repr(key.string))
    else:
        key_node = key
    # TODO: if eq and value are missing (how is this represented?), assign True token to value
    # OR: create a new node type for single name attributes (what are these called?), then do the conversion in the codemod
    element = DictElement(
        key_node,
        value.value,
        whitespace_before_colon=parse_parenthesizable_whitespace(
            config, eq.whitespace_before
        ),
        whitespace_after_colon=parse_parenthesizable_whitespace(
            config, eq.whitespace_after
        ),
    )
    return element


@add_slots
@dataclass(frozen=True)
class StartFragment(CSTNode):
    """
    A '<>' node
    """

    #: Any space that appears directly after this left square bracket.
    whitespace_after: BaseParenthesizableWhitespace = SimpleWhitespace.field("")

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "StartFragment":
        return StartFragment(
            whitespace_after=visit_required(
                self, "whitespace_after", self.whitespace_after, visitor
            )
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        state.add_token("<>")
        self.whitespace_after._codegen(state)


@add_slots
@dataclass(frozen=True)
class EndFragment(CSTNode):
    """
    A '</>' node
    """

    #: Any space that appears directly after this left square bracket.
    whitespace_after: BaseParenthesizableWhitespace = SimpleWhitespace.field("")

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "EndFragment":
        return EndFragment(
            whitespace_after=visit_required(
                self, "whitespace_after", self.whitespace_after, visitor
            )
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        state.add_token("</>")
        self.whitespace_after._codegen(state)


@add_slots
@dataclass(frozen=True)
class BmxFragment(_BaseParenthesizedNode, CSTNode):
    """
    A BMX fragment node
    """
    contents: typing.Sequence[BaseElement]
    
    start_fragment: StartFragment = StartFragment.field()
    end_fragment: EndFragment = EndFragment.field()

    lpar: typing.Sequence[LeftParen] = ()
    #: Sequence of parenthesis for precedence dictation.
    rpar: typing.Sequence[RightParen] = ()

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "BmxFragment":
        return BmxFragment(
            lpar=visit_sequence(self, "lpar", self.lpar, visitor),
            start_fragment=visit_required(self, "start_fragment", self.start_fragment, visitor),
            contents=visit_sequence(self, "contents", self.contents, visitor),
            end_fragment=visit_required(self, "end_fragment", self.end_fragment, visitor),
            rpar=visit_sequence(self, "rpar", self.rpar, visitor),
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        with self._parenthesize(state):
            elements = self.contents
            self.start_fragment._codegen(state)
            for idx, el in enumerate(elements):
                el._codegen(
                    state,
                    default_comma=(idx < len(elements) - 1),
                    default_comma_whitespace=True,
                )
            self.end_fragment._codegen(state)


# bmx_fragment: '<>' [atom]* '</>'
@with_production("bmx_fragment", "'<>' atom* '</>'")
def convert_bmx_fragment(config: ParserConfig, children: typing.Sequence[typing.Any]) -> typing.Any:
    opener, *contents, closer = children
    return WithLeadingWhitespace(
            BmxFragment(
                start_fragment=StartFragment(opener),
                end_fragment=EndFragment(closer),
                contents=[Element(val.value) for val in contents]
            ),
            opener.whitespace_before)


