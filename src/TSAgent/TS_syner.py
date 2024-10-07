import sys
from os import path
import re
from typing import Literal

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from TSAgent.TS_parser import TSParser
from LMAgent.LM_agent import *
from config.config import *
from utility.online_model import *
from utility.function import *
from utility.logger import *
import importlib


def get_prompts(
    fn_name: str, source_or_sink: Literal["source"] | Literal["sink"]
) -> Dict:
    prompts = {
        "model_role_name": "Tree-sitter AST node extractor code synthesizer",
        "user_role_name": "Code synthesizer",
        "system_role": f"You are a python developer who is writing a tree-sitter AST parser to extract the AST nodes that may be data flow {source_or_sink}s in java source code.",
        "task": f"Please write a program using the given tree-sitter AST parser template to extract the AST nodes that may be data flow {source_or_sink}s.",
        "template": [
            f"""def {fn_name}(source_code: str, root_node: tree_sitter.Node) -> List[LocalValue]:
                def is_interesting(node: Node) -> bool:
                    # fill this function
                    pass

                def traverse(node: Node, results: List[LocalValue]):
                    if is_interesting(node):
                        line_number = source_code[: node.start_byte].count("\n") + 1
                        name = source_code[node.start_byte : node.end_byte]
                        results.append(LocalValue(name, line_number, ValueType.{'SRC' if source_or_sink == 'source' else 'SINK'}))
                        return
                    for child in node.children:
                        traverse(child, results)

                results = []
                traverse(root_node, results)
                return results

            """
        ],
        "input_description": [
            "The first argument `source_code` is the original source code of the program.",
            "The second argument `root_node` is the root node of the tree-sitter AST of the program.",
        ],
        "output_description": [
            "The return value is a list of `LocalValue` objects.",
            f"The `LocalValue` object represent a value on the AST tree that may be a data flow {source_or_sink}.",
        ],
        "utility_functions": [
            "LocalValue is a python class whose constructor takes three arguments:",
            f"- `name`: the name of the {source_or_sink} value in the source code",
            f"- `line_number`: the line number of the {source_or_sink} value in the source code",
            f"- `v_type`: the type of the {source_or_sink} value, which is one of `ValueType` enum values, which should always be set as `{'ValueType.SRC' if source_or_sink == 'source' else 'ValueType.SINK'}` for this task",
            "",
            "One class TSAnalyzer (imported as `from TSAgent.TS_analyzer import TSAnalyzer`) contains a static utility function `find_nodes`, which recursively find all nodes with a given AST node type in a tree-sitter AST tree.",
            "Function `TSAnalyzer.find_nodes` takes two arguments:",
            "- `root_node`: the root node of the tree-sitter AST of the program",
            "- `node_type`: the AST node type to be found. The value should be one of the node types specified by tree-sitter.",
            "",
            "Note that each AST node has `start_byte` and `end_byte` attributes, denoting the starting and ending byte offsets of the code of the AST node.",
            "Name of a value in the source code can be obtained by `source_code[node.start_byte:node.end_byte]`.",
            "Line number of a value in the source code can be obtained by `source_code[:node.start_byte].count('\\n') + 1`.",
        ],
    }
    return prompts


