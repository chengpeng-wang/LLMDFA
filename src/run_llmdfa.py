import concurrent.futures
import shutil
import argparse
import os
import re
import time
from engine.DFA import DFA
from typing import List
from pathlib import Path
from typing import Tuple
import json
from datetime import datetime
import multiprocessing


def transform_function_split_cluster_files(file_cluster: List[str]) -> None:
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

    new_file_path = main_file.replace(".java", "")[0:-1] + ".java"
    new_lines = file_lines_dic[main_file][:-1]
    for file_path in file_lines_dic:
        if file_path == main_file:
            continue
        new_lines.extend(file_lines_dic[file_path])
    new_lines.append("}")
    with open(new_file_path, "w") as file:
        for new_line in new_lines:
            file.write(new_line)
    return


def transform_class_split_cluster_files(file_cluster: List[str]) -> None:
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
                    transformed_line = "    "
                    transformed_line += " ".join(split_tokens)
                else:
                    transformed_line = line
                transformed_lines.append(transformed_line)
        file_lines_dic[file_path] = transformed_lines

    new_file_path = main_file.replace(".java", "")[0:-1] + ".java"
    new_lines = file_lines_dic[main_file][:-1]
    for file_path in file_lines_dic:
        if file_path == main_file:
            continue
        new_lines.extend(file_lines_dic[file_path])
    new_lines.append("}")
    with open(new_file_path, "w") as file:
        for new_line in new_lines:
            file.write(new_line)
    return


