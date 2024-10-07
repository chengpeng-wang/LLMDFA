import os

from tree_sitter import Language, Parser
from pathlib import Path

cwd = Path(__file__).resolve().parent.absolute()

# clone tree-sitter if necessary
if not (cwd / "vendor/tree-sitter-java/grammar.js").exists():
    os.system(
        f'git clone https://github.com/tree-sitter/tree-sitter-java.git {cwd / "vendor/tree-sitter-java"}'
    )
    os.system(
        f'cd {cwd / "vendor/tree-sitter-java"} && git checkout 490d878cf33b0ad5ae7a7253ff30597a5bdc348e && cd {cwd}'
    )

Language.build_library(
    # Store the library in the `build` directory
    str(cwd / "build/my-languages.so"),
    # Include one or more languages
    [str(cwd / "vendor/tree-sitter-java")],
)
