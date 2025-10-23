from pathlib import Path
from typing import List

from tree_sitter import Node, Tree, Parser, Language

from typing import Literal, Optional
import re

from utility.function import LocalValue, ValueType

DFType = Literal["source", "sink"]
DFValue = tuple[int, str, DFType]  # line number, variable name, 'source' or 'sink'


class Example:
    @staticmethod
    def from_str(s: str) -> Optional["Example"]:
        """
        Format:
        ```
        source_code line 1 // source_or_sink variable_name
        source_code line 2 // source_or_sink variable_name
        ...
        ```
        """
        matches = re.search(r"```\n(.*)\n\s*```", s, re.MULTILINE | re.DOTALL)
        if matches is None or len(matches.groups()) < 1:
            return None

        def parse_line(line_number: int, line: str) -> (str, Optional[DFValue]):
            line = line.strip()
            if len(line) == 0:
                return "", None
            segments = line.split("//")
            if len(segments) != 2:
                return line, None
            _code = segments[0].strip()
            _label = segments[1].strip()
            _label = re.search(r"^(source|sink)\s+(.*)$", _label)
            if _label is None or len(_label.groups()) < 2:
                return _code, None
            _label = (line_number, _label.group(2), _label.group(1))
            assert _label[2] in ["source", "sink"]
            assert _label[1] in _code
            return _code, _label

        lines = list(
            filter(
                lambda _: True,
                map(
                    lambda x: parse_line(x[0] + 1, x[1]),
                    enumerate(matches.group(1).split("\n")),
                ),
            )
        )
        code_lines = []
        labels = []
        for code, label in lines:
            code_lines.append(code)
            if label is not None:
                labels.append(label)

        return Example(code_lines, labels)

    def __init__(self, code: list[str], label: list[DFValue]) -> None:
        self.code = code  # list of lines of source code
        self.label = label  # list of (line number, variable name, 'source' or 'sink')


class TestExample:
    def test_from_str(self):
        example = """
```
int a = 0; // source a
float b = 0.0f; // source b
```
"""
        e = Example.from_str(example)
        assert e is not None
        assert e.code == ["int a = 0;", "float b = 0.0f;"]
        assert e.label == [(1, "a", "source"), (2, "b", "source")]

    def test_from_str_expr_sink(self):
        example = """
```
int a = 0;
int b = 1 + a; // sink 1 + a
```
"""
        e = Example.from_str(example)
        assert e is not None
        assert e.code == ["int a = 0;", "int b = 1 + a;"]
        assert e.label == [(2, "1 + a", "sink")]


class SynSpec:
    def __init__(
        self, fn_name: str, df_type: DFType, rules: str, examples: list[Example]
    ):
        self.fn_name = fn_name
        self.df_type = df_type
        self.rules = rules
        self.examples = examples

    @staticmethod
    def get_pretty_ast(example: Example) -> str:
        code = "\n".join(example.code)
        utils = TSUtils()
        tree = utils.parse_code(code)
        return utils.get_pretty_ast(code, tree)

    def get_example_prompt(self) -> str:
        prompt = ""
        for i, example in enumerate(self.examples):
            prompt += f"Example {i + 1}:\n"
            prompt += "```\n" + "\n".join(example.code) + "\n```\n"
            prompt += f"The corresponding AST of the above code is:\n"
            prompt += f"```\n{self.get_pretty_ast(example)}\n```\n"
            prompt += f"The following values are {self.df_type}s:\n"
            for j, labels in enumerate(example.label):
                prompt += f"- {labels[1]} on line {labels[0]} is a {labels[2]}\n"
            prompt += "\n"
        if len(self.examples) > 0:
            prompt += """
            The AST tree presents the tree structure in which each line is a node in the tree and
            the indentation indicates the parent-child relationship.
            Children of a node are printed in order, starting from index 0.
            The node is represented as `index [type] 'text'`, where index is the child index of
            current node in its parent node, type is the node type of the current node, and
            text is the string text of the node.
            """
        return prompt


class TSUtils:
    def __init__(self, language: str = None, library: Path = None) -> None:
        if language is None:
            language = "java"
        if library is None:
            library = (
                Path(__file__).resolve().parent.absolute()
                / "../../../lib/build/my-languages.so"
            )
        self.language = Language(str(library), language)
        self.library = library
        self.parser: Parser = Parser()
        self.parser.set_language(self.language)

    def parse_code(self, code: str) -> Tree:
        return self.parser.parse(bytes(code, "utf8"))

    @staticmethod
    def get_pretty_ast(source_code: str, tree: Tree) -> str:
        """
        Print the extracted AST in a pretty format.
        """

        def traverse(node: Node, depth: int) -> str:
            ret = ""
            for child in node.children:
                if child.type == "line_comment":
                    continue
                code = source_code[child.start_byte : child.end_byte]
                code = code.replace("// interesting", "")
                ret += "\n" + "  " * depth + f"[{child.type}] '{code}'"
                ret += traverse(child, depth + 1)
            return ret

        # prettify AST
        return traverse(tree.root_node, 0)

    @staticmethod
    def get_line_number(source_code: str, node: Node) -> int:
        """
        Get the line number of the given byte offset.
        """
        return source_code[: node.start_byte].count("\n") + 1

    @staticmethod
    def get_argument_list(node: Node) -> list[Node]:
        """
        Get the list of arguments from a function call.
        """
        assert node.type == "method_invocation"
        for child in node.children:
            if child.type == "argument_list":
                return child.children[1:-1]
        return []

    @staticmethod
    def get_binary_expression_operands(node: Node) -> list[Node]:
        """
        Get the operands from a binary expression.
        """
        assert node.type == "binary_expression"
        return [node.children[0], node.children[2]]

    @staticmethod
    def find_nodes_by_type(node: Node, node_type: str) -> list[Node]:
        """
        Find a node with the given type.
        """
        ret = []
        if node.type == node_type:
            ret += [node]
        for child in node.children:
            ret.extend(TSUtils.find_nodes_by_type(child, node_type))
            
        return ret


def source_extractor(fn):
    def wrapper(source_code: str, root_node: Node) -> List[DFValue]:
        def get_assigned_vars_in_line(line_number: int) -> List[str]:
            def inner(node: Node) -> list[str]:
                _r = []
                if (
                    source_code[: node.start_byte].count("\n") + 1 == line_number
                    and len(node.children) > 1
                    and node.children[1].type == "="
                ):
                    _r.append(node.children[0].text.decode("utf-8"))
                for child in node.children:
                    _r.extend(inner(child))
                return _r

            return inner(root_node)

        results = []
        for r in fn(source_code, root_node):
            for v in get_assigned_vars_in_line(r.line_number):
                results.append(LocalValue(r.name, v, r.v_type))
        return results

    return wrapper


def regulate_return_value(fn):
    def wrapper(source_code: str, root_node: Node) -> List[LocalValue]:
        values: List[DFValue] = fn(source_code, root_node)
        return list(
            map(
                lambda x: LocalValue(
                    x[1], x[0], ValueType.SRC if x[2] == "source" else ValueType.SINK
                ),
                values,
            )
        )

    return wrapper