class BatchRun:
    def __init__(
        self,
        src_spec_file: str,
        sink_spec_file: str,
        propagator_spec_file: str,
        validator_spec_file: str,
        project_name: str,
        online_model_name: str,
        is_syn_parser: bool,
        is_fscot: bool,
        is_syn_solver: bool,
        solving_refine_number: int,
        temp: float,
        model_key: str,
        analysis_mode: str,
    ):
        self.src_spec_file = src_spec_file
        self.sink_spec_file = sink_spec_file
        self.propagator_spec_file = propagator_spec_file
        self.validator_spec_file = validator_spec_file
        self.bug_type = project_name
        self.project_name = project_name
        self.simplified_project_name = self.project_name + "_simplified"
        self.all_java_files = []
        self.analyzed_java_files = []
        self.all_single_files = []
        self.analysis_mode = analysis_mode

        self.online_model_name = online_model_name

        self.is_syn_parser = is_syn_parser
        self.is_fscot = is_fscot
        self.is_syn_solver = is_syn_solver
        self.solving_refine_number = solving_refine_number
        self.total_time = 0

        self.batch_run_statistics = {}
        self.temp = temp
        self.model_key = model_key
        return

    def batch_transform_projects(self, main_test: str) -> None:
        cwd = Path(__file__).resolve().parent.parent.absolute()
        full_project_name = cwd / "benchmark" / self.project_name
        new_full_project_name = cwd / "benchmark" / self.simplified_project_name

        if os.path.exists(new_full_project_name):
            shutil.rmtree(new_full_project_name)
        shutil.copytree(full_project_name, new_full_project_name)

        cluster_list = []
        history = set([])
        for root, dirs, files in os.walk(new_full_project_name):
            for file in files:
                if file.endswith(".java") and file.startswith("CWE"):
                    if not re.search(r"_\d+[a-z]$", file.replace(".java", "")):
                        continue
                    file_path = os.path.join(root, file)
                    match_str = file.replace(".java", "")[0:-1]
                    if file_path in history:
                        continue
                    cluster = []
                    cluster.append(file_path)
                    history.add(file_path)

                    for root2, dirs2, files2 in os.walk(new_full_project_name):
                        for file2 in files2:
                            if file2 in history or "_base.java" in file2:
                                continue
                            full_path2 = os.path.join(root2, file2)
                            if file2.startswith(match_str) and (
                                full_path2 not in history
                            ):
                                cluster.append(full_path2)
                                history.add(full_path2)
                    cluster_list.append(cluster)
        for file_cluster in cluster_list:
            is_class_split = True
            for file_path in file_cluster:
                trim_file_path = file_path.replace(".java", "")
                if not re.search(r"_\d+[a-z]$", trim_file_path):
                    is_class_split = False
            if is_class_split:
                transform_class_split_cluster_files(file_cluster)
            else:
                transform_function_split_cluster_files(file_cluster)

        for root, dirs, files in os.walk(new_full_project_name):
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
        return

    @staticmethod
    def is_labeled(function_str: str, line_number: int, file_name: str):
        split_strs = function_str.split("\n")
        line_number -= 1 # index start by 0
        line_number = min(len(split_strs) - 1, line_number)

        if "XSS" in file_name and (
            "getCookies" in file_name or "Servlet_database" in file_name
        ):
            line_number = min(line_number + 4, len(split_strs) - 1)

        while True:
            if "CWE" in split_strs[line_number]:
                return True
            if "POTENTIAL FLAW:" in split_strs[line_number]:
                return True
            if (
                "FIX:" in split_strs[line_number]
                or "INCIDENTAL:" in split_strs[line_number]
            ):
                break
            line_number = line_number - 1
            if line_number == 0:
                break
        return False

    @staticmethod
    def examineBugReport(DFAEngine: DFA) -> Tuple:
        positive_num = 1
        negative_num = 0

        results = {"TPs": 0, "FPs": 0}

        for function_id in DFAEngine.environment.analyzed_functions:
            name = DFAEngine.environment.analyzed_functions[function_id].function_name
            if name == "good":
                negative_num += len(
                    DFAEngine.environment.analyzed_functions[
                        function_id
                    ].line_to_call_site_info
                )

        reports = DFAEngine.bug_reports
        TPs = []
        FPs = []
        for function_src_id in reports:
            for bug_trace in reports[function_src_id]:
                isFP = False
                for function_id, local_value in bug_trace:
                    function_name = DFAEngine.environment.analyzed_functions[
                        function_id
                    ].function_name
                    if "Good" in function_name or "good" in function_name:
                        FPs.append(bug_trace)
                        isFP = True
                        break
                if not isFP:
                    (function_id_start, local_value_start) = bug_trace[0]
                    (function_id_end, local_value_end) = bug_trace[-1]
                    start_function = DFAEngine.environment.analyzed_functions[
                        function_id_start
                    ].original_function
                    end_function = DFAEngine.environment.analyzed_functions[
                        function_id_end
                    ].original_function

                    if (
                        BatchRun.is_labeled(
                            start_function,
                            local_value_start.line_number,
                            DFAEngine.java_file_path,
                        )
                        and BatchRun.is_labeled(
                            end_function,
                            local_value_end.line_number,
                            DFAEngine.java_file_path,
                        )
                        and (
                            start_function != end_function
                            or local_value_start.line_number
                            != local_value_end.line_number
                        )
                    ):
                        TPs.append(bug_trace)
                    else:
                        FPs.append(bug_trace)
            results = {"TPs": len(TPs), "FPs": len(FPs)}
        return results, positive_num, negative_num

    def startBatchRun(self, main_test: str) -> None:
        self.batch_transform_projects(main_test)
        total_input_token_cost = 0
        total_output_token_cost = 0
        analysis_result = {}

        DFA_num = 1

        log_dir_name = ""
        if self.is_syn_parser:
            log_dir_name += "synparser"
        else:
            log_dir_name += "nosynparser"
        log_dir_name += "_"
        if self.is_fscot:
            log_dir_name += "fscot"
        else:
            log_dir_name += "nofscot"
        log_dir_name += "_"
        if self.is_syn_solver:
            log_dir_name += "synsolver"
        else:
            log_dir_name += "nosynsolver"

        base_log_dir_path = str(
            Path(__file__).resolve().parent.parent
            / "log"
            / self.online_model_name
            / log_dir_name
        )

        if not os.path.exists(base_log_dir_path):
            os.makedirs(base_log_dir_path)

        support_files = []
        cwd = Path(__file__).resolve().parent.parent.absolute()
        support_dir = str(
            cwd / "benchmark" / self.simplified_project_name / "testcasesupport"
        )
        for root, dirs, files in os.walk(support_dir):
            for file in files:
                support_files.append(support_dir + "/" + str(file))

        total_results = {}

        # for java_file in self.analyzed_java_files:
        for java_file in self.all_single_files:
            name = java_file[java_file.rfind("/") + 1 :].replace(".java", "")

            DFAEngine = DFA(
                java_file,
                support_files,
                base_log_dir_path,
                self.bug_type,
                self.src_spec_file,
                self.sink_spec_file,
                self.propagator_spec_file,
                self.validator_spec_file,
                self.online_model_name,
                self.is_syn_parser,
                self.is_fscot,
                self.is_syn_solver,
                self.solving_refine_number,
                self.model_key,
                self.temp,
            )

            print(
                "Start to analyze the case ",
                DFA_num,
                "out of ",
                len(self.all_single_files),
            )
            print(java_file)

            start_time = time.time()
            DFAEngine.analyze()
            DFAEngine.validate()
            print("finish validate")
            DFAEngine.report()
            print("finish report")
            end_time = time.time()
            single_time_cost = end_time - start_time

            results, positive_num, negative_num = BatchRun.examineBugReport(DFAEngine)
            input_token_cost, output_token_cost = DFAEngine.compute_total_token_cost()
            total_input_token_cost += input_token_cost
            total_output_token_cost += output_token_cost
            analysis_result = {
                "input_token_cost": input_token_cost,
                "output_token_cost": output_token_cost,
                "analysis_result": results,
                "ground_truth": {"TPs": positive_num, "FPs": negative_num},
                "single time cost": single_time_cost,
            }

            proj_path = java_file[java_file.rfind("/") + 1 : java_file.rfind(".java")]
            single_log_dir_path = str(
                base_log_dir_path + "/" + proj_path.split("/")[-1]
            )
            with open(single_log_dir_path + "/report_summary.json", "w") as file:
                json.dump(analysis_result, file, indent=4)

            total_results = {"TPs": 0, "FPs": 0}
            total_results["TPs"] += results["TPs"]
            total_results["FPs"] += results["FPs"]

            print("===================================================")
            print(DFA_num, " / ", len(self.all_single_files), "\n")
            print(name, "\n")
            print(analysis_result, "\n")
            print("===================================================")
            print("\n")

            DFA_num += 1

            if DFA_num > 10 and self.analysis_mode == "single":
                break

        return


