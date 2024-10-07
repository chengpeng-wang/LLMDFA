import sys
from os import path

sys.path.append(path.dirname(path.dirname(path.abspath(__file__))))
from LMAgent.LM_agent import LMAgent
from utility.llm import *
from utility.function import *
from TSAgent.TS_synthesis_extractor import *


class SinkExtractor(LMAgent):
    """
    SinkExtractor class for identifying the sink values in the SSI function
    """

    def __init__(
        self,
        prompt_config_file_path,
        online_model_name: str,
        openai_key: str,
        temp: float,
    ) -> None:
        super().__init__()
        self.sink_config_file_path: str = prompt_config_file_path
        system_role, prompt = self.construct_general_prompt(
            self.sink_config_file_path, False
        )
        self.openai_key = openai_key
        self.model = LLM(online_model_name, self.openai_key, temp, system_role)
        self.prompt: str = prompt
        self.sinks: List[LocalValue] = []

        assert (
            "dbz" in self.sink_config_file_path
            or "xss" in self.sink_config_file_path
            or "ci" in self.sink_config_file_path
        )

        if "dbz" in self.sink_config_file_path:
            self.sink_identifier = find_dbz_sink
        elif "xss" in self.sink_config_file_path:
            self.sink_identifier = find_xss_sink
        elif "ci" in self.sink_config_file_path:
            self.sink_identifier = find_ci_sink

    def apply(self, function: Function, is_parse) -> None:
        """
        :param function: Function object
        :param is_parse: Whether invoke parser instead of apply the LLM
        """
        message = (
            self.prompt
            + "\n```\n"
            + function.lined_SSI_function_without_comments
            + "\n```\n"
        )
        if not is_parse:
            response, input_token_cost, output_token_cost = self.model.infer(message)
            self.sinks = LMAgent.process_response_item_lines(response, ValueType.SINK)
        else:
            self.sinks = self.sink_identifier(
                function.SSI_function_without_comments, function.parse_tree.root_node
            )
        return