class TSExtractorSynthesizer(LMAgent):
    """
    TSExtractorSynthesizer class for synthesizing a tree-sitter AST parser to extract nodes
    given rules or input output examples.
    """

    def __init__(
        self,
        model: str = "gpt-3.5-turbo-1106",
        fn_name: str = "find_in_ast",
        source_or_sink: Literal["source"] | Literal["sink"] = "source",
        analysis_rules: List[str] = [],
    ) -> None:
        super().__init__()
        self.source_or_sink = source_or_sink
        self.fn_name = fn_name
        self.prompts = get_prompts(fn_name, source_or_sink)
        self.prompts["analysis_rules"] = analysis_rules
        self.system_role = self.prompts["system_role"]
        self.model = OnlineModel(model, self.system_role, keys[0], 0.1)

    def construct_synthesize_code_snippet_prompt(self) -> Tuple[str, str]:
        """
        Construct the prompt to synthesize a code snippet that help generate a example AST tree.
        :param config_file_path: The file path of prompt config file
        :return: The system role description and prompt
        """
        system_role = self.prompts["system_role"]
        prompt = self.prompts["task"] + "\n"
        prompt += "\n".join(self.prompts["analysis_rules"])
        prompt += "Please generate a java code snippet containing the example code that covers all distinct characteristics described in the aforementioned rules.\n"
        prompt += "Please also include some conterexamples that do not have the aforementioned characteristics in the code.\n"
        prompt += "Please only generate the java code snippet without any other description.\n"
        prompt += f"Please add `// interesting` at the end of lines to indicate this line contains {self.source_or_sink}.\n"
        prompt += f"Similarly, please add `// not interesting` at the end of lines to indicate this line does not contain {self.source_or_sink}.\n"
        prompt += "Not all lines need to be labeled.\n"
        return system_role, prompt

    def construct_synthesize_parser_prompt(
        self, code_snippet: str, ast: str
    ) -> Tuple[str, str]:
        message = "Below is a java code and its corresponding tree-sitter AST tree in the tree-sitter's sexp format.\n"
        message += "The java code is:\n```\n" + code_snippet + "\n```\n"
        message += f"The lines that contains {self.source_or_sink} are labeled with `// interesting`.\n"
        message += f"The lines that do not contain {self.source_or_sink} are labeled with `// not interesting`.\n"
        message += "The corresponding AST tree is:\n```\n" + ast + "\n```\n"
        message += "The AST tree presents the tree structure in which each line is a node in the tree and the indentation indicates the parent-child relationship. Children of a node are printed in order, starting from index 0. The node is represented as `index [type] 'text'`, where index is the child index of current node in its parent node, type is the node type of the current node, and text is the string text of the node.\n"
        message += "Please synthesize the tree-sitter AST parser that considering the structure and node information in this code snippet example.\n"  # You may use node.children[index] to access the child of one node. If you want to get the method_name node of a method_invocation, you can use node.children[2] to get the node containing the method name. You can also use `source_code[node.children[2].start_byte:node.children[2].end_byte]`to get the text of the method name. \n"
        message += "You need to recursively search all nodes in the AST tree from the root node.\n"
        message += f"The template of the function to synthesize is as follows: \n```\n{ self.prompts['template']}```\n"
        message += "\n".join(self.prompts["input_description"]) + "\n"
        message += "\n".join(self.prompts["output_description"]) + "\n"
        message += "\n".join(self.prompts["utility_functions"]) + "\n"
        message += f"Please directly output code without any other description. In the code, please output the `{self.fn_name}` function only.\n"
        return message

    def synthesize_code_snippet(self, logger: Logger) -> Tuple[str, list]:
        """
        :return: The synthesized code snippet and the conversation history
        """
        _, prompt = self.construct_synthesize_code_snippet_prompt()
        input = [
            {"role": "system", "content": self.system_role},
            {"role": "user", "content": prompt},
        ]
        (response, _, _) = self.model.infer(logger=logger, input=input)
        logger.logging(prompt, response)
        response = re.sub(r"```[a-z]*", "", response)
        history = input + [
            {"role": "assistant", "content": self.system_role},
        ]
        return response, history

    def find_groud_truth(self, code_snippet: str) -> Tuple[List[int], List[int]]:
        """
        Find the line number of interesting and not interesting lines in the code snippet.
        """
        lines = code_snippet.split("\n")
        interesting_lines = []
        not_interesting_lines = []
        for i, line in enumerate(lines):
            if "// interesting" in line:
                interesting_lines.append(i + 1)
            if "// not interesting" in line:
                not_interesting_lines.append(i + 1)
        return interesting_lines, not_interesting_lines

    def evaluate_parser(
        self,
        parser: str,
        code: str,
        root_node: tree_sitter.Node,
        interesting_lines: List[int],
        not_interesting_lines: List[int],
    ) -> str:
        """
        Evaluate the parser on the code snippet.
        Returns the feedback text for LLM reflexion.
        Returns empty string if the parser is correct.
        """
        fn_lines = []
        in_fn = False
        for line in parser.split("\n"):
            if line.startswith(f"def {self.fn_name}"):
                in_fn = True
                fn_lines.append(line)
            elif len(line.strip()) == 0 or line.startswith("    ") and in_fn:
                fn_lines.append(line)
            else:
                in_fn = False
        fn = "\n".join(fn_lines)

        parent_dir = path.dirname(path.abspath(__file__))
        with open(f"{parent_dir}/synthezied_parser.py", "w") as f:
            f.write(
                """
from typing import List
from TSAgent.TS_analyzer import TSAnalyzer
import tree_sitter
from tree_sitter import Node
from utility.function import *

"""
            )
            f.write(fn)
        try:
            synthesized_parser_module = importlib.import_module(
                "TSAgent.synthezied_parser"
            )
            parser_fn = getattr(synthesized_parser_module, self.fn_name)
        except Exception as e:
            return f"Failed to import the synthesized parser. {e}"

        local_values: List[LocalValue] = parser_fn(code, root_node)
        code_lines = code.split("\n")
        message = ""
        for interesting_line in interesting_lines:
            if interesting_line not in [
                local_value.line_number for local_value in local_values
            ]:
                message += f"Line `{code_lines[interesting_line-1]}` is interesting but the synthesized parser does not find it.\n"
        for value in local_values:
            if value.line_number in not_interesting_lines:
                message += f"Line `{code_lines[value.line_number-1]}` is not interesting but the synthesized parser finds it.\n"
        return message

    def synthesize(self, logger: Logger) -> str:
        code, history = self.synthesize_code_snippet(logger)

        # parse the code as AST
        with open("/tmp/code.java", "w") as f:
            f.write(code)
        parser = TSParser("/tmp/code.java")
        ast = parser.get_pretty_ast("/tmp/code.java")
        tree = parser.get_ast("/tmp/code.java")

        # synthesize the parser
        message = self.construct_synthesize_parser_prompt(code, ast)
        input = history + [
            {"role": "user", "content": message},
        ]
        (response, _, _) = self.model.infer(logger=logger, input=input)
        logger.logging(message, response)
        history = input + [
            {"role": "assistant", "content": response},
        ]
        synthesized_parser = re.sub(r"```[a-z]*", "", response)
        # print("Synthesized parser:\n" + synthesized_parser)

        # evaluate the parser
        interesting_lines, not_interesting_lines = self.find_groud_truth(code)
        for _ in range(1):
            # print("Evaluating the synthesized parser...")
            eval_result = self.evaluate_parser(
                synthesized_parser,
                code,
                tree.root_node,
                interesting_lines,
                not_interesting_lines,
            )
            # print(eval_result)
            if len(eval_result) == 0:
                # success
                return response
            history = history + [
                {
                    "role": "user",
                    "content": f"This is the execution result of the synthesized parser on the example code snippet:\n{eval_result}",
                },
            ]

            # reflexion
            input = history + [
                {
                    "role": "user",
                    "content": f"Please reflect on the execution result of the synthesized parser. What is the problem of the synthesized parser?",
                },
            ]
            (response, _, _) = self.model.infer(logger=logger, input=input)
            logger.logging(eval_result, response)
            input = history + [
                {"role": "assistant", "content": response},
            ]

            # retry
            input = history + [
                {
                    "role": "user",
                    "content": f"lease synthesize the python using the template provided above. Please directly write the code without any other description. In the code, please output the `{self.fn_name}` function only. The template of the function to synthesize is as follows: \n```\n{ self.prompts['template']}```\n",
                },
            ]
            (response, _, _) = self.model.infer(logger=logger, input=input)
            logger.logging("Retry", response)
            history = input + [
                {"role": "assistant", "content": response},
            ]
            # print(response)
            synthesized_parser = re.sub(r"```[a-z]*", "", response)

        return response

    def apply(self, function: Function, logger: Logger) -> Function:
        message = self.prompt + "\n```\n" + function.original_function + "\n```\n"
        new_function = self.model.infer(message, logger)

        # compute the line numbers for the new function
        new_function = new_function.replace("```", "").lstrip("\n").rstrip("\n")
        function_content = "1. " + new_function
        line_no = 2
        lined_new_function = ""
        for ch in function_content:
            if ch == "\n":
                lined_new_function += "\n" + str(line_no) + ". "
                line_no += 1
            else:
                lined_new_function += ch
        function.set_transformed_function(new_function, lined_new_function)
        return function


