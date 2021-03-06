"""
Defines a visitor to check the control flow of fuctions, verifying if they always/never return.
"""

import clr.ast as ast
import clr.annotations as an
import clr.types as ts
import clr.errors as er


class FlowChecker(ast.DeepVisitor):
    """
    Ast visitor to check which parts of code always/sometimes return.
    """

    def func_decl(self, node: ast.AstFuncDecl) -> None:
        super().func_decl(node)
        # TODO: Show how rather than just highlighting the whole function
        if (
            node.return_type.type_annot != ts.VOID
            and node.block.return_annot != an.ReturnAnnot.ALWAYS
        ):
            self.errors.add(
                message="non-void function may not return", regions=[node.region]
            )

    def block_stmt(self, node: ast.AstBlockStmt) -> None:
        super().block_stmt(node)
        for decl in node.decls:
            if node.return_annot == an.ReturnAnnot.ALWAYS:
                # Unreachable code
                self.errors.add(
                    message="unreachable code",
                    regions=[decl.region],
                    severity=er.Severity.WARNING,
                )
            elif decl.return_annot == an.ReturnAnnot.SOMETIMES:
                node.return_annot = an.ReturnAnnot.SOMETIMES
            elif decl.return_annot == an.ReturnAnnot.ALWAYS:
                node.return_annot = an.ReturnAnnot.ALWAYS

    def if_stmt(self, node: ast.AstIfStmt) -> None:
        super().if_stmt(node)
        blocks = (
            [node.if_part[1]]
            + [elif_block for _, elif_block in node.elif_parts]
            + ([node.else_part] if node.else_part else [])
        )
        if node.else_part is not None and all(
            block.return_annot == an.ReturnAnnot.ALWAYS for block in blocks
        ):
            node.return_annot = an.ReturnAnnot.ALWAYS
        elif any(block.return_annot == an.ReturnAnnot.SOMETIMES for block in blocks):
            node.return_annot = an.ReturnAnnot.SOMETIMES

    def while_stmt(self, node: ast.AstWhileStmt) -> None:
        super().while_stmt(node)
        if node.block.return_annot != an.ReturnAnnot.NEVER:
            node.return_annot = an.ReturnAnnot.SOMETIMES

    def return_stmt(self, node: ast.AstReturnStmt) -> None:
        super().return_stmt(node)
        node.return_annot = an.ReturnAnnot.ALWAYS
