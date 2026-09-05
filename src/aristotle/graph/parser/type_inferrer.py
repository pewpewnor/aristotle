import ast
from typing import Any, Dict

common_callers = {
    "int": "int",
    "float": "float",
    "str": "str",
    "bool": "bool",
    "list": "List",
    "dict": "Dict",
    "set": "Set",
    "tuple": "Tuple",
    "len": "int",
    "range": "range",
    "enumerate": "enumerate",
}


class TypeInferrer:
    def __init__(
        self,
        function_params: Dict[str, str],
        global_vars: Dict[str, str],
        imports: Dict[str, str],
    ):
        self.function_params = function_params
        self.global_vars = global_vars
        self.imports = imports

    def infer_type_from_value(self, node: ast.AST) -> str:
        if isinstance(node, ast.Constant):
            return self._infer_from_constant(node.value)
        if isinstance(node, (ast.List, ast.Dict, ast.Set, ast.Tuple)):
            return self._infer_from_collection(node)
        if isinstance(node, ast.Name):
            return self._infer_from_name(node)
        if isinstance(node, ast.Call):
            return self._infer_from_call(node)
        if isinstance(node, ast.BinOp):
            return self._infer_from_binop(node)
        if isinstance(node, (ast.Compare, ast.BoolOp)):
            return "bool"
        if isinstance(node, ast.UnaryOp):
            return self._infer_from_unaryop(node)
        if isinstance(node, ast.Attribute):
            if isinstance(node.value, ast.Name) and node.value.id in self.imports:
                return f"{self.imports[node.value.id]}.{node.attr}"
            return node.attr
        return "Any"

    def _infer_from_constant(self, value: Any) -> str:
        return type(value).__name__

    def _infer_from_collection(self, node: ast.AST) -> str:
        if isinstance(node, ast.List):
            return (
                f"List[{self.infer_type_from_value(node.elts[0])}]"
                if node.elts
                else "List[Any]"
            )
        if isinstance(node, ast.Dict):
            if node.keys and node.values:
                key_type = (
                    self.infer_type_from_value(node.keys[0]) if node.keys[0] else "Any"
                )
                value_type = self.infer_type_from_value(node.values[0])
                return f"Dict[{key_type}, {value_type}]"
            return "Dict[Any, Any]"
        if isinstance(node, ast.Set):
            return (
                f"Set[{self.infer_type_from_value(node.elts[0])}]"
                if node.elts
                else "Set[Any]"
            )
        if isinstance(node, ast.Tuple):
            return (
                f"Tuple[{', '.join(self.infer_type_from_value(elt) for elt in node.elts)}]"
                if node.elts
                else "Tuple[Any, ...]"
            )
        return "Any"

    def _infer_from_name(self, node: ast.Name) -> str:
        if node.id in self.function_params:
            return self.function_params[node.id]
        if node.id in self.global_vars:
            return self.global_vars[node.id]
        return node.id

    def _infer_from_call(self, node: ast.Call) -> str:
        if isinstance(node.func, ast.Name):
            func_name = node.func.id
            return common_callers.get(func_name, f"{func_name}(...)")
        if isinstance(node.func, ast.Attribute):
            if (
                isinstance(node.func.value, ast.Name)
                and node.func.value.id in self.imports
            ):
                return f"{self.imports[node.func.value.id]}.{node.func.attr}"
            return node.func.attr
        return "Any"

    def _infer_from_binop(self, node: ast.BinOp) -> str:
        left_type = self.infer_type_from_value(node.left)
        right_type = self.infer_type_from_value(node.right)
        if left_type == right_type and left_type in ["int", "float", "str"]:
            return left_type
        if "float" in [left_type, right_type] and all(
            t in ["int", "float"] for t in [left_type, right_type]
        ):
            return "float"
        return "Any"

    def _infer_from_unaryop(self, node: ast.UnaryOp) -> str:
        return (
            "bool"
            if isinstance(node.op, ast.Not)
            else self.infer_type_from_value(node.operand)
        )
