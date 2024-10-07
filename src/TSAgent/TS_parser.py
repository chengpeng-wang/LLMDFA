import os
import tree_sitter
from tree_sitter import Language
from typing import Dict, List
from pathlib import Path


class TSParser:
    """
    TSParser class for extracting information from Java files using tree-sitter.
    """

    def __init__(self, java_file_path: str) -> None:
        """
        Initialize TSParser with a java file path
        :param java_file_path: The path of a java file.
        """
        self.java_file_path: str = java_file_path
        self.methods: Dict[int, (str, str)] = {}
        self.classToFunctions: Dict[str, List[int]] = {}
        self.classToFields: Dict[str, List[int]] = {}
        self.fields: Dict[int, str] = {}
        self.fields_init: Dict[int, str] = {}

        self.fileToPackage: Dict[str, str] = {}
        self.fileToImports: Dict[str, set[str]] = {}
        self.fileToClasses: Dict[str, set[str]] = {}
        self.functionToFile: Dict[int, str] = {}
        self.packageToClasses: Dict[str, set[str]] = {}

        self.static_field_info: Dict[str, str] = {}

        cwd = Path(__file__).resolve().parent.absolute()
        TSPATH = cwd.parent.parent / "lib/build/"
        language_path = TSPATH / "my-languages.so"
        # Load the Java language
        self.java_lang: Language = Language(str(language_path), "java")

        # Initialize the parser
        self.parser: tree_sitter.Parser = tree_sitter.Parser()
        self.parser.set_language(self.java_lang)

    def parse_package_info(
        self, file_path: str, source_code: str, root_node: tree_sitter.Tree
    ) -> str:
        """
        Extract package, Assume only have one package declaration
        :param file_path: The path of the Java file.
        :param source_code: The content of the source code
        :param root_node: The root node the parse tree
        :return package name
        """
        package_code = ""
        for node in root_node.children:
            if node.type == "package_declaration":
                for child_node in node.children:
                    if child_node.type in {"scoped_identifier", "identifier"}:
                        package_code = source_code[
                            child_node.start_byte : child_node.end_byte
                        ]
                        if package_code != "":
                            break
                self.fileToPackage[file_path] = package_code
                break
        return package_code

    def parse_import_info(
        self, file_path: str, source_code: str, root_node: tree_sitter.Tree
    ) -> None:
        """
        Extract imported packages or classes
        :param file_path: The path of the Java file.
        :param source_code: The content of the source code
        :param root_node: The root node the parse tree
        """
        for node in root_node.children:
            import_code = ""
            if node.type == "import_declaration":
                for child_node in node.children:
                    if child_node.type in {"scoped_identifier", "identifier"}:
                        import_code = source_code[
                            child_node.start_byte : child_node.end_byte
                        ]
                    if import_code == "":
                        continue
                    if file_path not in self.fileToImports:
                        self.fileToImports[file_path] = set([])
                    self.fileToImports[file_path].add(import_code)

    def parse_class_declaration_info(
        self,
        file_path: str,
        source_code: str,
        package_name: str,
        root_node: tree_sitter.Tree,
    ) -> None:
        """
        Extract class declaration info: class name, fields, and methods
        :param file_path: The path of the Java file.
        :param source_code: The content of the source code
        :param package_name: The package name
        :param root_node: The root node the parse tree
        """
        for node in root_node.children:
            class_name = ""
            if node.type == "class_declaration":
                # Extract class name
                for child_node in node.children:
                    if child_node.type == "identifier":
                        class_name = source_code[
                            child_node.start_byte : child_node.end_byte
                        ]
                        break
                if file_path not in self.fileToClasses:
                    self.fileToClasses[file_path] = set([])
                self.fileToClasses[file_path].add(class_name)
                if package_name not in self.packageToClasses:
                    self.packageToClasses[package_name] = set([])
                self.packageToClasses[package_name].add(class_name)

                # Extract method name and method content
                for child_node in node.children:
                    if child_node.type == "class_body":
                        for child_child_node in child_node.children:
                            # Extract methodsw
                            if child_child_node.type == "method_declaration":
                                method_name = ""
                                for child_child_child_node in child_child_node.children:
                                    if child_child_child_node.type == "identifier":
                                        method_name = source_code[
                                            child_child_child_node.start_byte : child_child_child_node.end_byte
                                        ]
                                        break
                                method_code = source_code[
                                    child_child_node.start_byte : child_child_node.end_byte
                                ]
                                method_id = len(self.methods) + 1
                                self.methods[method_id] = (method_name, method_code)
                                if class_name not in self.classToFunctions:
                                    self.classToFunctions[class_name] = []
                                self.classToFunctions[class_name].append(method_id)
                                self.functionToFile[method_id] = file_path

                            # Extract fields
                            if child_child_node.type == "field_declaration":
                                for child_child_child_node in child_child_node.children:
                                    if (
                                        child_child_child_node.type
                                        == "variable_declarator"
                                    ):
                                        for (
                                            child_child_child_child_node
                                        ) in child_child_child_node.children:
                                            if (
                                                child_child_child_child_node.type
                                                == "identifier"
                                            ):
                                                field_id = len(self.fields)
                                                self.fields[field_id] = source_code[
                                                    child_child_child_child_node.start_byte : child_child_child_child_node.end_byte
                                                ]
                                                self.fields_init[field_id] = (
                                                    source_code[
                                                        child_child_child_node.start_byte : child_child_child_node.end_byte
                                                    ]
                                                )
                                                if class_name not in self.classToFields:
                                                    self.classToFields[class_name] = []
                                                self.classToFields[class_name].append(
                                                    field_id
                                                )

    def extract_single_file(self, file_path: str) -> None:
        """
        Process a single Java file and extract method and field information.
        :param file_path: The path of the Java file.
        """
        with open(file_path, "r") as file:
            source_code = file.read()

        # Parse the Java code
        tree: tree_sitter.Tree = self.parser.parse(bytes(source_code, "utf8"))

        # Get the root node of the parse tree
        root_node: tree_sitter.Node = tree.root_node

        # Obtain package, import, and class info
        package_name = self.parse_package_info(file_path, source_code, root_node)
        self.parse_import_info(file_path, source_code, root_node)
        self.parse_class_declaration_info(
            file_path, source_code, package_name, root_node
        )

    def extract_static_field_from_support_files(self, support_files):
        def find_nodes(
            root_node: tree_sitter.Node, node_type: str
        ) -> List[tree_sitter.Node]:
            nodes = []
            if root_node.type == node_type:
                nodes.append(root_node)

            for child_node in root_node.children:
                nodes.extend(find_nodes(child_node, node_type))
            return nodes

        for support_file in support_files:
            with open(support_file, "r") as file:
                source_code = file.read()

            # Parse the Java code
            tree: tree_sitter.Tree = self.parser.parse(bytes(source_code, "utf8"))

            # Get the root node of the parse tree
            root_node: tree_sitter.Node = tree.root_node
            class_body_items = find_nodes(root_node, "class_declaration")

            for class_body_item in class_body_items:
                class_name = ""
                for child_node in class_body_item.children:
                    if child_node.type == "identifier":
                        class_name = source_code[
                            child_node.start_byte : child_node.end_byte
                        ]
                    elif child_node.type == "class_body":
                        for child_child_node in child_node.children:
                            if child_child_node.type == "field_declaration":
                                if (
                                    " static "
                                    in source_code[
                                        child_child_node.start_byte : child_child_node.end_byte
                                    ]
                                ):
                                    for field_token in child_child_node.children:
                                        if field_token.type == "variable_declarator":
                                            info_str = source_code[
                                                field_token.start_byte : field_token.end_byte
                                            ]
                                            field_name = info_str.split("=")[0].rstrip()
                                            assigned_value = info_str.split("=")[
                                                1
                                            ].lstrip()
                                            self.static_field_info[
                                                class_name + "." + field_name
                                            ] = (
                                                class_name
                                                + "."
                                                + field_name
                                                + " = "
                                                + assigned_value
                                            )

    def extract_all(self) -> None:
        """
        Process all the files in the project path and invoke extract_single_file for each file.
        """
        for root, _, files in os.walk(self.proj_path):
            for file in files:
                if file.endswith(".java"):
                    file_path: str = os.path.join(root, file)
                    self.extract_single_file(file_path)

    def get_pretty_ast(self, file_path: str) -> str:
        """
        Print the extracted AST in a pretty format.
        """
        with open(file_path, "r") as file:
            source_code = file.read()

        # parse source code
        tree: tree_sitter.Tree = self.parser.parse(bytes(source_code, "utf8"))

        def traverse(node: tree_sitter.Node, depth: int) -> str:
            ret = ""
            for child in node.children:
                code = source_code[child.start_byte : child.end_byte]
                ret += "\n" + "  " * depth + f"[{child.type}] '{code}'"
                ret += traverse(child, depth + 1)
            return ret

        # prettify AST
        # return tree.root_node.sexp()
        return traverse(tree.root_node, 0)

    def get_ast(self, file_path: str) -> tree_sitter.Tree:
        """
        Return the AST of a Java file.
        """
        with open(file_path, "r") as file:
            source_code = file.read()

        # parse source code
        tree: tree_sitter.Tree = self.parser.parse(bytes(source_code, "utf8"))

        return tree
