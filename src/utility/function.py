from typing import Dict, List, Tuple
import tree_sitter
from enum import Enum


class ValueType(Enum):
    SRC = 1
    SINK = 2
    PARA = 3
    RET = 4
    ARG = 5
    OUT = 6
    FIELD = 7


class LocalValue:
    def __init__(
        self, name: str, line_number: int, v_type: ValueType, index: int = -1
    ) -> None:
        self.name = name  # name can be a variable/parameter name or the expression tokenized string
        self.line_number = line_number
        self.index = index
        self.v_type = v_type

    def __str__(self) -> str:
        return (
            "("
            + "("
            + self.name
            + ", "
            + str(self.index)
            + ", "
            + str(self.line_number)
            + ")"
            + ", "
            + str(self.v_type)
            + ")"
        )

    def __repr__(self) -> str:
        return self.__str__()


class Function:
    def __init__(
        self, function_id: int, function_name: str, original_function: str
    ) -> None:
        """
        Record basic facts of the function
        """
        self.function_id: int = function_id
        self.function_name: str = function_name
        self.original_function: str = original_function
        self.parse_tree: tree_sitter.Tree = None
        self.is_transformed: bool = False
        self.is_parsed: bool = False

        self.SSI_function: str = ""
        self.SSI_function_without_comments: str = ""
        self.lined_SSI_function_without_comments: str = ""

        # field initialization statements
        self.field_inits: Dict[int, str] = {}

        # para name, para type, index
        self.paras: List[LocalValue] = []

        # returned var name and line number
        self.rets: List[LocalValue] = []

        # call site nodes and line numbers (conform to control flow order
        self.call_site_nodes: List[Tuple[tree_sitter.Node, int]] = []

        # call site node, input variable name and index, output variable name and line number, callee id list
        self.line_to_call_site_info: Dict[
            int,
            Tuple[
                tree_sitter.Node,
                List[LocalValue],
                List[LocalValue],
                List[int],
            ],
        ] = {}

        # if statement info
        self.if_statements: Dict[Tuple, Tuple] = {}

        # switch statement info
        self.switch_statements: Dict[Tuple, List] = {}

        # function summaries
        self.reachable_summaries: List[Tuple[LocalValue, LocalValue]] = []
        self.unreachable_summaries: List[Tuple[LocalValue, LocalValue]] = []

    def set_transformed_function(
        self, transformed_function: str, lined_transformed_function: str
    ) -> None:
        """
        :param transformed_function: SSI form
        :param lined_transformed_function: SSI form with line numbers
        """
        self.SSI_function = transformed_function
        self.lined_SSI_function = lined_transformed_function
        self.is_transformed = True
        return

    def set_parse_tree(self, parse_tree: tree_sitter.Tree) -> None:
        self.parse_tree = parse_tree
        self.is_parsed = True
        return

    def set_call_sites(self, call_sites: List[Tuple[tree_sitter.Node, int]]) -> None:
        self.call_site_nodes = call_sites
        return

    def set_para_ret_info(
        self, paras: List[LocalValue], rets: List[LocalValue] = []
    ) -> None:
        self.paras = paras
        self.rets = rets
        return

    def set_field_inits_info(self, field_inits: Dict[int, str]) -> None:
        self.field_inits = field_inits
        return

    def update_line_to_call_site_info(
        self,
        line_number: int,
        call_site_node: tree_sitter.Node,
        args: List[LocalValue],
        outputs: List[LocalValue],
        callee_ids: List[int],
    ) -> None:
        assert (
            line_number not in self.line_to_call_site_info
        )  # program should be SSI function
        self.line_to_call_site_info[line_number] = (
            call_site_node,
            args,
            outputs,
            callee_ids,
        )
        return

    def extend_function_summaries(
        self,
        reachable_summaries: List[Tuple[LocalValue, LocalValue]],
        unreachable_summaries: List[Tuple[LocalValue, LocalValue]],
    ):
        for start, end in reachable_summaries:
            is_exist = False
            for existing_start, existing_end in self.reachable_summaries:
                if str(start) == str(existing_start) and str(end) == str(existing_end):
                    is_exist = True
                    break
            if not is_exist:
                self.reachable_summaries.append((start, end))
        for start, end in unreachable_summaries:
            is_exist = False
            for existing_start, existing_end in self.unreachable_summaries:
                if str(start) == str(existing_start) and str(end) == str(existing_end):
                    is_exist = True
                    break
            if not is_exist:
                self.unreachable_summaries.append((start, end))
        return

    def find_para_value_by_index(self, index: int) -> LocalValue:
        for para in self.paras:
            if para.index == index:
                return para
        assert "unreachable code"

    def find_output_value_by_line_number(self, line_number) -> List[LocalValue]:
        assert line_number in self.line_to_call_site_info
        (_, _, outputs, _) = self.line_to_call_site_info[line_number]
        assert len(outputs) <= 1
        return outputs

    def print_function_info(self) -> None:
        print("-----------------------------------------")
        print("function:")
        print(self.lined_SSI_function)
        print("-----------------------------------------")
        print("para info:")
        for para in self.paras:
            print(str(para))
        print("-----------------------------------------")
        print("ret info:")
        for ret in self.rets:
            print(str(ret))
        print("-----------------------------------------")
        print("call site info:")
        for line_number in self.line_to_call_site_info:
            (node, outputs, args, callee_ids) = self.line_to_call_site_info[line_number]
            print("line_number: ", line_number)
            print("callee_ids: ", str(callee_ids))
            print("args: ")
            for arg in args:
                print(str(arg))
            print("outputs: ")
            for output in outputs:
                print(str(output))
        print("-----------------------------------------")
        return

    def print_function_summary(self) -> None:
        print("---------------------------")
        print("function id: ", self.function_id)
        print("---------------------------")
        print(self.lined_SSI_function)
        print("---------------------------")
        print("#summaries: ", len(self.reachable_summaries))
        for v1, v2 in self.reachable_summaries:
            print(
                v1.name,
                v1.line_number,
                v1.v_type,
                " -> ",
                v2.name,
                v2.line_number,
                v2.v_type,
            )
        print("---------------------------\n")
