import importlib
import logging
import re
import traceback
from pathlib import Path

from TSAgent.synthesis.utils import SynSpec, Example, TSUtils
from TSAgent.synthesis.llm import GPT
from TSAgent.synthesis.prompts.common import (
    system_role,
    synthesize_task,
    utilities,
    refine_task,
    ast_usage,
)
from utility.function import ValueType


class Feedback:
    def __init__(
        self,
        spec: SynSpec,
        message: str = "",
        missed_examples: list[(Example, int, str)] = None,
        wrong_examples: list[(Example, int)] = None,
    ):
        self.spec = spec
        self.message = message
        self.missed_examples = missed_examples or []
        self.wrong_examples = wrong_examples or []

    def get_prompt(self) -> str:
        missed_msg = f"The {self.spec.df_type}s in following examples are missed by the synthesized parser:\n"
        for example, line in self.missed_examples:
            lbl = list(filter(lambda x: x[0] == line, example.label))[0]
            missed_msg += f"The {lbl[2]} `{lbl[1]}` at line {lbl[0]} in the following code are missed:\n"
            missed_msg += "```\n" + "\n".join(example.code) + "\n```\n"
            missed_msg += f"The corresponding AST of the above code is:\n"
            missed_msg += f"```\n{self.spec.get_pretty_ast(example)}\n```\n"
            missed_msg += "\n"

        wrong_msg = f"The {self.spec.df_type}s in following examples are wrong by the synthesized parser:\n"
        for example, line, value in self.wrong_examples:
            wrong_msg += f"The {self.spec.df_type} `{value}` at line {line} in the following code is not {self.spec.df_type}, but the parser identifies it:\n"
            wrong_msg += "```\n" + "\n".join(example.code) + "\n```\n"
            wrong_msg += f"The corresponding AST of the above code is:\n"
            wrong_msg += f"```\n{self.spec.get_pretty_ast(example)}\n```\n"
            wrong_msg += "\n"

        msg = self.message
        if len(self.missed_examples) > 0:
            msg += missed_msg
            msg += "You may want to loosen the conditions in the parser to cover the above examples.\n"
            msg += "\n"
        if len(self.wrong_examples) > 0:
            msg += wrong_msg
            msg += "You may want to combine multiple conditions in the parser to avoid the above examples.\n"
            msg += "\n"
        return msg


def evaluate_parser(spec: SynSpec, parser: str) -> Feedback | None:
    parent_dir = Path(__file__).resolve().parent.absolute()
    with open(parent_dir / "synthesized_parser.py", "w") as f:
        f.write(parser + "\n")

    try:
        synthesized_parser_module = importlib.import_module(
            "TSAgent.synthesis.synthesized_parser"
        )
        synthesized_parser_module = importlib.reload(synthesized_parser_module)
        parser_fn = getattr(synthesized_parser_module, spec.fn_name)
    except Exception as e:
        feedback = Feedback(
            spec,
            message=f"Failed to import the synthesized parser. {e}\n{traceback.format_exc()}",
        )
        return feedback

    # evaluate the synthesized parser
    utils = TSUtils()
    missed = []
    wrong = []
    for example in spec.examples:
        code = "\n".join(example.code)
        tree = utils.parse_code(code)
        try:
            local_values = parser_fn(code, tree.root_node)
            vs = list(
                map(
                    lambda v: (
                        v.line_number,
                        v.name,
                        "source" if v.v_type == ValueType.SRC else "sink",
                    ),
                    local_values,
                )
            )
            for line, value, label in vs:
                if (line, value, label) not in example.label:
                    wrong.append((example, line, value))
            for line, value, label in example.label:
                if (line, value, label) not in vs:
                    missed.append((example, line))
        except Exception as e:
            feedback = Feedback(
                spec,
                message=f"Failed to parse the code example {example.code}. {e}\n{traceback.format_exc()}",
            )
            return feedback
    if len(missed) == 0 and len(wrong) == 0:
        return None
    feedback = Feedback(spec, missed_examples=missed, wrong_examples=wrong)
    return feedback


def synthesize(model: GPT, spec: SynSpec) -> tuple[str, int]:
    """
    Synthesize source or sink extractor from the given specification.
    """
    logging.info("Synthesizing the parser...")
    model.set_system_role(system_role)
    syn_task = synthesize_task(spec)
    prompt = f"""
    {syn_task}
    {utilities}
    {ast_usage}
    """
    resp = model.query(prompt)
    matches = re.search(r"```(python)?\n(.*)\n```", resp, re.DOTALL | re.MULTILINE)
    synthesized = matches.group(2)
    feedback = evaluate_parser(spec, synthesized)
    iterations = 1
    while feedback is not None:
        logging.info("Synthesized an incorrect parser. Refining the parser...")
        ref_task = refine_task(
            spec, feedback, script=synthesized if iterations % 5 != 0 else None
        )
        prompt = f"""
        {ref_task}
        {utilities}
        {ast_usage}
        """
        resp = model.query(prompt)
        matches = re.search(r"```(python)?\n(.*)\n```", resp, re.DOTALL | re.MULTILINE)
        if matches is None:
            iterations += 1
            continue
        synthesized = matches.group(2)
        feedback = evaluate_parser(spec, synthesized)
        iterations += 1

    return synthesized, iterations