def syn_dbz_src_parser(logger: Logger) -> str:
    syner = TSExtractorSynthesizer(
        fn_name="find_dbz_src",
        source_or_sink="source",
        analysis_rules=[
            "- Any line that contains a literal `0`, `0.0`, or `0.0f` is a source.",
            "- Any line that contains an identifier `parseInt`, `parseFloat`, `nextInt` or `nextFloat` is a source.",
        ],
    )
    code = syner.synthesize(logger)
    return code


def syn_dbz_sink_parser(logger: Logger) -> str:
    syner = TSExtractorSynthesizer(
        fn_name="find_dbz_sink",
        source_or_sink="sink",
        analysis_rules=[
            "- Any line that contains `/` or `%` is a sink.",
        ],
    )
    code = syner.synthesize(logger)
    return code


def syn_xss_src_parser(logger: Logger) -> str:
    syner = TSExtractorSynthesizer(
        fn_name="find_xss_src",
        source_or_sink="source",
        analysis_rules=[
            "- Any line that contains an identifier named `readLine`, `executeQuery`, `getCookies`, `getParameter`, `nextToken`, or `getProperty` is a source.",
        ],
    )
    code = syner.synthesize(logger)
    return code


def syn_xss_sink_parser(logger: Logger) -> str:
    syner = TSExtractorSynthesizer(
        fn_name="find_xss_sink",
        source_or_sink="sink",
        analysis_rules=[
            "- Any line that contains a identifier `println` is a sink.",
        ],
    )
    code = syner.synthesize(logger)
    return code


if __name__ == "__main__":
    logger = Logger("TSExtractorSynthesizer", 0, 0)
    # code = syn_dbz_src_parser(logger)
    # print(code)
    # code = syn_dbz_sink_parser(logger)
    # print(code)
    code = syn_xss_src_parser(logger)
    print(code)
    # code = syn_xss_sink_parser(logger)
    # print(code)
