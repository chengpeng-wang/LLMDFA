from tree_sitter import Node

from TSAgent.synthesis.utils import *
from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def __T__FN_NAME__T__(source_code: str, root_node: Node) -> list[DFValue]:
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
        nested_children = TSUtils.find_nodes_by_type(node, __NODE_TYPE__)
        nested_children.extend(
            TSUtils.find_nodes_by_type(node, __CHILD_NODE_TYPE_2__)
        )  # you may want to repeat this line for more child node types

        # second check if the child node contains the source
        for child in nested_children:
            # TODO: fill the condition __CONDITION__ on child node here to filter nodes that contain the source
            # Please use `source_code[child.start_byte:child.end_byte]` to get the text of the child node
            if __CONDITION__:
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
