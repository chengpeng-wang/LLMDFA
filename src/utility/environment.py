from typing import Dict, List, Tuple, Set
from utility.function import *


class Environment:
    def __init__(self):
        self.caller_callee_map: Dict[Tuple[int, int], Set[int]] = (
            {}
        )  # (caller_id, line_number) --> callee ids
        self.callee_caller_map: Dict[int, Set[Tuple[int, int]]] = (
            {}
        )  # callee id --> caller id and line_number
        self.analyzed_functions: Dict[int, Function] = {}

    def insert_caller_callee_pair(
        self, caller_id: int, line_number: int, callee_id: int
    ) -> None:
        """
        Update the call graph
        :params caller_id: the id of caller function
        :params line_number: the line number of the call site in caller function that invokes the callee function
        :params callee_id: the id of callee function
        """
        if (caller_id, line_number) not in self.caller_callee_map:
            self.caller_callee_map[(caller_id, line_number)] = set([])
        self.caller_callee_map[(caller_id, line_number)].add(callee_id)
        if callee_id not in self.callee_caller_map:
            self.callee_caller_map[callee_id] = set([])
        self.callee_caller_map[callee_id].add((caller_id, line_number))
        return

    def set_analyzed_function(self, function_id: int, function: Function) -> None:
        """
        Add a function to the environment as the analyzed one
        :params function_id: the id of the function
        :params function: Function object
        """
        self.analyzed_functions[function_id] = function
        return

    def is_analyzed(self, function_id: int) -> bool:
        return function_id in self.analyzed_functions
