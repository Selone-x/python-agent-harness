"""A concrete opt-in policy tested through the actual Fixit engine."""

from typing import ClassVar

import libcst as cst
from fixit import Invalid, LintRule, Valid
from fixit.testing import add_lint_rule_tests_to_module


class NoConsoleOutput(LintRule):
    """Example project policy: use an explicit logger instead of direct print."""

    MESSAGE = "Use the agreed logger in this module."
    VALID: ClassVar[list[str | Valid]] = [Valid("logger.info('event')"), Valid("service.print()")]
    INVALID: ClassVar[list[str | Invalid]] = [Invalid("print('event')"), Invalid("print(value)")]

    def visit_Call(self, node: cst.Call) -> None:
        """Check exactly the agreed syntactic form, without guessing aliases."""
        if isinstance(node.func, cst.Name) and node.func.value == "print":
            self.report(node)


add_lint_rule_tests_to_module(globals(), [NoConsoleOutput()])
