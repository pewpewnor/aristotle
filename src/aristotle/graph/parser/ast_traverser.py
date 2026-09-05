import ast
import json
import os
from collections import defaultdict
from typing import Dict, List, Optional

import nbformat
from nbconvert import PythonExporter

from .node import Node
from .parser_settings import ParserSettings
from .relationship import Relationship
from .type_inferrer import TypeInferrer


def extract_module_name(path: str) -> str:
    path = path.lstrip("./\\")
    path_without_ext = os.path.splitext(path)[0]
    module_path = path_without_ext.replace(os.path.sep, ".")
    return module_path


class ASTTraverser(ast.NodeVisitor):
    def __init__(
        self,
        codebase_name: str,
        file_path: str,
        virtual_path: str,
        reference: str,
        settings: ParserSettings,
    ):
        self.codebase_name = codebase_name
        self.file_path = file_path
        self.reference = reference
        self.settings = settings
        self.module_name = extract_module_name(virtual_path)

        self.current_class: Optional[str] = None
        self.current_function: Optional[str] = None

        self.class_fields: defaultdict = defaultdict(set)
        self.function_params: defaultdict = defaultdict(str)
        self.local_vars: set = set()
        self.global_vars: defaultdict = defaultdict(str)
        self.imports: defaultdict = defaultdict(str)

        # Nodes: uuid -> Node
        self.nodes: dict[str, Node] = {}
        self.relationships: dict[tuple[str, str, str], dict] = {}

        self.type_inferrer = TypeInferrer(
            dict(self.function_params), dict(self.global_vars), dict(self.imports)
        )

    def should_include_name(self, name: str) -> bool:
        """Determine if a name should be included based on privacy settings."""
        if name == "self":
            return False
        if name.startswith("__") and name.endswith("__"):
            return self.settings.include_dunder
        if name.startswith("_"):
            return self.settings.include_private_members
        return True

    def get_full_name(self, name: str, context: str) -> Optional[str]:
        """Generate fully qualified name for a given entity."""
        if not self.should_include_name(name):
            return None

        namespace_parts = [self.codebase_name]
        if self.settings.include_module_name:
            namespace_parts.append(self.module_name)

        if context == "class" and self.current_class:
            namespace_parts.extend([self.current_class, name])
        elif context == "method" and self.current_class and self.current_function:
            namespace_parts.extend([self.current_class, self.current_function, name])
        elif context == "function" and self.current_function and not self.current_class:
            namespace_parts.extend([self.current_function, name])
        elif context == "module":
            namespace_parts.append(name)
        else:
            namespace_parts.append(name)

        return ".".join(namespace_parts)

    def get_root_namespace(self) -> str:
        """Get the root namespace for module relationships."""
        if self.settings.include_module_name:
            return f"{self.codebase_name}.{self.module_name}"
        return self.codebase_name

    def add_node(self, uuid: str, kind: str, attributes: Optional[Dict] = None):
        if uuid in self.nodes:
            self.nodes[uuid].attributes.update(attributes or {})
            return
        self.nodes[uuid] = Node(uuid=uuid, kind=kind, attributes=attributes or {})

    def add_relationship(
        self,
        source: Optional[str],
        relation: str,
        target: Optional[str],
        source_kind: str,
        target_kind: str,
        extra_attrs: Optional[Dict] = None,
    ):
        if source is None or target is None:
            return
        key = (source, relation, target)
        if key in self.relationships:
            return
        attrs = extra_attrs or {}
        attrs["source_kind"] = source_kind
        attrs["target_kind"] = target_kind
        attrs["reference"] = self.reference
        # Ensure basic human-readable names and file path are present for downstream consumers/tests
        if "source_name" not in attrs:
            attrs["source_name"] = source.split(".")[-1]
        # Only auto-populate target_name for non-INHERITS relations; INHERITS may intentionally omit target_name
        if relation != "INHERITS" and "target_name" not in attrs:
            attrs["target_name"] = target.split(".")[-1]
        # do not inject file_path automatically here; only use file_path when explicitly set
        # ensure nodes exist (only set name by default)
        self.add_node(source, source_kind, {"name": source.split(".")[-1]})
        self.add_node(target, target_kind, {"name": target.split(".")[-1]})
        self.relationships[key] = attrs

    def parse_annotation(self, annotation) -> Optional[str]:
        """Parse an AST annotation into a string. Returns None when no annotation present."""
        if annotation is None:
            return None
        elif isinstance(annotation, ast.Name):
            # Check if it's an imported type
            if annotation.id in self.imports:
                return f"{self.imports[annotation.id]}.{annotation.id}"
            return annotation.id
        elif isinstance(annotation, ast.Subscript):
            base = self.parse_annotation(annotation.value) or "Any"
            # Handle different AST slice shapes across Python versions
            sub_node = getattr(annotation.slice, "value", annotation.slice)
            sub = self.parse_annotation(sub_node) or "Any"
            return f"{base}[{sub}]"
        elif isinstance(annotation, ast.Attribute):
            val = self.parse_annotation(annotation.value) or "Any"
            return f"{val}.{annotation.attr}"
        elif isinstance(annotation, ast.Tuple):
            return ", ".join(self.parse_annotation(e) or "Any" for e in annotation.elts)
        elif isinstance(annotation, ast.Constant):
            return str(annotation.value)
        return "Unknown"

    def infer_target_return_type_from_body(self, body) -> str:
        """Infer return type by analyzing function body for return statements."""
        target_return_types = set()

        for node in ast.walk(ast.Module(body=body, type_ignores=[])):
            if isinstance(node, ast.Return):
                if node.value:
                    inferred_type = self.type_inferrer.infer_type_from_value(node.value)
                    target_return_types.add(inferred_type)
                else:
                    target_return_types.add("None")

        if not target_return_types:
            return "None"  # No return statements found
        elif len(target_return_types) == 1:
            return target_return_types.pop()
        else:
            # Multiple return types - create union
            return f"Union[{', '.join(sorted(target_return_types))}]"

    def build_class_signature(self, node: ast.ClassDef) -> str:
        """Build the class signature including inheritance."""
        class_name = node.name
        if not node.bases:
            return f"class {class_name}"

        # Build base class names
        base_names = []
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_names.append(base.id)
            elif isinstance(base, ast.Attribute):
                # Handle cases like module.ClassName
                base_name = self.parse_annotation(base) or "Unknown"
                base_names.append(base_name)
            else:
                base_name = self.parse_annotation(base) or "Unknown"
                base_names.append(base_name)

        return f"class {class_name}({', '.join(base_names)})"

    # ---------------------------
    # AST Visitors
    # ---------------------------
    def visit_Import(self, node):
        """Track imports for proper namespacing."""
        for alias in node.names:
            if alias.asname:
                self.imports[alias.asname] = alias.name
            else:
                # For 'import os', we map 'os' to 'os'
                self.imports[alias.name.split(".")[-1]] = alias.name

        # Update type inferrer with new imports
        self.type_inferrer.imports = dict(self.imports)
        self.generic_visit(node)

    def visit_ImportFrom(self, node):
        """Track from imports for proper namespacing."""
        module_name = node.module or ""
        for alias in node.names:
            if alias.name == "*":
                continue  # Skip wildcard imports
            imported_name = alias.asname if alias.asname else alias.name
            self.imports[imported_name] = (
                f"{module_name}.{alias.name}" if module_name else alias.name
            )

        # Update type inferrer with new imports
        self.type_inferrer.imports = dict(self.imports)
        self.generic_visit(node)

    def visit_Module(self, node):
        # Capture module docstring (if present) and ensure module node exists
        module_doc = ast.get_docstring(node)
        module_uuid = self.get_full_name(
            os.path.splitext(os.path.basename(self.reference))[0], "module"
        )
        if module_uuid:
            # attach module node with docstring and file path
            attrs = {
                "name": os.path.splitext(os.path.basename(self.reference))[0],
                "reference": self.reference,
            }
            if module_doc:
                attrs["docstring"] = module_doc
            self.add_node(module_uuid, "MODULE", attrs)

        self.generic_visit(node)

    def visit_ClassDef(self, node):
        class_name = node.name

        if not self.should_include_name(class_name):
            return

        full_class_name = self.get_full_name(class_name, "module")
        root_namespace = self.get_root_namespace()

        # Build class signature with inheritance
        class_signature = self.build_class_signature(node)

        # MODULE CONTAINS CLASS
        self.add_relationship(
            root_namespace,
            "CONTAINS",
            full_class_name,
            source_kind="MODULE",
            target_kind="CLASS",
            extra_attrs={
                "target_name": class_name,
                "target_signature": class_signature,
            },
        )

        # Attach class docstring (if present) to the class node attributes
        class_doc = ast.get_docstring(node)
        if class_doc and full_class_name:
            # ensure node exists and merge docstring
            self.add_node(
                full_class_name,
                "CLASS",
                {
                    "name": class_name,
                    "reference": self.reference,
                    "docstring": class_doc,
                },
            )

        # class inherits other classes
        for base in node.bases:
            if isinstance(base, ast.Name):
                base_name = base.id
                # check if it's an imported class
                if base_name in self.imports:
                    base_full_name = self.imports[base_name]
                else:
                    # build base class name with proper namespace
                    if self.settings.include_module_name:
                        base_full_name = (
                            f"{self.codebase_name}.{self.module_name}.{base_name}"
                        )
                    else:
                        base_full_name = f"{self.codebase_name}.{base_name}"
            else:
                base_name = self.parse_annotation(base) or "Unknown"
                base_full_name = base_name

            self.add_relationship(
                full_class_name,
                "INHERITS",
                base_full_name,
                source_kind="CLASS",
                target_kind="CLASS",
            )

        prev_class = self.current_class
        self.current_class = class_name
        self.generic_visit(node)
        self.current_class = prev_class

    def visit_FunctionDef(self, node):
        func_name = node.name

        if not self.should_include_name(func_name):
            self.generic_visit(node)
            return

        # Build argument signature with full names for parameters
        arg_types = []
        for arg in node.args.args:
            if self.should_include_name(arg.arg):
                ann = self.parse_annotation(arg.annotation) or "Any"
                arg_types.append(f"{arg.arg}: {ann}")

        # Parse return annotation (None means not annotated)
        ret_ann = self.parse_annotation(node.returns)
        if ret_ann is None or ret_ann == "Unknown":
            # Try to infer from body
            inferred_target_return_type = self.infer_target_return_type_from_body(
                node.body
            )
            target_return_type = inferred_target_return_type or "Any"
        else:
            target_return_type = ret_ann

        signature = f"{func_name}(self, {', '.join(arg_types)}) -> {target_return_type}"

        # capture function/method docstring
        func_doc = ast.get_docstring(node)

        if self.current_class:
            node_type = "METHOD"
            full_func_name = self.get_full_name(func_name, "class")
            full_class_name = self.get_full_name(self.current_class, "module")

            self.add_relationship(
                full_class_name,
                "HAS_METHOD",
                full_func_name,
                source_kind="CLASS",
                target_kind=node_type,
                extra_attrs={
                    "target_name": func_name,
                    "target_signature": signature,
                    "target_return_type": target_return_type,
                },
            )
            # attach docstring to method node if present
            if func_doc and full_func_name:
                self.add_node(
                    full_func_name,
                    node_type,
                    {
                        "name": func_name,
                        "reference": self.reference,
                        "docstring": func_doc,
                    },
                )
        else:
            node_type = "FUNCTION"
            full_func_name = self.get_full_name(func_name, "module")
            root_namespace = self.get_root_namespace()

            self.add_relationship(
                root_namespace,
                "CONTAINS",
                full_func_name,
                source_kind="MODULE",
                target_kind=node_type,
                extra_attrs={
                    "target_name": func_name,
                    "target_signature": signature,
                    "target_return_type": target_return_type,
                },
            )
            if func_doc and full_func_name:
                self.add_node(
                    full_func_name,
                    node_type,
                    {
                        "name": func_name,
                        "reference": self.reference,
                        "docstring": func_doc,
                    },
                )

        # Track parameters as FIELD only if inside a class and should be included
        if self.current_class:
            full_class_name = self.get_full_name(self.current_class, "module")
            for arg in node.args.args:
                if self.should_include_name(arg.arg):
                    full_param_name = self.get_full_name(arg.arg, "method")
                    ann = self.parse_annotation(arg.annotation) or "Any"

                    self.add_relationship(
                        full_class_name,
                        "HAS_FIELD",
                        full_param_name,
                        source_kind="CLASS",
                        target_kind="FIELD",
                        extra_attrs={
                            "target_name": arg.arg,
                            "target_type": ann,
                        },
                    )
                    # also ensure param node exists
                    if full_param_name:
                        self.add_node(
                            full_param_name,
                            "FIELD",
                            {"name": arg.arg, "reference": self.reference},
                        )

        # Store function params for tracking (used by the inferrer)
        temp_function_params = {}
        for arg in node.args.args:
            if self.should_include_name(arg.arg):
                temp_function_params[arg.arg] = (
                    self.parse_annotation(arg.annotation) or "Any"
                )
        self.function_params.update(temp_function_params)

        # Update type inferrer with new function parameters
        self.type_inferrer.function_params = dict(self.function_params)

        prev_function = self.current_function
        self.current_function = func_name
        self.local_vars = set()
        self.generic_visit(node)
        self.current_function = prev_function

        # Clear function params after processing
        for key in temp_function_params:
            if key in self.function_params:
                del self.function_params[key]
        self.local_vars = set()

        # Reset type inferrer function params
        self.type_inferrer.function_params = {}

    def visit_AnnAssign(self, node: ast.AnnAssign):
        """Handle annotated assignments (module-level or class-level)."""
        # target could be Name or Attribute
        target = node.target
        annotation = self.parse_annotation(node.annotation)
        value = node.value

        # Module-level annotated variable
        if (
            isinstance(target, ast.Name)
            and not self.current_class
            and not self.current_function
        ):
            var_name = target.id
            if self.should_include_name(var_name):
                ann = annotation or "Any"
                self.global_vars[var_name] = ann
                self.type_inferrer.global_vars = dict(self.global_vars)

                full_var_name = self.get_full_name(var_name, "module")
                root_namespace = self.get_root_namespace()
                self.add_relationship(
                    root_namespace,
                    "CONTAINS",
                    full_var_name,
                    source_kind="MODULE",
                    target_kind="GLOBAL_VARIABLE",
                    extra_attrs={
                        "target_name": var_name,
                        "target_type": ann,
                    },
                )
                # ensure variable node exists
                if full_var_name:
                    self.add_node(
                        full_var_name,
                        "GLOBAL_VARIABLE",
                        {
                            "name": var_name,
                            "reference": self.reference,
                            "target_type": ann,
                        },
                    )

        # Class or instance annotated attribute like self.x: int = 5 or x: int at class level
        if (
            isinstance(target, ast.Attribute)
            and isinstance(target.value, ast.Name)
            and target.value.id == "self"
        ):
            if not self.current_class:
                return
            field_name = target.attr
            if self.should_include_name(field_name):
                full_class_name = self.get_full_name(self.current_class, "module")
                full_field_name = self.get_full_name(field_name, "class")
                self.class_fields[full_class_name].add(field_name)

                # Prefer annotation, fall back to value inference
                if annotation:
                    field_type = annotation
                elif value is not None:
                    field_type = self.type_inferrer.infer_type_from_value(value)
                else:
                    field_type = "Any"

                self.add_relationship(
                    full_class_name,
                    "HAS_FIELD",
                    full_field_name,
                    source_kind="CLASS",
                    target_kind="FIELD",
                    extra_attrs={
                        "target_name": field_name,
                        "target_type": field_type,
                    },
                )
                if full_field_name:
                    self.add_node(
                        full_field_name,
                        "FIELD",
                        {
                            "name": field_name,
                            "reference": self.reference,
                            "target_type": field_type,
                        },
                    )

        # Class-level simple annotated name (x: int)
        if (
            isinstance(target, ast.Name)
            and self.current_class
            and not self.current_function
        ):
            field_name = target.id
            if self.should_include_name(field_name):
                full_class_name = self.get_full_name(self.current_class, "module")
                full_field_name = self.get_full_name(field_name, "class")
                self.class_fields[full_class_name].add(field_name)
                ann = annotation or (
                    self.type_inferrer.infer_type_from_value(value)
                    if value is not None
                    else "Any"
                )

                self.add_relationship(
                    full_class_name,
                    "HAS_FIELD",
                    full_field_name,
                    source_kind="CLASS",
                    target_kind="FIELD",
                    extra_attrs={
                        "target_name": field_name,
                        "target_type": ann,
                    },
                )
                if full_field_name:
                    self.add_node(
                        full_field_name,
                        "FIELD",
                        {
                            "name": field_name,
                            "reference": self.reference,
                            "target_type": ann,
                        },
                    )

        self.generic_visit(node)

    def visit_Assign(self, node):
        """Track class field assignments and global variables."""
        # Handle class field assignments (self.field = value)
        if self.current_class and isinstance(node.targets[0], ast.Attribute):
            attr = node.targets[0]
            if isinstance(attr.value, ast.Name) and attr.value.id == "self":
                field_name = attr.attr
                if self.should_include_name(field_name):
                    full_class_name = self.get_full_name(self.current_class, "module")
                    full_field_name = self.get_full_name(field_name, "class")

                    self.class_fields[full_class_name].add(field_name)

                    # Determine field type from assignment with inference
                    field_type = (
                        self.type_inferrer.infer_type_from_value(node.value)
                        if node.value is not None
                        else "Any"
                    )

                    self.add_relationship(
                        full_class_name,
                        "HAS_FIELD",
                        full_field_name,
                        source_kind="CLASS",
                        target_kind="FIELD",
                        extra_attrs={
                            "target_name": field_name,
                            "target_type": field_type,
                        },
                    )
                    if full_field_name:
                        self.add_node(
                            full_field_name,
                            "FIELD",
                            {
                                "name": field_name,
                                "reference": self.reference,
                                "target_type": field_type,
                            },
                        )

        # Handle global variable assignments (only if not inside a function or class)
        elif (
            not self.current_function
            and not self.current_class
            and isinstance(node.targets[0], ast.Name)
        ):
            var_name = node.targets[0].id
            if self.should_include_name(var_name):
                # Infer type from assignment value
                var_type = (
                    self.type_inferrer.infer_type_from_value(node.value)
                    if node.value is not None
                    else "Any"
                )
                self.global_vars[var_name] = var_type

                # Update type inferrer with new global variables
                self.type_inferrer.global_vars = dict(self.global_vars)

                # Add relationship for global variable and ensure node exists
                full_var_name = self.get_full_name(var_name, "module")
                root_namespace = self.get_root_namespace()

                self.add_relationship(
                    root_namespace,
                    "CONTAINS",
                    full_var_name,
                    source_kind="MODULE",
                    target_kind="GLOBAL_VARIABLE",
                    extra_attrs={
                        "target_name": var_name,
                        "target_type": var_type,
                    },
                )
                if full_var_name:
                    self.add_node(
                        full_var_name,
                        "GLOBAL_VARIABLE",
                        {
                            "name": var_name,
                            "reference": self.reference,
                            "target_type": var_type,
                        },
                    )

        self.generic_visit(node)

    def visit_Name(self, node):
        # Track variable usage for HAS_PARAMETER relationships
        if (
            self.current_function
            and isinstance(node.ctx, ast.Load)
            and self.should_include_name(node.id)
        ):
            target_kind = None
            target_type = None
            full_target_name = None

            if node.id in self.global_vars:
                target_kind = "GLOBAL_VARIABLE"
                target_type = self.global_vars[node.id]
                full_target_name = self.get_full_name(node.id, "module")
            elif self.current_class:
                full_class_name = self.get_full_name(self.current_class, "module")
                if node.id in self.class_fields[full_class_name]:
                    target_kind = "FIELD"
                    target_type = "Unknown"
                    full_target_name = self.get_full_name(node.id, "class")

            if node.id in self.function_params:
                target_kind = "FIELD"
                target_type = self.function_params[node.id]
                if self.current_class:
                    full_target_name = self.get_full_name(node.id, "method")
                else:
                    full_target_name = self.get_full_name(node.id, "function")

            if target_kind and full_target_name:
                source_kind = "METHOD" if self.current_class else "FUNCTION"
                full_func_name = self.get_full_name(
                    self.current_function, "class" if self.current_class else "module"
                )

                self.add_relationship(
                    full_func_name,
                    "HAS_PARAMETER",
                    full_target_name,
                    source_kind=source_kind,
                    target_kind=target_kind,
                    extra_attrs={
                        "target_name": node.id,
                        "target_type": target_type,
                    },
                )
                # ensure parameter node exists
                self.add_node(
                    full_target_name,
                    target_kind,
                    {"name": node.id, "reference": self.reference},
                )

        self.generic_visit(node)

    def traverse(self) -> tuple[list[Node], list["Relationship"]]:
        if self.file_path.endswith(".ipynb"):
            try:
                with open(self.file_path, "r", encoding="utf-8") as f:
                    notebook_content = json.load(f)

                nb = nbformat.from_dict(notebook_content)
                exporter = PythonExporter()
                source_code, _ = exporter.from_notebook_node(nb)
            except Exception as e:
                print(
                    f"[WARN] Error converting notebook to Python for file '{self.file_path}': {e}"
                )
                raise e
        else:
            with open(self.file_path, "r", encoding="utf-8") as f:
                source_code = f.read()

        tree = ast.parse(source_code, filename=self.file_path)
        self.visit(tree)

        nodes = list(self.nodes.values())
        relationship_objs: List[Relationship] = []
        for (s, r, t), attrs in self.relationships.items():
            relationship_objs.append(Relationship(s, r, t, attrs))

        return nodes, relationship_objs
