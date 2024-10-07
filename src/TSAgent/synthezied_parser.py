from typing import List
from TSAgent.TS_analyzer import TSAnalyzer
import tree_sitter
from tree_sitter import Node
from utility.function import *


def find_xss_src(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
    def is_interesting(node: Node) -> bool:
        interesting_identifiers = [
            "readLine",
            "executeQuery",
            "getCookies",
            "getParameter",
            "nextToken",
            "getProperty",
        ]
        if (
            node.type == "identifier"
            and source_code[node.start_byte : node.end_byte] in interesting_identifiers
        ):
            return True
        return False

    def traverse(node: Node, results: List[LocalValue]):
        if is_interesting(node):
            line_number = source_code[: node.start_byte].count("\n") + 1
            name = source_code[node.start_byte : node.end_byte]
            results.append(LocalValue(name, line_number, ValueType.SRC))
            return
        for child in node.children:
            traverse(child, results)

    results = []
    traverse(root_node, results)
    return results
