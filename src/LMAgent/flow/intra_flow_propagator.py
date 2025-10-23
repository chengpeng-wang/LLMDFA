import sys
from os import path
import json

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))
from LMAgent.LM_agent import LMAgent
from utility.llm import *
from utility.function import *
from typing import List, Tuple


class IntraFlowPropagator(LMAgent):
    """
    IntraFlowPropagator class for checking whether source can flow to sink in the SSI function
    """

    def __init__(self, file_path, online_model_name, openai_key, temp) -> None:
        super().__init__()
        self.ifp_file_path = file_path
        system_role = self.fetch_system_role()
        self.openai_key = openai_key
        self.model = LLM(online_model_name, self.openai_key, temp, system_role)
        self.prompt_fscot = self.construct_prompt_skeleton_fscot()
        self.prompt_no_fscot = self.construct_prompt_skeleton_no_fscot()
        self.response = ""

    def is_must_unreachable(
        self, src: LocalValue, sink: LocalValue, function: Function
    ) -> bool:
        for condition_line, if_statement_end_line in function.if_statements:
            (
                _,
                _,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            ) = function.if_statements[(condition_line, if_statement_end_line)]
            if (
                true_branch_start_line <= src.line_number <= true_branch_end_line
                and else_branch_start_line <= sink.line_number <= else_branch_end_line
            ):
                return True
            if (
                true_branch_start_line <= sink.line_number <= true_branch_end_line
                and else_branch_start_line <= src.line_number <= else_branch_end_line
            ):
                return True
        return False

    def apply(
        self,
        function: Function,
        srcs: List[LocalValue],
        sinks: List[LocalValue],
        is_fscot: bool = True,
    ) -> Tuple[
        List[Tuple[LocalValue, LocalValue]], List[Tuple[LocalValue, LocalValue]]
    ]:
        """
        Apply the intra-flow propagator to the function
        """
        reachable_pairs = []
        unreachable_pairs = []
        with open(self.prompt_config_file_base / self.ifp_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        question_template = dump_config_dict["question_template"]

        for src in srcs:
            for sink in sinks:
                # When two points are the same, then src must flow to sink
                # Handle the case where the fields are assigned with sensitive values directly
                if src.line_number == sink.line_number:
                    reachable_pairs.append((src, sink))
                    continue

                if is_fscot:
                    if self.is_must_unreachable(src, sink, function):
                        unreachable_pairs.append((src, sink))
                        continue

                # Avoid analyzing existing reachable pairs
                is_exist_reachable = False
                for existing_start, existing_end in function.reachable_summaries:
                    if str(src) == str(existing_start) and str(sink) == str(
                        existing_end
                    ):
                        is_exist_reachable = True
                        break
                if is_exist_reachable:
                    reachable_pairs.append((src, sink))
                    continue

                # Avoid analyzing existing unreachable pairs
                is_exist_unreachable = False
                for existing_start, existing_end in function.unreachable_summaries:
                    if str(src) == str(existing_start) and str(sink) == str(
                        existing_end
                    ):
                        is_exist_unreachable = True
                        break
                if is_exist_unreachable:
                    unreachable_pairs.append((src, sink))
                    continue

                question = (
                    question_template.replace("<SRC_NAME>", src.name)
                    .replace("<SRC_LINE>", str(src.line_number))
                    .replace("<SINK_NAME>", sink.name)
                    .replace("<SINK_LINE>", str(sink.line_number))
                )

                if src.name == sink.name:
                    cmp = "the same"
                else:
                    cmp = "different"

                if sink.v_type in {ValueType.ARG, ValueType.SINK}:
                    used = "used"
                else:
                    used = ""

                question = question.replace("<CMP>", cmp)
                question = question.replace("<USED>", used)

                if is_fscot:
                    message = self.prompt_fscot
                else:
                    message = self.prompt_no_fscot
                message = message.replace(
                    "<PROGRAM>", function.lined_SSI_function_without_comments
                )
                message = message.replace("<QUESTION>", question)

                if is_fscot:
                    message = message.replace(
                        "<ANSWER>", self.fetch_answer_format_fscot()
                    )
                else:
                    message = message.replace(
                        "<ANSWER>", self.fetch_answer_format_no_fscot()
                    )

                is_reachable = False
                while True:

                    output, input_token_cost, output_token_cost = self.model.infer(
                        message, True
                    )
                    self.total_input_token_cost += input_token_cost
                    self.total_output_token_cost += output_token_cost
                    self.response = output

                    yes_no_vector = LMAgent.process_yes_no_list_in_response(
                        self.response
                    )
                    if len(yes_no_vector) == 0:
                        continue
                    if yes_no_vector[0] == "Yes":
                        is_reachable = True
                    break

                if is_reachable:
                    reachable_pairs.append((src, sink))
                else:
                    unreachable_pairs.append((src, sink))
        return reachable_pairs, unreachable_pairs

    def construct_prompt_skeleton_fscot(self) -> str:
        """
        Construct the prompt according to prompt config file
        :return: The prompt
        """
        with open(self.prompt_config_file_base / self.ifp_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "\n".join(dump_config_dict["analysis_examples"])
        prompt += "\n" + "".join(dump_config_dict["meta_prompts"])
        return prompt

    def construct_prompt_skeleton_no_fscot(self) -> str:
        """
        Construct the prompt according to prompt config file
        :return: The prompt
        """
        with open(self.prompt_config_file_base / self.ifp_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        prompt = dump_config_dict["task"]
        prompt += "\n" + "\n".join(dump_config_dict["analysis_rules"])
        prompt += "\n" + "".join(dump_config_dict["meta_prompts"])
        return prompt

    def fetch_system_role(self):
        with open(self.prompt_config_file_base / self.ifp_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        role = dump_config_dict["system_role"]
        return role

    def fetch_answer_format_fscot(self) -> str:
        with open(self.prompt_config_file_base / self.ifp_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        answer_format = dump_config_dict["answer_format_cot"]
        return "\n".join(answer_format)

    def fetch_answer_format_no_fscot(self) -> str:
        with open(self.prompt_config_file_base / self.ifp_file_path, "r") as read_file:
            dump_config_dict = json.load(read_file)
        answer_format = dump_config_dict["answer_format_no_cot"]
        return "\n".join(answer_format)
