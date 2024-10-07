from TSAgent.synthesis.utils import SynSpec
from TSAgent.synthesis.templates import gen_skeleton

system_role = """
You are an experienced developer familiar with the tree-sitter AST structures and
know how to write a parser for tree-sitter AST to extract specific nodes.
"""

utilities = """
`TSUtils` provides several utility functions to help you extract sources and sinks from the given code.
- To get the line number of a node, use `TSUtils.get_line_number(source_code: str, node: Node) -> int`.
- To get the list of arguments from a function call, use `TSUtils.get_argument_list(node: Node) -> list[Node]`.
- To get the list of operands from a binary expression, use `TSUtils.get_binary_expression_operands(node: Node) -> list[Node]`.
- To find a node with the given type in the children of one node recursively, use `TSUtils.find_nodes_by_type(node: Node, child_node_type: str) -> list[Node]`.
  The `child_node_type` must be one of the node types in the tree-sitter AST.

In addition, here are some useful usage of AST nodes:
- To get the line number of a node, use `source_code[: node.start_byte].count("\\n") + 1`.
- To get the text of a node, use `source_code[node.start_byte: node.end_byte]`.
"""

ast_usage = """
In the following are some useful usage of AST trees:
Given the following code and AST tree:
```
int x = 0;
```
```
[local_variable_declaration] 'int x = 0;'
  [integral_type] 'int'
    [int] 'int'
  [variable_declarator] 'x = 0'
    [identifier] 'x'
    [=] '='
    [decimal_integer_literal] '0'
  [;] ';'
```
The root node is of type `local_variable_declaration`, and it has 3 children of the following type: `integral_type`, `variable_declarator`, and `;`.
In other to get all the children node of a type, say `decimal_integer_literal`, you can use `TSUtils.find_nodes_by_type(root_node, "decimal_integer_literal")`,
which returns a list of child nodes of type `decimal_integer_literal`. Such child nodes may or may not be direct children of the root node.
To get the text of a node, say the node with type `variable_declarator`, you can use `source_code[node.start_byte: node.end_byte]`.
In this example, the text of `variable_declarator` node is `x = 0`.

If the task is to find an identifier in the source code whose name is `x`, you can use the following code:
```
children = TSUtils.find_nodes_by_type(root_node, 'identifier')
for child in children:
    if source_code[child.start_byte: child.end_byte] == 'x':
        # do something
```
"""


def synthesize_task(spec: SynSpec) -> str:
    return f"""
Please synthesize a tree-sitter parser in Python to extract {spec.df_type} from java code {spec.df_type} from the AST of java code.

The rules of the {spec.df_type} are as follows:
{spec.rules}

Here's a list of examples of {spec.df_type}:
{spec.get_example_prompt()}

Please synthesize the tree-sitter AST parser that considering the structure and node information in the above code examples,
based on the following skeleton of a tree-sitter AST parser. You should focus on filling the placeholders in the template
according to the instructions in the TODO comments.
```python
{gen_skeleton(spec)}
```
Please directly output code without any other description.
In the code, please output the `{spec.fn_name}` function only.
"""


def refine_task(spec: SynSpec, feedback, script: str = None) -> str:
    return f"""
{"Given the following script:" if script else ""}
{script if script else ""}

{feedback.get_prompt()}

The rules of the {spec.df_type} are as follows:
{spec.rules}

Please synthesize the tree-sitter AST parser that considering the structure and node information in the above code examples,
based on the following skeleton of a tree-sitter AST parser. You should focus on filling the placeholders in the template
according to the instructions in the TODO comments.
Please only output the synthesized parser and output the `{spec.fn_name}` function only..
```python
{gen_skeleton(spec)}
```
"""
