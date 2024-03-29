# Copyright (c) Meta Platforms, Inc. and affiliates.
#
# This source code is licensed under the MIT license found in the
# LICENSE file in the root directory of this source tree.

from dataclasses import dataclass

from libcst._add_slots import add_slots
from libcst._nodes.op import BaseCompOp, _BaseOneTokenOp
from libcst._nodes.whitespace import BaseParenthesizableWhitespace, SimpleWhitespace


@add_slots
@dataclass(frozen=True)
class LessThanSlash(BaseCompOp, _BaseOneTokenOp):
    """
    A '</' for BMX.
    """

    #: Any space that appears directly before this operator.
    whitespace_before: BaseParenthesizableWhitespace = SimpleWhitespace.field(" ")

    #: Any space that appears directly after this operator.
    whitespace_after: BaseParenthesizableWhitespace = SimpleWhitespace.field(" ")

    def _get_token(self) -> str:
        return "</"


@add_slots
@dataclass(frozen=True)
class SlashGreaterThan(BaseCompOp, _BaseOneTokenOp):
    """
    A '/>' for BMX.
    """

    #: Any space that appears directly before this operator.
    whitespace_before: BaseParenthesizableWhitespace = SimpleWhitespace.field(" ")

    #: Any space that appears directly after this operator.
    whitespace_after: BaseParenthesizableWhitespace = SimpleWhitespace.field(" ")

    def _get_token(self) -> str:
        return "/>"

