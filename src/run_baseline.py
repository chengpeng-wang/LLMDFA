import concurrent.futures
import argparse
import sys
import shutil
import json
import os
import re
from typing import List
from pathlib import Path
from datetime import datetime
import openai
import tree_sitter

from utility.online_model import OnlineModel
from utility.llm import LLM

# Set up paths and language parser
cwd = Path(__file__).resolve().parent.absolute()
TSPATH = cwd.parent / "lib/build/"
language_path = TSPATH / "my-languages.so"

JAVA_LANGUAGE = tree_sitter.Language(str(language_path), "java")

parser = tree_sitter.Parser()
parser.set_language(JAVA_LANGUAGE)


def transform_function_split_cluster_files(file_cluster: List[str]) -> None:
    """
    Transforms function split cluster files by modifying their content based on specific rules.
    """
    file_lines_dic = {}
    main_file = None

    for file_path in file_cluster:
        is_main_class = False
        trim_file_path = file_path.replace(".java", "")
        if trim_file_path.endswith("a"):
            main_file = file_path
            is_main_class = True

        with open(file_path, "r") as file:
            lines = file.readlines()

        transformed_lines = []
        if is_main_class:
            for line in lines:
                if "action(" in line:
                    prev_line = transformed_lines.pop()
                    function_name = prev_line[
                        prev_line.rfind("new ") + 4 : prev_line.rfind("(")
                    ]
                    para = line[line.rfind("(") : line.rfind(")") + 1]
                    whitespace_count = len(line) - len(line.lstrip())
                    new_line = " " * whitespace_count + function_name + para + ";\n"
                    transformed_lines.append(new_line)
                else:
                    transformed_lines.append(line)
        else:
            class_name = ""
            for line in lines:
                if " class " in line:
                    class_name = line.lstrip(" ").split(" ")[2]
                    continue
                if not line.startswith("    "):
                    continue
                if line.startswith("    public"):
                    transformed_line = line.replace("action", class_name)
                else:
                    transformed_line = line
                transformed_lines.append(transformed_line)
        file_lines_dic[file_path] = transformed_lines

    new_file_path = main_file.replace(".java", "")[:-1] + ".java"
    new_lines = file_lines_dic[main_file][:-1]
    for file_path in file_lines_dic:
        if file_path == main_file:
            continue
        new_lines.extend(file_lines_dic[file_path])
    new_lines.append("}")

    with open(new_file_path, "w") as file:
        file.writelines(new_lines)


def transform_class_split_cluster_files(file_cluster: List[str]) -> None:
    """
    Transforms class split cluster files by modifying their content based on specific rules.
    """
    file_lines_dic = {}
    main_file = None

    for file_path in file_cluster:
        is_main_class = False
        trim_file_path = file_path.replace(".java", "")
        if trim_file_path.endswith("a"):
            main_file = file_path
            is_main_class = True

        with open(file_path, "r") as file:
            lines = file.readlines()

        transformed_lines = []
        if is_main_class:
            for line in lines:
                if "(new CWE" in line:
                    transformed_line = line.replace("(new ", "").replace("()).", "_")
                else:
                    transformed_line = line
                transformed_lines.append(transformed_line)
        else:
            for line in lines:
                if not line.startswith("    "):
                    continue
                if "(new CWE" in line:
                    transformed_line = line.replace("(new ", "").replace("()).", "_")
                elif line.startswith("    public "):
                    split_tokens = line.replace("    ", "").split(" ")
                    class_name = file_path[file_path.rfind("/") + 1 :].replace(
                        ".java", ""
                    )
                    split_tokens[2] = class_name + "_" + split_tokens[2]
                    transformed_line = "    " + " ".join(split_tokens)
                else:
                    transformed_line = line
                transformed_lines.append(transformed_line)
        file_lines_dic[file_path] = transformed_lines

    new_file_path = main_file.replace(".java", "")[:-1] + ".java"
    new_lines = file_lines_dic[main_file][:-1]
    for file_path in file_lines_dic:
        if file_path == main_file:
            continue
        new_lines.extend(file_lines_dic[file_path])
    new_lines.append("}")

    with open(new_file_path, "w") as file:
        file.writelines(new_lines)


