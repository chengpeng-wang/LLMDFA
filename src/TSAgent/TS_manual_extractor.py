import sys
from os import path
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from TSAgent.TS_analyzer import TSAnalyzer
from typing import Tuple, List
from utility.function import *


def find_dbz_src(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for dbz detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of source values
    """
    # Find assignment_expression
    nodes = TSAnalyzer.find_nodes(root_node, "assignment_expression")

    # Find local_variable_declaration
    nodes.extend(TSAnalyzer.find_nodes(root_node, "variable_declarator"))

    # Extract the name info and line number
    lines = []
    for node in nodes:
        is_src_node = False
        for child in node.children:
            if (
                child.type == "decimal_integer_literal"
                and source_code[child.start_byte : child.end_byte] == "0"
            ):
                is_src_node = True
            if child.type == "decimal_floating_point_literal" and source_code[
                child.start_byte : child.end_byte
            ] in {"0.0", "0.0f"}:
                is_src_node = True
            if child.type == "method_invocation" and (
                "parseInt(" in source_code[child.start_byte : child.end_byte]
                or "nextInt(" in source_code[child.start_byte : child.end_byte]
                or "parseFloat(" in source_code[child.start_byte : child.end_byte]
                or "nextFloat(" in source_code[child.start_byte : child.end_byte]
            ):
                is_src_node = True
        if is_src_node:
            for child in node.children:
                if child.type == "identifier":
                    name = source_code[child.start_byte : child.end_byte]
                    # If the program is wrapped with ```
                    # line_number should be equal to source_code[:child.start_byte].count('\n')
                    line_number = source_code[: child.start_byte].count("\n") + 1
                    lines.append(LocalValue(name, line_number, ValueType.SRC))
    return lines


def find_dbz_sink(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for dbz detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of sink values
    """
    nodes = TSAnalyzer.find_nodes(root_node, "binary_expression")
    lines = []
    for node in nodes:
        is_sink_node = False
        for child in node.children:
            if child.type in {"/", "%"}:
                is_sink_node = True
                continue
            if is_sink_node and child.type == "identifier":
                name = source_code[child.start_byte : child.end_byte]
                line_number = source_code[: child.start_byte].count("\n") + 1
                lines.append(LocalValue(name, line_number, ValueType.SINK))
    return lines


def find_xss_src(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for xss detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of source values
    """
    # Find assignment_expression
    nodes = TSAnalyzer.find_nodes(root_node, "assignment_expression")

    # Find local_variable_declaration
    nodes.extend(TSAnalyzer.find_nodes(root_node, "variable_declarator"))

    # Extract the name info and line number
    lines = []
    for node in nodes:
        is_src_node = False

        for child in node.children:
            if child.type == "method_invocation" and (
                "readLine(" in source_code[child.start_byte : child.end_byte]
                or "getString(" in source_code[child.start_byte : child.end_byte]
                or "getenv(" in source_code[child.start_byte : child.end_byte]
                or "getValue(" in source_code[child.start_byte : child.end_byte]
                or "executeQuery(" in source_code[child.start_byte : child.end_byte]
                or "getCookies(" in source_code[child.start_byte : child.end_byte]
                or "getParameter(" in source_code[child.start_byte : child.end_byte]
                or "nextToken(" in source_code[child.start_byte : child.end_byte]
                or "getProperty(" in source_code[child.start_byte : child.end_byte]
                or "substring(" in source_code[child.start_byte : child.end_byte]
            ):
                is_src_node = True

        if is_src_node:
            for child in node.children:
                if child.type == "identifier":
                    name = source_code[child.start_byte : child.end_byte]
                    line_number = source_code[: child.start_byte].count("\n") + 1
                    lines.append(LocalValue(name, line_number, ValueType.SRC))
    return lines


def find_xss_sink(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for dbz detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of sink values
    """
    nodes = TSAnalyzer.find_nodes(root_node, "method_invocation")
    lines = []
    for node in nodes:
        is_sink_function = False
        for sub_node in node.children:
            if (
                sub_node.type == "identifier"
                and source_code[sub_node.start_byte : sub_node.end_byte] == "println"
            ):
                is_sink_function = True
                break
        if is_sink_function:
            for sub_node in node.children:
                if sub_node.type == "argument_list":
                    line_number = source_code[: sub_node.start_byte].count("\n") + 1
                    name = source_code[sub_node.start_byte + 1 : sub_node.end_byte - 1]
                    lines.append(LocalValue(name, line_number, ValueType.SINK))
    return lines


def find_ci_src(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for xss detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of source values
    """
    # Find assignment_expression
    nodes = TSAnalyzer.find_nodes(root_node, "assignment_expression")

    # Find local_variable_declaration
    nodes.extend(TSAnalyzer.find_nodes(root_node, "variable_declarator"))

    # Extract the name info and line number
    lines = []
    for node in nodes:
        is_src_node = False
        for child in node.children:
            if child.type == "method_invocation" and (
                "readLine(" in source_code[child.start_byte : child.end_byte]
                or "getString(" in source_code[child.start_byte : child.end_byte]
                or "getenv(" in source_code[child.start_byte : child.end_byte]
                or "getValue(" in source_code[child.start_byte : child.end_byte]
                or "executeQuery(" in source_code[child.start_byte : child.end_byte]
                or "getCookies(" in source_code[child.start_byte : child.end_byte]
                or "getParameter(" in source_code[child.start_byte : child.end_byte]
                or "nextToken(" in source_code[child.start_byte : child.end_byte]
                or "getProperty(" in source_code[child.start_byte : child.end_byte]
                or "substring(" in source_code[child.start_byte : child.end_byte]
            ):
                is_src_node = True
        if is_src_node:
            for child in node.children:
                if child.type == "identifier":
                    name = source_code[child.start_byte : child.end_byte]
                    line_number = source_code[: child.start_byte].count("\n") + 1
                    lines.append(LocalValue(name, line_number, ValueType.SRC))
    return lines


def find_ci_sink(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for dbz detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of sink values
    """
    nodes = TSAnalyzer.find_nodes(root_node, "method_invocation")
    lines = []
    for node in nodes:
        is_sink_function = False
        for sub_node in node.children:
            if (
                sub_node.type == "identifier"
                and source_code[sub_node.start_byte : sub_node.end_byte] == "exec"
            ):
                is_sink_function = True
                break
        if is_sink_function:
            for sub_node in node.children:
                if sub_node.type == "argument_list":
                    line_number = source_code[: sub_node.start_byte].count("\n") + 1
                    name = source_code[sub_node.start_byte + 1 : sub_node.end_byte - 1]
                    lines.append(LocalValue(name, line_number, ValueType.SINK))
    return lines


def find_taint_src(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for xss detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of source values
    """
    # Find assignment_expression
    nodes = TSAnalyzer.find_nodes(root_node, "assignment_expression")

    # Find local_variable_declaration
    nodes.extend(TSAnalyzer.find_nodes(root_node, "variable_declarator"))

    # Extract the name info and line number
    lines = []
    for node in nodes:
        is_src_node = False
        for child in node.children:
            if child.type == "method_invocation" and (
                "getStringExtra(" in source_code[child.start_byte : child.end_byte]
            ):
                is_src_node = True
                print("hit")
                print(source_code[child.start_byte : child.end_byte])
                line_number = source_code[: child.start_byte].count("\n") + 1
                name = (
                    source_code[node.start_byte : node.end_byte].split("=")[0].strip()
                )
                print(name, " added")
                lines.append(LocalValue(name, line_number, ValueType.SRC))
    return lines


def find_taint_sink(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # This function should be synthesized automatically. This implementation is just a demo.
    """
    Find source values for dbz detection
    :param source_code: The source code
    :param root_node: The root node of the parse tree
    :return: The variable names and line numbers of sink values
    """
    nodes = TSAnalyzer.find_nodes(root_node, "method_invocation")
    lines = []
    for node in nodes:
        is_sink_function = False
        for sub_node in node.children:
            if sub_node.type == "identifier" and (
                source_code[sub_node.start_byte : sub_node.end_byte] == "execute"
            ):
                print("hit sink")
                is_sink_function = True
                break
        if is_sink_function:
            for sub_node in node.children:
                if sub_node.type == "argument_list":
                    line_number = source_code[: sub_node.start_byte].count("\n") + 1
                    arg_list = source_code[
                        sub_node.start_byte + 1 : sub_node.end_byte - 1
                    ]
                    for arg_name in arg_list.split(","):
                        lines.append(
                            LocalValue(arg_name.strip(), line_number, ValueType.SINK)
                        )
    return lines
