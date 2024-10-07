import sys
from os import path
import json
import subprocess

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from LMAgent.LM_agent import LMAgent
from TSAgent.TS_parser import TSParser
from TSAgent.TS_analyzer import TSAnalyzer
from utility.llm import *
from utility.function import *
from utility.environment import Environment
from typing import List, Tuple, Set


class InterFlowValidator(LMAgent):
    """
    InterFlowValidator class for checking whether given inter-procedural paths are feasible or not
    """

    def __init__(self, file_path: str, online_model_name, openai_key, temp) -> None:
        super().__init__()
        self.ifv_file_path = file_path
        system_role = self.fetch_system_role()
        self.response_location_check = ""
        self.response_path_check = ""
        self.openai_key = openai_key
        self.model = LLM(online_model_name, self.openai_key, temp, system_role)

    def apply(
        self,
        environment: Environment,
        ts_analyzer: TSAnalyzer,
        bug_candidate: List[Tuple[int, LocalValue]],
        bug_name: str,
        solving_refine_number: int = 5,
        is_solver_using: bool = True,
    ) -> bool:
        """
        determine the feasibility of the paths induced by bug candidates
        """
        if is_solver_using:
            print("Applying path checker with solver...")
            is_path_feasible_with_solver = self.apply_path_check_with_solver(
                environment,
                ts_analyzer,
                bug_candidate,
                bug_name,
                solving_refine_number,
            )

            if is_path_feasible_with_solver is not None:
                print("Solver-aided path checker succeeded...")
                return is_path_feasible_with_solver

            print("Solver-aided path checker failed...")
            print("Applying path reachability check with LLM...")
            is_path_feasible = self.apply_reachable_program_path_check_with_LLM(
                environment, ts_analyzer, bug_candidate
            )
            print("LLM-aided path checker succeeded...")
            return is_path_feasible
        else:
            print("Applying path reachability check with LLM...")
            is_path_feasible = self.apply_reachable_program_path_check_with_LLM(
                environment, ts_analyzer, bug_candidate
            )
            print("LLM-aided path checker succeeded...")
            return is_path_feasible

    def apply_path_check_with_solver(
        self,
        environment: Environment,
        ts_analyzer: TSAnalyzer,
        bug_candidate: List[Tuple[int, LocalValue]],
        bug_name: str,
        solving_refine_number: int = 3,
    ):
        """
        Use solver to check the feasibility of the path
        """
        is_uncertain = False
        fact_template = "Assume that the value of the variable `<VAR_1>` at the line <LINE_1> in the function <FUNCTION_1> is <VALUE>"
        message_line_fd_list = []
        val_literal = ""

        for function_id, local_val in bug_candidate:
            message = (
                "Here is the program:\n" + 
                "```\n" +
                environment.analyzed_functions[function_id].lined_SSI_function_without_comments +
                "```\n" +
                "\n"
            )
            if "DBZ" in bug_name:
                val_literal = "0"
                message += (
                    fact_template.replace("<VAR_1>", local_val.name)
                    .replace("<LINE_1>", str(local_val.line_number))
                    .replace(
                        "<FUNCTION_1>",
                        environment.analyzed_functions[function_id].function_name,
                    )
                    .replace("<VALUE>", val_literal)
                ) + "\n"
                message += (
                    "Hence, you should first add a constraint to ensure that "
                    + local_val.name
                    + " = "
                    + val_literal
                    + " is satisfied. \n"
                )
            else:
                message = ""

            ## If-statement
            function = environment.analyzed_functions[function_id]
            line_number = local_val.line_number
            branch_info_str_template = (
                " - The line <CHECK_LINE> in the function <FUNCTION> "
                "is in the <BRANCH_TYPE> branch of the if-statement. "
                "Please notice that the condition of the if-statement is `<CONDITION>` at the line <BR_COND_LINE>."
            )
            branch_info_strs = []

            split_tokens_list = []
            split_tokens_list.append([local_val.name])
            condition_strs = set([])
            for condition_line, if_statement_end_line in function.if_statements:
                (
                    condition_line,
                    condition_str,
                    (true_branch_start_line, true_branch_end_line),
                    (else_branch_start_line, else_branch_end_line),
                ) = function.if_statements[(condition_line, if_statement_end_line)]
                branch_type = ""
                if true_branch_start_line < line_number < true_branch_end_line:
                    branch_type = "true"
                if else_branch_start_line < line_number < else_branch_end_line:
                    branch_type = "else"
                if branch_type == "":
                    continue
                if (condition_str == "(true)" and branch_type == "true") or (
                    condition_str == "(false)" and branch_type == "else"
                ):
                    continue
                if (condition_str == "(true)" and branch_type == "else") or (
                    condition_str == "(false)" and branch_type == "true"
                ):
                    return False
                branch_info_str = (
                    branch_info_str_template.replace("<CHECK_LINE>", str(line_number))
                    .replace("<FUNCTION>", function.function_name)
                    .replace("<BRANCH_TYPE>", branch_type)
                    .replace("<CONDITION>", condition_str)
                    .replace("<BR_COND_LINE>", str(condition_line))
                )
                condition_expr = condition_str.lstrip("(").rstrip(")")

                if branch_type == "true":
                    branch_info_str += (
                        " Hence you need to write a constraint to ensure that "
                        + condition_expr
                        + " is satisified, i.e., "
                        + condition_expr
                        + " is equal to True."
                    )
                elif branch_type == "else":
                    branch_info_str += (
                        " Hence you need to write a constraint to ensure that "
                        + condition_expr
                        + " is NOT satisified, i.e., "
                        + condition_expr
                        + " is equal to False."
                    )
                condition_strs.add(condition_str)
                branch_info_strs.append(branch_info_str)
                split_tokens_list.append(condition_str.split(" "))

            # Switch statement
            switch_info_str_template = (
                " - The line <CHECK_LINE> in the function <FUNCTION> "
                "belongs to the case of the switch statements,"
                "of which the case label is `<LABEL>` and the switch expression is <SWITCH_EXPR> .\n"
            )
            switch_info_strs = []

            split_tokens_list = []
            split_tokens_list.append([local_val.name])
            for (
                switch_statement_start_line,
                switch_statement_end_line,
            ) in function.switch_statements:
                (parenthesized_node_str, items) = function.switch_statements[
                    (switch_statement_start_line, switch_statement_end_line)
                ]
                switch_label = "non_def"
                switch_expr = parenthesized_node_str.lstrip("(").rstrip(")")
                for label_str, case_start_line, case_end_line in items:
                    if case_start_line < line_number < case_end_line:
                        switch_label = label_str
                        break
                if switch_label == "non_def":
                    continue
                if switch_label != "":
                    if switch_expr == switch_label:
                        continue
                    if switch_expr.isdigit() or switch_expr in {"true", "false"}:
                        return False
                    switch_info_str = (
                        switch_info_str_template.replace(
                            "<CHECK_LINE>", str(line_number)
                        )
                        .replace("<FUNCTION>", function.function_name)
                        .replace("<LABEL>", switch_label)
                        .replace("<SWITCH_EXPR>", switch_expr)
                    )
                    switch_info_strs.append(switch_info_str)
                else:
                    for label_str, case_start_line, case_end_line in items:
                        if label_str == "":
                            continue
                        if label_str == switch_expr:
                            return False
                    switch_info_str = (
                        switch_info_str_template.replace(
                            "<CHECK_LINE>", str(line_number)
                        )
                        .replace("<FUNCTION>", function.function_name)
                        .replace("<LABEL>", "default")
                        .replace("<SWITCH_EXPR>", switch_expr)
                    )
                    switch_info_strs.append(switch_info_str)

            # filtering special cases. avoiding exhaustively invoking smt solver.
            if len(branch_info_strs) > 0 or len(switch_info_strs) > 0:
                message += (
                    "We have the following fact for the line "
                    + str(line_number)
                    + ": \n\n"
                )
                message += "\n".join(branch_info_strs) + "\n"
                message += "\n".join(switch_info_strs) + "\n"
            else:
                message += "The line " + str(line_number) + " is not in any branch. \n"
                continue

            global_variable_info = self.extract_global_variable_info(
                environment, ts_analyzer, bug_candidate, condition_strs
            )

            if global_variable_info != "":
                message += global_variable_info
                message += (
                    "\n"
                    + "You should note that not all the global variables can be used in the path condition of the line "
                    + str(line_number)
                    + ".\n"
                )

            # We can assign the priority to the program locations appearing in the path
            # This may result in UNSAT earlier
            freedom_degree = 0
            for i in range(len(split_tokens_list)):
                for j in range(i):
                    for token in split_tokens_list[i]:
                        if token in split_tokens_list[j]:
                            freedom_degree += 1

            # Store message and line_number in a list and sort them according to freedom_degree
            message_line_fd_list.append(
                (message, local_val.line_number, freedom_degree)
            )

        message_line_fd_list.sort()
        sorted_message_line_fd_list = sorted(
            message_line_fd_list, key=lambda x: x[2], reverse=True
        )

        for message, line_number, freedom_degree in sorted_message_line_fd_list:
            # constructing the solving program
            solving_program = self.construct_solving_program(
                line_number, message, val_literal
            )
            run_output = ""

            try:
                # Run the solving program using subprocess
                completed_process = subprocess.run(
                    ["python", "-c", solving_program], capture_output=True, text=True
                )

                # Check if the program executed successfully
                if completed_process.returncode == 0:
                    # Return the console output
                    run_output = completed_process.stdout.strip()
                else:
                    # Return the error output
                    run_output = completed_process.stderr.strip()
            except Exception as e:
                # Handle any exceptions that occur during program execution
                print(f"An error occurred: {str(e)}")
                run_output = completed_process.stdout.strip()

            # refine the solving program until we can obtain SAT or UNSAT as the result
            cnt = 0
            if run_output not in {"SAT", "UNSAT"}:
                while True:
                    cnt += 1
                    if cnt > solving_refine_number:
                        break
                    new_program = self.refine_solving_program(
                        solving_program, run_output
                    )
                    try:
                        # Run the program using subprocess
                        completed_process = subprocess.run(
                            ["python", "-c", new_program],
                            capture_output=True,
                            text=True,
                        )

                        # Check if the program executed successfully
                        if completed_process.returncode == 0:
                            # Return the console output
                            run_output = completed_process.stdout.strip()
                        else:
                            # Return the error output
                            run_output = completed_process.stderr.strip()
                    except Exception as e:
                        # Handle any exceptions that occur during program execution
                        print(f"An error occurred: {str(e)}")
                        run_output = completed_process.stdout.strip()
                    if run_output in {"UNSAT", "SAT"}:
                        break
            if run_output == "UNSAT":
                return False
            if run_output not in {"UNSAT", "SAT"}:
                is_uncertain = True
        if is_uncertain:
            return None
        else:
            return True

    def apply_reachable_program_path_check_with_LLM(
        self,
        environment: Environment,
        ts_analyzer: TSAnalyzer,
        bug_candidate: List[Tuple[int, LocalValue]],
    ) -> bool:
        """
        Determine the feasibility of the path using LLM
        """
        message = self.construct_prompt_for_path_check(
            environment, ts_analyzer, bug_candidate
        )

        while True:

            response, input_token_cost, output_token_cost = self.model.infer(message)
            self.total_input_token_cost += input_token_cost
            self.total_output_token_cost += output_token_cost
            self.response_path_check = response

            yes_no_vector = self.process_yes_no_list_in_response(
                self.response_path_check
            )
            if len(yes_no_vector) == 0:
                continue
            if "Yes" in yes_no_vector[0] or "yes" in yes_no_vector[0]:
                return True
            else:
                return False

    def extract_function_in_trace(
        self, environment: Environment, bug_candidate: List[Tuple[int, LocalValue]]
    ) -> str:
        program_str = ""
        function_ids = set([])
        for function_id, value in bug_candidate:
            if function_id not in function_ids:
                function_ids.add(function_id)
                program_str += (
                    environment.analyzed_functions[
                        function_id
                    ].lined_SSI_function_without_comments
                    + "\n"
                )
        return program_str

    def extract_global_variable_info(
        self,
        environment: Environment,
        ts_analyzer: TSAnalyzer,
        bug_candidate: List[Tuple[int, LocalValue]],
        condition_strs: set[str],
    ) -> str:
        with open(self.prompt_config_file_base / self.ifv_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        global_var_info = "\n".join(dump_config_dict["global_variable_info"])

        fun_history = set([])
        fields_dic = {}
        for function_id, local_value in bug_candidate:
            if function_id in fun_history:
                continue
            fun_history.add(function_id)
            if len(environment.analyzed_functions[function_id].field_inits) > 0:
                for field_id in environment.analyzed_functions[function_id].field_inits:
                    field_init_str = environment.analyzed_functions[
                        function_id
                    ].field_inits[field_id]
                    for condition_str in condition_strs:
                        if field_init_str.split("=")[0].strip() in condition_str:
                            fields_dic[field_id] = environment.analyzed_functions[
                                function_id
                            ].field_inits[field_id]
        static_field_dic = {}
        for condition_str in condition_strs:
            for static_field in ts_analyzer.ts_parser.static_field_info:
                if static_field in condition_str:
                    static_field_dic[static_field] = (
                        ts_analyzer.ts_parser.static_field_info[static_field]
                    )

        if len(fields_dic) == 0 and len(static_field_dic) == 0:
            global_var_info = ""
        else:
            fields_strs = []
            for field_id in fields_dic:
                fields_strs.append(" - " + fields_dic[field_id] + "\n")
            for static_field in static_field_dic:
                fields_strs.append(" - " + static_field_dic[static_field] + "\n")

            global_var_info = global_var_info.replace(
                "<GLOBAL_VAR>", "\n".join(fields_strs)
            )
        return global_var_info

    def construct_prompt_for_path_check(
        self,
        environment: Environment,
        ts_analyzer: TSAnalyzer,
        bug_candidate: List[Tuple[int, LocalValue]],
    ) -> str:
        """
        Construct the prompt for path check using LLMs
        """
        code_str = ""
        function_ids = set([])
        for function_id, value in bug_candidate:
            if function_id not in function_ids:
                function_ids.add(function_id)
                code_str += (
                    environment.analyzed_functions[
                        function_id
                    ].lined_SSI_function_without_comments
                    + "\n"
                )

        with open(self.prompt_config_file_base / self.ifv_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        question_template = dump_config_dict["question_template"]

        path_strs = InterFlowValidator.summarize_path_info(environment, bug_candidate)
        path_str = "```\n" + " --> ".join(path_strs) + "\n```\n"

        (
            branch_info_strs,
            condition_strs,
        ) = InterFlowValidator.summarize_path_branch_info(environment, bug_candidate)

        switch_info_strs = InterFlowValidator.summarize_path_switch_info(
            environment, bug_candidate
        )

        info_str = ""
        if len(branch_info_strs) > 0 or len(switch_info_strs) > 0:
            info_str = (
                "We have several important facts for the lines appearing in the path.\n"
            )
            info_str += "\n".join(branch_info_strs)
            info_str += "\n".join(switch_info_strs)

        (function_id_start, value_start) = bug_candidate[0]
        (function_id_end, value_end) = bug_candidate[-1]
        question = (
            question_template.replace("<VAR_1>", value_start.name)
            .replace("<VAR_2>", value_end.name)
            .replace("<PATH>", path_str)
            .replace("<LINE_1>", str(value_start.line_number))
            .replace(
                "<FUNCTION_1>",
                environment.analyzed_functions[function_id_start].function_name,
            )
            .replace("<LINE_2>", str(value_end.line_number))
            .replace(
                "<FUNCTION_2>",
                environment.analyzed_functions[function_id_end].function_name,
            )
        )

        answer_format = self.fetch_path_check_answer_format()

        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["additional_fact"])
        prompt += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        prompt += "\n" + "".join(dump_config_dict["meta_prompts"])
        prompt = (
            prompt.replace(
                "<PROGRAM>", self.extract_function_in_trace(environment, bug_candidate)
            )
            .replace("<QUESTION>", question)
            .replace(
                "<INIT_GLOBAL_INFO>",
                self.extract_global_variable_info(
                    environment, ts_analyzer, bug_candidate, condition_strs
                ),
            )
            .replace("<ANSWER>", answer_format)
            .replace("<PATH_BRANCH_INFO>", info_str)
        )
        return prompt

    @staticmethod
    def summarize_path_info(
        environment: Environment, bug_candidate: List[Tuple[int, LocalValue]]
    ) -> List[str]:
        path_strs = []
        for i in range(len(bug_candidate)):
            (function_id, local_val) = bug_candidate[i]
            loc_str = (
                "Line "
                + str(local_val.line_number)
                + " in the function "
                + environment.analyzed_functions[function_id].function_name
            )
            path_strs.append(loc_str)
        return path_strs

    @staticmethod
    def summarize_path_branch_info(
        environment: Environment, bug_candidate: List[Tuple[int, LocalValue]]
    ) -> Tuple[List[str], Set[str]]:
        """
        Extract the brnach information of the path for the path feasibility check
        """

        covered_if_statements = {}

        condition_strs = set([])

        for function_id, local_val in bug_candidate:
            function = environment.analyzed_functions[function_id]
            line_number = local_val.line_number

            for condition_line, if_statement_end_line in function.if_statements:
                (
                    condition_line,
                    condition_str,
                    (true_branch_start_line, true_branch_end_line),
                    (else_branch_start_line, else_branch_end_line),
                ) = function.if_statements[(condition_line, if_statement_end_line)]
                branch_type = ""
                if true_branch_start_line < line_number < true_branch_end_line:
                    branch_type = "true"
                if else_branch_start_line < line_number < else_branch_end_line:
                    branch_type = "else"
                if branch_type == "":
                    continue
                if (function_id, line_number) not in covered_if_statements:
                    covered_if_statements[(function_id, line_number)] = []
                covered_if_statements[(function_id, line_number)].append(
                    (condition_line, condition_str, branch_type)
                )
                condition_strs.add(condition_str)

        branch_info_str_template = (
            "    - The line <CHECK_LINE> in the function <FUNCTION> "
            "is in the <BRANCH_TYPE> branch of the if-statement. "
            "of which the branch condition is `<CONDITION>` at the line <BR_COND_LINE>"
        )
        branch_info_strs = []
        for function_id, local_val in bug_candidate:
            function = environment.analyzed_functions[function_id]
            line_number = local_val.line_number
            if (function_id, line_number) in covered_if_statements:
                single_branch_info_strs = []
                for condition_line, condition_str, branch_type in covered_if_statements[
                    (function_id, line_number)
                ]:
                    branch_info_str = (
                        branch_info_str_template.replace(
                            "<CHECK_LINE>", str(line_number)
                        )
                        .replace("<BRANCH_TYPE>", branch_type)
                        .replace("<FUNCTION>", function.function_name)
                        .replace("<BR_COND_LINE>", str(condition_line))
                        .replace("<CONDITION>", condition_str)
                    )
                    single_branch_info_strs.append(branch_info_str)
                check_line_summary = (
                    "  - For the line <CHECK_LINE> in the function <FUNCTION>".replace(
                        "<CHECK_LINE>", str(line_number)
                    ).replace("<FUNCTION>", function.function_name)
                    + ", we have: \n"
                )
                check_line_summary += "\n".join(single_branch_info_strs)
                branch_info_strs.append(check_line_summary)
        return branch_info_strs, condition_strs

    @staticmethod
    def summarize_path_switch_info(
        environment: Environment, bug_candidate: List[Tuple[int, LocalValue]]
    ) -> List[str]:
        switch_info_strs = []

        for function_id, local_val in bug_candidate:
            function = environment.analyzed_functions[function_id]
            line_number = local_val.line_number
            switch_info_str_template = (
                " - The line <CHECK_LINE> in the function <FUNCTION> "
                "belongs to the case of the switch statements,"
                "of which the case label is `<LABEL>` and the switch expression is <SWITCH_EXPR> .\n"
            )
            split_tokens_list = []
            split_tokens_list.append([local_val.name])
            switch_expr_strs = set([])
            for (
                switch_statement_start_line,
                switch_statement_end_line,
            ) in function.switch_statements:
                (parenthesized_node_str, items) = function.switch_statements[
                    (switch_statement_start_line, switch_statement_end_line)
                ]
                switch_label = ""
                switch_expr = parenthesized_node_str.lstrip("(").rstrip(")")
                for label_str, case_start_line, case_end_line in items:
                    if case_start_line < line_number < case_end_line:
                        switch_label = label_str
                        break
                if switch_label != "":
                    switch_info_str = (
                        switch_info_str_template.replace(
                            "<CHECK_LINE>", str(line_number)
                        )
                        .replace("<FUNCTION>", function.function_name)
                        .replace("<LABEL>", switch_label)
                        .replace("<SWITCH_EXPR>", switch_expr)
                    )
                    switch_info_strs.append(switch_info_str)
                    switch_expr_strs.add(switch_expr)
                else:
                    switch_info_str = (
                        switch_info_str_template.replace(
                            "<CHECK_LINE>", str(line_number)
                        )
                        .replace("<FUNCTION>", function.function_name)
                        .replace("<LABEL>", "default")
                        .replace("<SWITCH_EXPR>", switch_expr)
                    )
                    switch_info_strs.append(switch_info_str)

                check_line_summary = (
                    "  - For the line <CHECK_LINE> in the function <FUNCTION>".replace(
                        "<CHECK_LINE>", str(line_number)
                    ).replace("<FUNCTION>", function.function_name)
                    + ", we have: \n"
                )
                check_line_summary += "\n".join(switch_info_strs)
                switch_info_strs.append(check_line_summary)
        return switch_info_strs

    def fetch_system_role(self):
        with open(self.prompt_config_file_base / self.ifv_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        role = dump_config_dict["system_role"]
        return role

    def fetch_path_check_answer_format(self) -> str:
        with open(self.prompt_config_file_base / self.ifv_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        answer_format = "\n".join(dump_config_dict["answer_format"])
        return answer_format

    @staticmethod
    def execute_solving_program(solving_program: str):
        try:
            # Run the program using subprocess
            completed_process = subprocess.run(
                ["python", "-c", solving_program], capture_output=True, text=True
            )

            # Check if the program executed successfully
            if completed_process.returncode == 0:
                # Return the console output
                return completed_process.stdout.strip()
            else:
                # Return the error output
                return completed_process.stderr.strip()
        except Exception as e:
            # Handle any exceptions that occur during program execution
            print(f"An error occurred: {str(e)}")
        return

    def construct_solving_program(
        self, line_number: int, path_description: str, val_literal: str
    ):
        print("Constructing solving program...")
        message = (
            "Please write the path condition for the line "
            + str(line_number)
            + " based on the description: \n"
        )
        message += path_description
        message += "Please write a runnable Python code to solve the path condition using Z3 python binding. "
        message += "Once I execute the program, the result can indicate whether the path constraint is SAT or UNSAT.\n"
        message += "To convenience your implementation, I provide the following skeleton for you:\n"
        program_skeleton = """
        from z3 import *
        
        def path_constraint_solving():
            solver = Solver()
        
            # TODO: Insert your implementation here
            
            
            
            # The end of your implementation
        
            result = solver.check()
        
            if result == sat:
                print("SAT")
            elif result == unsat:
                print("UNSAT")
            else:
                print("Result is unknown")
        
        # Call the function
        path_constraint_solving()
        """

        message += program_skeleton + "\n"
        message += 'Please write your own code after the comment "TODO: Insert your implementation here". \n\n'
        message += "Also, I have several tips for you: \n\n"
        message += (
            "- Assume that the condition of if-statement is C, i.e., if (C) {...} else {...}. "
            "If the line is in the true branch of the if-statement, you need to write the code like this: "
            "solver.add(C), which enforces the condition to true.\n\n"
        )
        message += (
            "- Assume that the condition of if-statement is C, i.e., if (C) {...} else {...}. "
            "If the line is in the else branch of the if-statement, you need to write the code like this: "
            "e.g., solver.add(C == False), which negates the condition C.\n\n"
        )
        message += (
            "- If you encounter a Java math function in the condition of a if-statement, you may need to use "
            "the corresponding math function provided by Z3 python binding.\n\n"
        )

        if val_literal != "":
            message += (
                "- Remember to appending the constraint that the focused variable is equal to <VALUE> to formulate the "
                "assumption mentioned above.\n\n"
            ).replace("<VALUE>", val_literal)

        message += "DO NOT change other program structures in the skeleton. "
        message += "Your response should contain the COMPLETED WHOLE PROGRAM only and DO NOT add extra explanations. "
        message += (
            "Also, the program should be wrapped with a pair of ``` at the beginning and the end of the "
            "program.\n"
        )
        # print(message)

        cnt = 0
        program = ""
        while cnt < 3:
            cnt += 1
            response, input_token_cost, output_token_cost = self.model.infer(message)
            self.total_input_token_cost += input_token_cost
            self.total_output_token_cost += output_token_cost
            response = response.replace("```python", "```")

            if response.count("```") != 2:
                continue
            else:
                program = response[
                    response.find("```") : response.rfind("```")
                ].replace("`", "")
                break
        assert program != ""
        return program

    def refine_solving_program(self, previous_solving_program: str, error_message: str):
        print("Refining solving program...")
        debug_message = "```\n" + previous_solving_program + "\n```\n"
        debug_message += (
            "When I run the program, we found the following error message: \n"
        )
        debug_message += error_message + "\n"
        debug_message += "Please fix the bug and give another program. "
        debug_message += "Your response should DO NOT add extra explanations. "
        debug_message += (
            "Also, the program should be wrapped with a pair of ``` at the beginning and the end of the "
            "program.\n"
        )

        cnt = 0
        while cnt < 3:
            cnt += 1
            (
                new_response,
                input_token_cost,
                output_token_cost,
            ) = self.model.infer(debug_message)
            self.total_input_token_cost += input_token_cost
            self.total_output_token_cost += output_token_cost

            new_response = new_response.replace("```python", "```")

            if new_response.count("```") != 2:
                continue
            else:
                new_program = new_response[
                    new_response.find("```") : new_response.rfind("```")
                ].replace("`", "")
                return new_program
        return previous_solving_program