class BaselineRun:
    """
    Class to handle the baseline run for transforming and analyzing Java projects.
    """

    def __init__(
        self,
        spec_file: str,
        project_name: str,
        model_name: str,
        key_str: str,
        mode: str,
    ):
        self.spec_file = spec_file
        self.project_name = project_name
        self.simplified_project_name = f"{self.project_name}_simplified"
        self.all_java_files = []
        self.analyzed_java_files = []
        self.all_single_files = []

        self.model_name = model_name
        self.key_str = key_str
        self.mode = mode

        self.online_model_name = model_name
        self.model = LLM(self.online_model_name, key_str, 0)
        self.batch_run_statistics = {}

    def batch_transform_projects(self, main_test: str) -> None:
        """
        Transforms and prepares Java projects for analysis.
        """
        cwd = Path(__file__).resolve().parent.parent.absolute()
        full_project_name = cwd / "benchmark" / self.project_name
        new_full_project_name = cwd / "benchmark" / self.simplified_project_name

        if os.path.exists(new_full_project_name):
            shutil.rmtree(new_full_project_name)
        shutil.copytree(full_project_name, new_full_project_name)

        cluster_list = []
        history = set()

        for root, _, files in os.walk(new_full_project_name):
            for file in files:
                if file.endswith(".java") and file.startswith("CWE"):
                    if not re.search(r"_\d+[a-z]$", file.replace(".java", "")):
                        continue
                    file_path = os.path.join(root, file)
                    match_str = file.replace(".java", "")[:-1]
                    if file_path in history:
                        continue
                    cluster = [file_path]
                    history.add(file_path)

                    for root2, _, files2 in os.walk(new_full_project_name):
                        for file2 in files2:
                            if file2 in history or "_base.java" in file2:
                                continue
                            full_path2 = os.path.join(root2, file2)
                            if (
                                file2.startswith(match_str)
                                and full_path2 not in history
                            ):
                                cluster.append(full_path2)
                                history.add(full_path2)
                    cluster_list.append(cluster)

        for file_cluster in cluster_list:
            is_class_split = all(
                re.search(r"_\d+[a-z]$", file_path.replace(".java", ""))
                for file_path in file_cluster
            )
            if is_class_split:
                transform_class_split_cluster_files(file_cluster)
            else:
                transform_function_split_cluster_files(file_cluster)

        for root, _, files in os.walk(new_full_project_name):
            for file in files:
                if file.endswith(".java") and file.startswith("CWE"):
                    if re.search(r"_\d+$", file.replace(".java", "")):
                        self.all_java_files.append(os.path.join(root, file))

        # Select typical test cases for analysis
        for full_java_file_path in self.all_java_files:
            if re.search(r"_\d+$", full_java_file_path.replace(".java", "")):
                self.all_single_files.append(full_java_file_path)

            if main_test in full_java_file_path:
                if re.search(r"_\d+$", full_java_file_path.replace(".java", "")):
                    self.analyzed_java_files.append(full_java_file_path)
            else:
                if "_01.java" in full_java_file_path:
                    self.analyzed_java_files.append(full_java_file_path)

    @staticmethod
    def is_labeled(function_str: str, line_number: int) -> bool:
        """
        Checks if a function string is labeled with a potential flaw or fix.
        """
        split_strs = function_str.split("\n")
        line_number = min(len(split_strs) - 1, line_number)
        while 0 <= line_number <= len(split_strs) - 1:
            if "POTENTIAL FLAW:" in split_strs[line_number]:
                return True
            if "FIX:" in split_strs[line_number]:
                return False
            line_number -= 1
        return True

    @staticmethod
    def find_nodes(
        root_node: tree_sitter.Node, node_type: str
    ) -> List[tree_sitter.Node]:
        """
        Finds all nodes of a specific type under the root node.
        """
        nodes = []
        if root_node.type == node_type:
            nodes.append(root_node)

        for child_node in root_node.children:
            nodes.extend(BaselineRun.find_nodes(child_node, node_type))
        return nodes

    @staticmethod
    def delete_comments(source_code: str, root_node: tree_sitter.Node) -> (str, str):
        """
        Deletes comments from the source code and returns the modified code and original code with line numbers.
        """
        nodes = BaselineRun.find_nodes(root_node, "line_comment")
        nodes.extend(BaselineRun.find_nodes(root_node, "block_comment"))
        nodes.extend(BaselineRun.find_nodes(root_node, "javadoc_comment"))

        new_code = source_code

        for node in nodes:
            comment = source_code[node.start_byte : node.end_byte]
            new_code = new_code.replace(comment, "\n" * comment.count("\n"))

        new_code = (
            new_code.replace("good", "foo")
            .replace("bad", "hoo")
            .replace("G2B", "xx")
            .replace("B2G", "yy")
        )

        new_lines = [f"{i+1}  {line}" for i, line in enumerate(new_code.split("\n"))]
        original_lines = [
            f"{i+1} {line}" for i, line in enumerate(source_code.split("\n"))
        ]

        return "\n".join(new_lines), "\n".join(original_lines)

    def start_baseline_run(self, main_test: str) -> None:
        """
        Starts the baseline run for analyzing Java files.
        """
        self.batch_transform_projects(main_test)

        total_cnt = 0
        log_dir_path = Path(__file__).resolve().parent / "../log/baseline/"
        log_dir_path.mkdir(parents=True, exist_ok=True)
        log_dir_path = log_dir_path / self.online_model_name
        log_dir_path.mkdir(parents=True, exist_ok=True)

        existing_files = {
            file.replace(".json", "")
            for root, _, files in os.walk(log_dir_path)
            for file in files
        }

        for java_file in self.all_single_files:
            name = java_file[java_file.rfind("/") + 1 :].replace(".java", "")
            if main_test not in name or name in existing_files:
                continue
            print(java_file)

            total_cnt += 1

            if total_cnt > 1 and self.mode == "single":
                break

            analyze_content = ""

            with open(java_file, "r") as file:
                source_code = file.read()
                t = parser.parse(bytes(source_code, "utf8"))
                new_code, original_code = BaselineRun.delete_comments(
                    source_code, t.root_node
                )

                analyze_content += (
                    f"Here is the java file {java_file}\n```\n{new_code}\n```\n\n"
                )

                with open(
                    Path(__file__).resolve().parent / "prompt" / self.spec_file, "r"
                ) as read_file:
                    dbz_spec = json.load(read_file)

                message = (
                    dbz_spec["task"]
                    + "\n"
                    + "\n".join(dbz_spec["analysis_rules"])
                    + "\n"
                    + "\n".join(dbz_spec["analysis_examples"])
                    + "\n"
                    + "\n".join(dbz_spec["meta_prompts"])
                    + "\n"
                    + "\n".join(dbz_spec["output_constraints"])
                    + "\n"
                    + "\n".join(dbz_spec["output_examples"])
                    + "\n"
                ).replace("<PROGRAM>", new_code)
                print(message)

                input_token_cost = 0
                output_token_cost = 0

                output, input_token_cost, output_token_cost = self.model.infer(
                    message, True
                )

                print(output)

                print("------------------------------")
                print("Analyzed code:")
                print("------------------------------")
                print(new_code)
                print("------------------------------")
                print("Original code:")
                print("------------------------------")
                print(original_code)
                print("------------------------------")
                print("Output code:")
                print("------------------------------")
                print(output)
                print("------------------------------")
                print("input token cost:", input_token_cost)
                print("output token cost:", output_token_cost)
                print("------------------------------")

                output_results = {
                    "original code": original_code,
                    "new code": new_code,
                    "response": output,
                    "input_token_cost": input_token_cost,
                    "output_token_cost": output_token_cost,
                }

                with open(log_dir_path / f"{name}.json", "w") as file:
                    json.dump({"response": output_results}, file, indent=4)


