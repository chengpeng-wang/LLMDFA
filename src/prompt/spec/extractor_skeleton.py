import sys
from os import path
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from utility.function import *


def find_nodes(root_node: tree_sitter.Node, node_type: str) -> List[tree_sitter.Node]:
    nodes = []
    if root_node.type == node_type:
        nodes.append(root_node)
    for child_node in root_node.children:
        nodes.extend(find_nodes(child_node, node_type))
    return nodes


# The skeleton of source extractor
def find_src(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    # Assumption: The sources are all defined by assignments.
    # Two sub-cases: In assignment expressions or in a variable declaration.
    # This assumption should generally hold.

    # Find assignment_expression
    nodes = find_nodes(root_node, "assignment_expression")

    # Find variable_declaration
    nodes.extend(find_nodes(root_node, "variable_declarator"))

    # Extract the name info and line number
    srcs = []
    for node in nodes:
        # TODO: Synthesize some code here
        name = ""  # Check the oracle I
        line_number = -1  # Check the oracle II

        node_str = source_code[node.start_byte : node.end_byte]
        srcs.append(LocalValue(name, line_number, ValueType.SRC))
    return srcs


# The skeleton of sink extractor
def find_sink(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    nodes = find_nodes(root_node, "****")  # TODO: Synthesize some code here
    sinks = []
    for node in nodes:
        # TODO: Synthesize some code here
        name = ""  # Check the oracle I
        line_number = -1  # Check the oracle II

        node_str = source_code[node.start_byte : node.end_byte]
        sinks.append(LocalValue(name, line_number, ValueType.SINK))
    return sinks
