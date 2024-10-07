from tree_sitter import Node

from TSAgent.synthesis.utils import *
from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def find_dbz_src(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    :param source_code: The original source code to be analyzed as a string.
    :param root_node: The root node of the syntax tree of the source code.
    :return: A list of tuples representing a list of data flow source values.
             The tuple is: (line number, source variable name, "source").
    """

    assignments = TSUtils.find_nodes_by_type(root_node, "assignment_expression")
    declarations = TSUtils.find_nodes_by_type(root_node, "variable_declarator")
    assignments.extend(declarations)

    sources = []
    for node in assignments:
        # first get all the nested children of the node that may contain the source recursively
        nested_children = TSUtils.find_nodes_by_type(node, "decimal_integer_literal")
        nested_children.extend(
            TSUtils.find_nodes_by_type(node, "decimal_floating_point_literal")
        )
        nested_children.extend(
            TSUtils.find_nodes_by_type(node, "method_invocation")
        )

        # second check if the child node contains the source
        for child in nested_children:
            # TODO: fill the condition __CONDITION__ on child node here to filter nodes that contain the source
            # Please use `source_code[child.start_byte:child.end_byte]` to get the text of the child node
            if (
                source_code[child.start_byte : child.end_byte] == "0"
                or source_code[child.start_byte : child.end_byte] == "0.0"
                or source_code[child.start_byte : child.end_byte] == "0.0f"
                or "parseInt" in source_code[child.start_byte : child.end_byte]
                or "parseFloat" in source_code[child.start_byte : child.end_byte]
                or "nextInt" in source_code[child.start_byte : child.end_byte]
                or "nextFloat" in source_code[child.start_byte : child.end_byte]
            ):
                v: DFValue = (
                    TSUtils.get_line_number(source_code, node),
                    source_code[node.start_byte : node.end_byte]
                    .split("=")[0]
                    .strip()
                    .split(" ")[-1],
                    "source",
                )
                sources.append(v)
        pass
    return sources
from tree_sitter import Node

from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def find_dbz_sink(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    """

    # TODO: fill the node type __NODE_TYPE__ here to filter nodes that contain the source
    nodes = TSUtils.find_nodes_by_type(root_node, 'binary_expression')

    sink_nodes = []
    for node in nodes:
        # TODO: fill the condition __CONDITION__ here to filter nodes that contain the source
        # Please use `source_code[child.start_byte:child.end_byte]` to get the text of a node
        if '/' in source_code[node.start_byte:node.end_byte] or '%' in source_code[node.start_byte:node.end_byte]:
            sink_nodes.append(node)

    sinks = []

    def extract_sinks(node: Node) -> list[DFValue]:
        sink_values = []
        # TODO: Extract sinks from the given node.
        # Below are several utility functions that may be useful:
        # - To extract a list of arguments from a method invocation node, use TSUtils.get_argument_list(node).
        # - To extract a list of operands from a binary expression node, use TSUtils.get_binary_expression_operands(node).
        # Each of the sink nodes should be a tuple (line number, sink variable name, "sink").
        line_number = TSUtils.get_line_number(source_code, node)
        operands = TSUtils.get_binary_expression_operands(node)
        if len(operands) == 2 and operands[1].type == 'identifier':
            sink_values.append((line_number, source_code[operands[1].start_byte:operands[1].end_byte], "sink"))
        return sink_values

    for node in sink_nodes:
        sinks.extend(extract_sinks(node))

    return sinks
from tree_sitter import Node

from TSAgent.synthesis.utils import *
from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def find_xss_src(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    :param source_code: The original source code to be analyzed as a string.
    :param root_node: The root node of the syntax tree of the source code.
    :return: A list of tuples representing a list of data flow source values.
             The tuple is: (line number, source variable name, "source").
    """

    assignments = TSUtils.find_nodes_by_type(root_node, "assignment_expression")
    declarations = TSUtils.find_nodes_by_type(root_node, "variable_declarator")
    assignments.extend(declarations)

    sources = []
    for node in assignments:
        # first get all the nested children of the node that may contain the source recursively
        nested_children = TSUtils.find_nodes_by_type(node, "method_invocation")
        nested_children.extend(
            TSUtils.find_nodes_by_type(node, "identifier")
        )  # you may want to repeat this line for more child node types

        # second check if the child node contains the source
        for child in nested_children:
            # TODO: fill the condition __CONDITION__ on child node here to filter nodes that contain the source
            # Please use `source_code[child.start_byte:child.end_byte]` to get the text of the child node
            if "readLine" in source_code[child.start_byte:child.end_byte] or "executeQuery" in source_code[child.start_byte:child.end_byte] or "getCookies" in source_code[child.start_byte:child.end_byte] or "getParameter" in source_code[child.start_byte:child.end_byte] or "nextToken" in source_code[child.start_byte:child.end_byte] or "getProperty" in source_code[child.start_byte:child.end_byte]:
                v: DFValue = (
                    TSUtils.get_line_number(source_code, node),
                    source_code[node.start_byte : node.end_byte]
                    .split("=")[0]
                    .strip()
                    .split(" ")[-1],
                    "source",
                )
                sources.append(v)
        pass
    return sources
from tree_sitter import Node

from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def find_xss_sink(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    """

    # TODO: fill the node type here to filter nodes that contain the source
    nodes = TSUtils.find_nodes_by_type(root_node, "method_invocation")

    sink_nodes = []
    for node in nodes:
        # TODO: fill the condition here to filter nodes that contain the source
        # Please use `source_code[child.start_byte:child.end_byte]` to get the text of a node
        if "println" in source_code[node.start_byte:node.end_byte] or "print" in source_code[node.start_byte:node.end_byte]:
            sink_nodes.append(node)

    sinks = []

    def extract_sinks(node: Node) -> list[DFValue]:
        sink_values = []
        # Extract sinks from the given node.
        # Below are several utility functions that may be useful:
        # - To extract a list of arguments from a method invocation node, use TSUtils.get_argument_list(node).
        # Each of the sink nodes should be a tuple (line number, sink variable name, "sink").
        line_number = TSUtils.get_line_number(source_code, node)
        arguments = TSUtils.get_argument_list(node)
        for arg in arguments:
            sink_values.append((line_number, source_code[arg.start_byte:arg.end_byte], "sink"))
        return sink_values

    for node in sink_nodes:
        sinks.extend(extract_sinks(node))

    return sinks
from tree_sitter import Node

from TSAgent.synthesis.utils import *
from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def find_ci_src(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    :param source_code: The original source code to be analyzed as a string.
    :param root_node: The root node of the syntax tree of the source code.
    :return: A list of tuples representing a list of data flow source values.
             The tuple is: (line number, source variable name, "source").
    """

    assignments = TSUtils.find_nodes_by_type(root_node, "assignment_expression")
    declarations = TSUtils.find_nodes_by_type(root_node, "variable_declarator")
    assignments.extend(declarations)

    sources = []
    for node in assignments:
        # first get all the nested children of the node that may contain the source recursively
        nested_children = TSUtils.find_nodes_by_type(node, "method_invocation")
        nested_children.extend(
            TSUtils.find_nodes_by_type(node, "array_access")
        )  # you may want to repeat this line for more child node types

        # second check if the child node contains the source
        for child in nested_children:
            # TODO: fill the condition __CONDITION__ on child node here to filter nodes that contain the source
            # Please use `source_code[child.start_byte:child.end_byte]` to get the text of the child node
            if "readLine" in source_code[child.start_byte:child.end_byte] or "getString" in source_code[child.start_byte:child.end_byte] or "getenv" in source_code[child.start_byte:child.end_byte] or "getValue" in source_code[child.start_byte:child.end_byte] or "nextToken" in source_code[child.start_byte:child.end_byte] or "executeQuery" in source_code[child.start_byte:child.end_byte] or "getCookies" in source_code[child.start_byte:child.end_byte] or "getParameter" in source_code[child.start_byte:child.end_byte] or "nextToken" in source_code[child.start_byte:child.end_byte] or "getProperty" in source_code[child.start_byte:child.end_byte] or "substring" in source_code[child.start_byte:child.end_byte]:
                v: DFValue = (
                    TSUtils.get_line_number(source_code, node),
                    source_code[node.start_byte : node.end_byte]
                    .split("=")[0]
                    .strip()
                    .split(" ")[-1],
                    "source",
                )
                sources.append(v)
        pass
    return sources
from tree_sitter import Node

from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def find_ci_sink(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    """

    # TODO: fill the node type here to filter nodes that contain the source
    nodes = TSUtils.find_nodes_by_type(root_node, "method_invocation")

    sink_nodes = []
    for node in nodes:
        # TODO: fill the condition here to filter nodes that contain the source
        # Please use `source_code[child.start_byte:child.end_byte]` to get the text of a node
        if "exec" in source_code[node.start_byte:node.end_byte]:
            sink_nodes.append(node)

    sinks = []

    def extract_sinks(node: Node) -> list[DFValue]:
        sink_values = []
        # Extract sinks from the given node.
        # Below are several utility functions that may be useful:
        # - To extract a list of arguments from a method invocation node, use TSUtils.get_argument_list(node).
        # Each of the sink nodes should be a tuple (line number, sink variable name, "sink").
        line_number = TSUtils.get_line_number(source_code, node)
        arguments = TSUtils.get_argument_list(node)
        for arg in arguments:
            sink_values.append((line_number, source_code[arg.start_byte:arg.end_byte], "sink"))
        return sink_values

    for node in sink_nodes:
        sinks.extend(extract_sinks(node))

    return sinks