def run():
    """
    Run the baseline analysis with specified parameters.
    """
    models = ["gpt-3.5-turbo", "gpt-4-turbo"]

    bug_type_mapping = {
        "dbz": (
            "juliet-test-suite-DBZ",
            "CWE369_Divide_by_Zero__float_random_divide",
            "baseline/dbz.json",
        ),
        "xss": (
            "juliet-test-suite-XSS",
            "CWE80_XSS__CWE182_Servlet_database",
            "baseline/xss.json",
        ),
        "osci": (
            "juliet-test-suite-CI",
            "CWE78_OS_Command_Injection__connect_tcp",
            "baseline/ci.json",
        ),
    }

    modes = ["single", "all"]

    parser = argparse.ArgumentParser(
        description="Run baseline analysis on Java projects."
    )
    parser.add_argument(
        "--model-name",
        choices=models,
        required=True,
        help="The model name to use for analysis.",
    )
    parser.add_argument(
        "--bug-type",
        choices=bug_type_mapping.keys(),
        required=True,
        help="The type of bug to analyze (dbz, xss, osci).",
    )
    parser.add_argument(
        "--mode",
        choices=modes,
        required=True,
        help="The type of bug to analyze (dbz, xss, osci).",
    )

    args = parser.parse_args()

    online_model_name = args.model_name
    bug_type, main_test, spec = bug_type_mapping[args.bug_type]
    mode = args.mode
    project_name = bug_type

    keys = os.environ.get("OPENAI_API_KEY").split(":")
    openai.api_key = keys[0]
    baseline_run = BaselineRun(spec, project_name, online_model_name, keys[0], mode)
    baseline_run.start_baseline_run(main_test)


if __name__ == "__main__":
    run()
