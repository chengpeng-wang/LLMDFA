from tree_sitter import Node

from TSAgent.synthesis.utils import TSUtils, DFValue, regulate_return_value

DFValue = tuple[int, str, str]


# noinspection PyPep8Naming,PyUnboundLocalVariable
@regulate_return_value
def __T__FN_NAME__T__(source_code: str, root_node: Node) -> list[DFValue]:
    """
    Extract sources from the given code.
    """

    # TODO: fill the node type __NODE_TYPE__ here to filter nodes that contain the source
    nodes = TSUtils.find_nodes_by_type(root_node, __NODE_TYPE__)

    sink_nodes = []
    for node in nodes:
        # TODO: fill the condition __CONDITION__ here to filter nodes that contain the source
        # Please use `source_code[child.start_byte:child.end_byte]` to get the text of a node
        if __CONDITION__:
            sink_nodes.append(node)

    sinks = []

    def extract_sinks(node: Node) -> list[DFValue]:
        sink_values = []
        # TODO: Extract sinks from the given node.
        # Below are several utility functions that may be useful:
        # - To extract a list of arguments from a method invocation node, use TSUtils.get_argument_list(node).
        # - To extract a list of operands from a binary expression node, use TSUtils.get_binary_expression_operands(node).
        # Each of the sink nodes should be a tuple (line number, sink variable name, "sink").
        return sink_values

    for node in sink_nodes:
        sinks.extend(extract_sinks(node))

    return sinks
