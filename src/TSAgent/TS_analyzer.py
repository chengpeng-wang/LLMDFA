import sys
from os import path
import tree_sitter

sys.path.append(path.dirname(path.dirname(path.dirname(path.abspath(__file__)))))

from TSAgent.TS_parser import TSParser
from typing import List, Tuple
from utility.function import *


class TSAnalyzer:
    """
    TSAnalyzer class for retrieving necessary facts or functions for LMAgent
    """

    def __init__(self, java_file_path: str, support_files: List[str]) -> None:
        """
        Initialize TSParser with the project path.
        Currently we only analyze a single java file
        :param java_file_path: The path of a java file
        """
        self.java_file_path: str = java_file_path
        self.ts_parser: TSParser = TSParser(java_file_path)

        self.ts_parser.extract_single_file(self.java_file_path)
        self.ts_parser.extract_static_field_from_support_files(support_files)

        # self.ts_parser.extract_all()
        self.main_ids: List[int] = self.find_all_top_functions()
        self.tmp_variable_count = 0

    def find_all_top_functions(self) -> List[int]:
        """
        Collect all the main functions, which are ready for analysis
        :return: a list of ids indicating main functions
        """
        # self.methods: Dict[int, (str, str)] = {}
        main_ids = []
        for method_id in self.ts_parser.methods:
            (name, code) = self.ts_parser.methods[method_id]
            if code.count("\n") < 2:
                continue
            if name in {"good", "bad"}:
                main_ids.append(method_id)
        return main_ids

    @staticmethod
    def find_nodes(
        root_node: tree_sitter.Node, node_type: str
    ) -> List[tree_sitter.Node]:
        """
        Find all the nodes with node_type type underlying the root node.
        :param root_node: root node
        :return the list of the nodes with node_type type
        """
        # TODO: If node_type is 'method_invocation',
        #  We need to ensure that the call site nodes in the list conform to the control flow order
        nodes = []
        if root_node.type == node_type:
            nodes.append(root_node)
        for child_node in root_node.children:
            nodes.extend(TSAnalyzer.find_nodes(child_node, node_type))
        return nodes

    def find_callee(
        self, method_id: int, source_code: str, call_site_node: tree_sitter.Node
    ) -> List[int]:
        """
        Find callees that invoked by a specific method.
        Attention: call_site_node should be derived from source_code directly
        :param method_id: caller function id
        :param file_path: the path of the file containing the caller function
        :param source_code: the content of the source file
        :param call_site_node: the node of the call site. The type is 'call_expression'
        :return the list of the ids of called functions
        """
        assert call_site_node.type == "method_invocation"
        method_name = ""
        for node2 in call_site_node.children:
            if node2.type == "identifier":
                method_name = source_code[node2.start_byte : node2.end_byte]
                break

        file_path = self.ts_parser.functionToFile[method_id]

        # Collect usable classes in the file named src_prompt_config_path
        usable_classes = set([])
        if file_path in self.ts_parser.fileToClasses:
            usable_classes = usable_classes.union(
                self.ts_parser.fileToClasses[file_path]
            )

        if file_path in self.ts_parser.fileToImports:
            for import_item in self.ts_parser.fileToImports[file_path]:
                for package_item in self.ts_parser.packageToClasses:
                    if package_item.startswith(import_item):
                        usable_classes = usable_classes.union(
                            self.ts_parser.packageToClasses[package_item]
                        )
                    if import_item.startswith(package_item):
                        tail_name = import_item.replace(package_item, "").replace(
                            ".", ""
                        )
                        if tail_name in self.ts_parser.packageToClasses[package_item]:
                            usable_classes.add(tail_name)

        # Grep callees with names
        callee_ids = []
        for class_name in usable_classes:
            if class_name not in self.ts_parser.classToFunctions:
                continue
            for method_id in self.ts_parser.classToFunctions[class_name]:
                if method_id not in self.ts_parser.methods:
                    continue
                (name, code) = self.ts_parser.methods[method_id]
                if name == method_name:
                    callee_ids.append(method_id)
        return callee_ids

    @staticmethod
    def find_function_parameters(
        source_code: str, root_node: tree_sitter.Node
    ) -> List[LocalValue]:
        """
        Extract the (formal) parameter info of a function
        :param source_code: the source code of a function
        :param root_node: the root node of the parse tree of the function
        :return the list of args, including arg names, type names, and indexes.
        """
        paras = []
        paras_nodes: List[tree_sitter.Node] = TSAnalyzer.find_nodes(
            root_node, "formal_parameters"
        )
        para_index = 1
        for para_node in paras_nodes[0].children:
            if para_node.type == "formal_parameter":
                para_name = source_code[
                    para_node.children[1].start_byte : para_node.children[1].end_byte
                ]
                paras.append(LocalValue(para_name, 1, ValueType.PARA, para_index))
                para_index += 1
        return paras

    @staticmethod
    def find_function_returns(
        source_code: str, root_node: tree_sitter.Node
    ) -> List[LocalValue]:
        """
        Extract the (formal) return info of a function
        :param source_code: the source code of a function
        :param root_node: the root node of the parse tree of the function
        :return the list of return value, including variable name and the line number
        """
        rets = []
        ret_nodes: List[tree_sitter.Node] = TSAnalyzer.find_nodes(
            root_node, "return_statement"
        )
        for ret_node in ret_nodes:
            for child in ret_node.children:
                if child.type == "identifier":
                    return_var = source_code[child.start_byte : child.end_byte]
                    line_num = source_code[: child.start_byte].count("\n") + 1
                    rets.append(LocalValue(return_var, line_num, ValueType.RET))
        return rets

    @staticmethod
    def find_call_site_args(
        source_code: str, call_site_node: tree_sitter.Node, line_number: int
    ) -> List[LocalValue]:
        """
        Extract the input info of a call site
        :param source_code: the source code of a function
        :param call_site_node: the node of a call site
        :param line_number: the line number of the call site
        :return the list of input variable names and the indexes
        """
        inputs = []
        index = 1
        for node in call_site_node.children:
            if node.type == "argument_list":
                for child in node.children:
                    if child.type == "identifier":
                        input_var = source_code[child.start_byte : child.end_byte]
                        inputs.append(
                            LocalValue(input_var, line_number, ValueType.ARG, index)
                        )
                        index += 1
        return inputs

    @staticmethod
    def find_call_site_outputs(
        source_code: str,
        root_node: tree_sitter.Node,
        call_site_node: tree_sitter.Node,
        line_number: int,
    ) -> List[LocalValue]:
        """
        Extract the output info of a call site
        :param source_code: the source code of a function
        :param root_node: the root node of a function
        :param call_site_node: the node of a call site
        :param line_number: the line number of a call site
        :return the list of output variable name and line number
        """
        outputs = []

        # Find assignment_expression
        nodes = TSAnalyzer.find_nodes(root_node, "assignment_expression")

        # Find local_variable_declaration
        nodes.extend(TSAnalyzer.find_nodes(root_node, "variable_declarator"))

        # Extract the name info and line number
        for node in nodes:
            if source_code[: node.start_byte].count("\n") == source_code[
                : call_site_node.start_byte
            ].count("\n"):
                for child in node.children:
                    if child.type == "identifier":
                        name = source_code[child.start_byte : child.end_byte]
                        outputs.append(LocalValue(name, line_number, ValueType.OUT))
        assert len(outputs) <= 1
        return outputs

    def find_class_by_function(self, function_id: int) -> str:
        class_name = ""
        for name in self.ts_parser.classToFunctions:
            if function_id in self.ts_parser.classToFunctions[name]:
                class_name = name
                break
        return class_name

    def find_IO_field(
        self,
        function_id: int,
        source_code: str,
        root_node: tree_sitter.Node,
        IO_type: str,
    ) -> List[LocalValue]:
        """
        Extract the write operation upon the field and return the fields
        :param function_id: function id
        :param source_code: the source code of a function
        :param root_node: the root node of a function
        :param IO_type: "read" or "write"
        :return the list of overwritten field name and line number
        """
        assert IO_type in {"read", "write"}
        available_fields = self.find_available_fields(function_id)
        IO_fields: List[LocalValue] = []

        # Attention: Here we only analyze the functions in a single class
        # All the accessed/modified fields belong to the current class
        # In the future, we can generalize the analysis to support inter-class analysis

        # Obtain class name
        class_name = self.find_class_by_function(function_id)
        assert class_name != ""

        # Find assignment_expression
        nodes = TSAnalyzer.find_nodes(root_node, "assignment_expression")

        if IO_type == "read":
            nodes.extend(TSAnalyzer.find_nodes(root_node, "variable_declarator"))

        # Extract the name info and line number
        for node in nodes:
            line_number = source_code[: node.start_byte].count("\n")
            is_equal_found = False
            for child in node.children:
                if child.type == "=":
                    is_equal_found = True
                    continue
                if child.type == "identifier" and (
                    is_equal_found ^ (IO_type == "write")
                ):
                    name = source_code[child.start_byte : child.end_byte]
                    if name in available_fields.values():
                        IO_fields.append(LocalValue(name, line_number, ValueType.FIELD))
                if child.type == "field_access" and (
                    is_equal_found ^ (IO_type == "write")
                ):
                    name = source_code[child.start_byte : child.end_byte]
                    name_1 = name[: name.find(".")]
                    name_2 = name[name.find(".") + 1 :]
                    if name_2 in available_fields.values() and name_1 == class_name:
                        IO_fields.append(
                            LocalValue(name_2, line_number, ValueType.FIELD)
                        )
        return IO_fields

    def find_available_fields(self, function_id: int) -> Dict[int, str]:
        class_name = self.find_class_by_function(function_id)
        if class_name not in self.ts_parser.classToFields:
            return {}
        field_ids_to_names = {}
        for field_id in self.ts_parser.classToFields[class_name]:
            field_ids_to_names[field_id] = self.ts_parser.fields[field_id]
        return field_ids_to_names

    def find_field_initialization(self, function_id: int) -> Dict[int, str]:
        class_name = self.find_class_by_function(function_id)
        if class_name not in self.ts_parser.classToFields:
            return {}
        field_inits = {}
        for field_id in self.ts_parser.classToFields[class_name]:
            field_inits[field_id] = self.ts_parser.fields_init[field_id]
        return field_inits

    def find_if_statements(self, source_code, root_node) -> Dict[Tuple, Tuple]:
        targets = self.find_nodes(root_node, "if_statement")
        if_statements = {}
        for target in targets:
            condition_str = ""
            condition_line = 0
            true_branch_start_line = 0
            true_branch_end_line = 0
            else_branch_start_line = 0
            else_branch_end_line = 0
            block_num = 0
            for sub_target in target.children:
                if sub_target.type == "parenthesized_expression":
                    condition_line = (
                        source_code[: sub_target.start_byte].count("\n") + 1
                    )
                    condition_str = source_code[
                        sub_target.start_byte : sub_target.end_byte
                    ]
                if sub_target.type == "block":
                    if block_num == 0:
                        true_branch_start_line = (
                            source_code[: sub_target.start_byte].count("\n") + 1
                        )
                        true_branch_end_line = (
                            source_code[: sub_target.end_byte].count("\n") + 1
                        )
                        block_num += 1
                    elif block_num == 1:
                        else_branch_start_line = (
                            source_code[: sub_target.start_byte].count("\n") + 1
                        )
                        else_branch_end_line = (
                            source_code[: sub_target.end_byte].count("\n") + 1
                        )
                        block_num += 1
            if_statement_end_line = max(true_branch_end_line, else_branch_start_line)
            if_statements[(condition_line, if_statement_end_line)] = (
                condition_line,
                condition_str,
                (true_branch_start_line, true_branch_end_line),
                (else_branch_start_line, else_branch_end_line),
            )
        return if_statements

    def find_switch_statements(self, source_code, root_node) -> Dict[Tuple, Tuple]:
        targets = self.find_nodes(root_node, "switch_expression")
        switch_statements = {}
        for target in targets:
            parenthesized_node = self.find_nodes(target, "parenthesized_expression")[0]
            condition_line = (
                source_code[: parenthesized_node.start_byte].count("\n") + 1
            )
            parenthesized_node_str = source_code[
                parenthesized_node.start_byte : parenthesized_node.end_byte
            ]
            switch_statement_start_line = condition_line
            switch_statement_end_line = source_code[: target.end_byte].count("\n") + 1

            case_group = self.find_nodes(target, "switch_block_statement_group")
            items = []
            for case_item in case_group:
                case_start_line = source_code[: case_item.start_byte].count("\n") + 1
                case_end_line = source_code[: case_item.end_byte].count("\n") + 1

                switch_label_node = self.find_nodes(case_item, "switch_label")[0]
                switch_label = source_code[
                    switch_label_node.start_byte : switch_label_node.end_byte
                ]
                if "case " in switch_label:
                    label_str = switch_label.replace("case ", "").lstrip().rstrip()
                else:
                    label_str = ""
                items.append((label_str, case_start_line, case_end_line))

            switch_statements[
                (switch_statement_start_line, switch_statement_end_line)
            ] = (parenthesized_node_str, items)
        return switch_statements
