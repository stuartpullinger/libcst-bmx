import argparse
from typing import List

from libcst_bmx.libcst._nodes.base import CSTNode
from libcst_bmx.libcst._nodes.expression import Arg, Call, DictElement, Dict, Name, SimpleString
from libcst_bmx.libcst._parser.conversions.bmx import BmxSelfClosing
from libcst_bmx.libcst.codemod import CodemodContext, VisitorBasedCodemodCommand
from libcst_bmx.libcst.codemod.visitors import AddImportsVisitor

from bmx.htmltags import html5tags


class ConvertConstantCommand(VisitorBasedCodemodCommand):

    DESCRIPTION: str = "Translates BMX syntax to standard Python syntax."

    def __init__(self, context: CodemodContext) -> None:
        super().__init__(context)
        self.context = context

    def leave_BmxSelfClosing(self, original_node: BmxSelfClosing, updated_node: CSTNode) -> Call:
        AddImportsVisitor.add_needed_import(self.context, "bmx_element", "BmxElement")
        ref = original_node.ref
        # Special-case html tags eg. h1
        if isinstance(ref, Name) and ref.value in html5tags:
            ref = SimpleString(ref.value)

        # attribute_elements = [DictElement(attr.key, attr.value or Name('None')) for attr in original_node.attributes]
        # attributes = Dict(attribute_elements)

        element = Call(func=Name('BmxElement'), args=[Arg(value=ref), *(Arg(keyword=attr.key, value=attr.value) for attr in original_node.attributes)])

        return element