def run():
    """
    Run the LLMDFA analysis with specified parameters.
    """
    models = ["gpt-3.5-turbo", "gpt-4-turbo", "gpt-4o-mini"]

    bug_type_mapping = {
        "dbz": (
            "juliet-test-suite-DBZ",
            "CWE369_Divide_by_Zero__float_random_divide",
            "spec/dbz_source.json",
            "spec/dbz_sink.json",
            "flow/eq_flow_propagator.json",
            "flow/eq_flow_validator.json",
        ),
        "xss": (
            "juliet-test-suite-XSS",
            "CWE80_XSS__CWE182_Servlet_connect_tcp",
            "spec/xss_source.json",
            "spec/xss_sink.json",
            "flow/dep_flow_propagator.json",
            "flow/dep_flow_validator.json",
        ),
        "osci": (
            "juliet-test-suite-CI",
            "CWE78_OS_Command_Injection__connect_tcp",
            "spec/ci_source.json",
            "spec/ci_sink.json",
            "flow/dep_flow_propagator.json",
            "flow/dep_flow_validator.json",
        ),
    }

    parser = argparse.ArgumentParser(
        description="Run LLMDFA analysis on Java projects."
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
        "-syn-parser", action="store_true", help="Enable or disable syntax parser."
    )
    parser.add_argument("-fscot", action="store_true", help="Enable or disable FSCOT.")
    parser.add_argument(
        "-syn-solver", action="store_true", help="Enable or disable syntax solver."
    )
    parser.add_argument(
        "--solving-refine-number",
        type=int,
        default=1,
        help="Number of solving refine iterations.",
    )
    parser.add_argument(
        "--analysis-mode",
        choices=["all", "single"],
        help="Analyze all the subjects or a single demo",
    )

    args = parser.parse_args()

    online_model_name = args.model_name
    bug_type, main_test, src_spec, sink_spec, propagator_spec, validator_spec = (
        bug_type_mapping[args.bug_type]
    )
    project_name = bug_type

    tokenkeys = os.environ.get("OPENAI_API_KEY").split(":")

    batch_run = BatchRun(
        src_spec,
        sink_spec,
        propagator_spec,
        validator_spec,
        project_name,
        online_model_name,
        args.syn_parser,
        args.fscot,
        args.syn_solver,
        args.solving_refine_number,
        0,
        tokenkeys[0],
        args.analysis_mode,
    )
    batch_run.startBatchRun(main_test)


if __name__ == "__main__":
    run()
