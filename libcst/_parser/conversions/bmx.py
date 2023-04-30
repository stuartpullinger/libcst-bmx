from contextlib import contextmanager
from dataclasses import dataclass
import keyword
import typing

from libcst._nodes.expression import Dict, DictElement, Element, List, Name, SimpleString, Tuple

from libcst._add_slots import add_slots
from libcst._nodes.base import CSTNode, CSTVisitorT
from libcst._nodes.op import (
        LessThan,
        GreaterThan,
)
from libcst._nodes.expression import (
    BaseExpression,
    Attribute,
    LeftParen,
    RightParen,
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

@add_slots
@dataclass(frozen=True)
class BmxOpenClose(_BaseParenthesizedNode, CSTNode):
    """
    A BMX open-close node
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

@add_slots
@dataclass(frozen=True)
class EndSelfClosing(CSTNode):
    """
    A '/>' node
    """

    #: Any space that appears directly after this.
    whitespace_after: BaseParenthesizableWhitespace = SimpleWhitespace.field("")

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "EndSelfClosing":
        return EndSelfClosing(
            whitespace_after=visit_required(
                self, "whitespace_after", self.whitespace_after, visitor
            )
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        state.add_token("/>")
        self.whitespace_after._codegen(state)


@add_slots
@dataclass(frozen=True)
class BmxSelfClosing(_BaseParenthesizedNode, CSTNode):
    """
    A BMX self-closing node
    """
    ref: typing.Any
    attributes: typing.Sequence[DictElement]
    
    opener: LessThan = LessThan.field()
    closer: EndSelfClosing = EndSelfClosing.field()

    lpar: typing.Sequence[LeftParen] = ()
    #: Sequence of parenthesis for precedence dictation.
    rpar: typing.Sequence[RightParen] = ()

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "BmxSelfClosing":
        return BmxSelfClosing(
            lpar=visit_sequence(self, "lpar", self.lpar, visitor),
            opener=visit_required(self, "opener", self.opener, visitor),
            ref=visit_sequence(self, "ref", self.ref, visitor),
            attributes=visit_sequence(self, "attributes", self.attributes, visitor),
            closer=visit_required(self, "closer", self.closer, visitor),
            rpar=visit_sequence(self, "rpar", self.rpar, visitor),
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        with self._parenthesize(state):
            self.opener._codegen(state)
            attributes = self.attributes
            for idx, el in enumerate(attributes):
                el._codegen(
                    state,
                    default_comma=(idx < len(attributes) - 1),
                    default_comma_whitespace=True,
                )
            self.closer._codegen(state)

# bmx: bmx_selfclosing | bmx_openclose | bmx_fragment
@with_production("bmx", "bmx_fragment | bmx_tag (bmx_selfclosing | bmx_openclose)")
def convert_bmx(config: ParserConfig, children: typing.Sequence[typing.Any]) -> typing.Any:
    if len(children) == 1:      # bmx_fragment
        return children[0]
    tag, rest = children
    l_angle, ref, *attributes = tag
    if len(rest) > 1:  # bmx_openclose
        close_opentag, *contents, open_closetag, close_name, close_closetag = rest
        return WithLeadingWhitespace(
                BmxOpenClose(
                    contents=contents,
                    # TODO: args here
                    )
                l_angle.whitespace_before)
    # bmx_selfclosing
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

@add_slots
@dataclass(frozen=True)
class BmxAttribute(CSTNode):
    """
    A BMX attribute node
    """
    key: SimpleString
    value: typing.Optional[BaseExpression]

    #: Whitespace after the key, but before the colon in ``key : value``.
    whitespace_before_equals: BaseParenthesizableWhitespace = SimpleWhitespace.field("")
    #: Whitespace after the colon, but before the value in ``key : value``.
    whitespace_after_equals: BaseParenthesizableWhitespace = SimpleWhitespace.field("")

    def _visit_and_replace_children(self, visitor: CSTVisitorT) -> "BmxAttribute":  
        value_keyword = {}
        if self.value is not None:
            value_keyword = dict(
                whitespace_before_equals=visit_required(
                    self, "whitespace_before_equals", self.whitespace_before_equals, visitor
                ),
                whitespace_after_equals=visit_required(
                    self, "whitespace_after_equals", self.whitespace_after_equals, visitor
                ),
                value=visit_required(self, "value", self.value, visitor),
            )

        return BmxAttribute(
            key=visit_required(self, "key", self.key, visitor),
            **value_keyword
        )

    def _codegen_impl(self, state: CodegenState) -> None:
        self.key._codegen(state)
        if self.value is not None:
            state.add_token('=')
            self.key._codegen(state)

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
    element = BmxAttribute(          # TODO: need a new node type here as this is changing the semantics of the what was written
        key_node,
        value.value,
        whitespace_before_equals=parse_parenthesizable_whitespace(
            config, eq.whitespace_before
        ),
        whitespace_after_equals=parse_parenthesizable_whitespace(
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


