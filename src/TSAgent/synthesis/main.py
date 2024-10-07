from argparse import ArgumentParser
import logging
import warnings

warnings.simplefilter(action="ignore", category=FutureWarning)
import os
import sys
from collections import defaultdict
from logging import Logger
from pathlib import Path
import time

sys.path.append(os.path.join(os.path.dirname(__file__), "../../"))
from TSAgent.synthesis.utils import SynSpec, Example
from TSAgent.synthesis.llm import GPT, LLM, Claude, Gemini
from TSAgent.synthesis.prompts.examples import (
    dbz_source_examples,
    dbz_sink_examples,
    xss_source_examples,
    xss_sink_examples,
    ci_source_examples,
    ci_sink_examples,
)
from TSAgent.synthesis.synthesize import synthesize


def synthesize_dbz_source(model: LLM) -> tuple[str, int]:
    rules = """
    - If there is an integer literal node whose text is exactly `0`, that line may contain source values.
    - If there is a floating point literal node whose text is exactly `0.0` or `0.0f`, then that line may contain source values.
    - If any of the `parseInt`, `parseFloat`, `nextInt`, or `nextFloat` is a substring of a method invocation, the line contains source values.
    """
    spec = SynSpec(
        fn_name="find_dbz_src",
        df_type="source",
        rules=rules,
        examples=[Example.from_str(e) for e in dbz_source_examples],
    )
    return synthesize(model, spec)


def synthesize_dbz_sink(model: LLM) -> tuple[str, int]:
    rules = """
    - If there is an binary operation whose text contains `/` or `%`, then the second operand (whose node type should be identifier) of the binary operation is sink.
    """
    spec = SynSpec(
        fn_name="find_dbz_sink",
        df_type="sink",
        rules=rules,
        examples=[Example.from_str(e) for e in dbz_sink_examples],
    )
    return synthesize(model, spec)


def synthesize_xss_source(model: LLM) -> tuple[str, int]:
    rules = """
    - If any of the `readLine`, `executeQuery`, `getCookies`, `getParameter`, `nextToken`, or `getProperty` is a substring of a method invocation, the line contains source values.
    """
    spec = SynSpec(
        fn_name="find_xss_src",
        df_type="source",
        rules=rules,
        examples=[Example.from_str(e) for e in xss_source_examples],
    )
    return synthesize(model, spec)


def synthesize_xss_sink(model: LLM) -> tuple[str, int]:
    rules = """
    - If either `println` or `print` is a substring of method invocation, then all the arguments of the method invocation are sinks. Give all the arguments as they are and do not decompose each argument.
    """
    spec = SynSpec(
        fn_name="find_xss_sink",
        df_type="sink",
        rules=rules,
        examples=[Example.from_str(e) for e in xss_sink_examples],
    )
    return synthesize(model, spec)


def synthesize_ci_source(model: LLM) -> tuple[str, int]:
    rules = """
    - If any of the `readLine`, `getString`, `getenv`, `getValue`, `nextToken`, `executeQuery`, `getCookies`, `getParameter`, `nextToken`, `getProperty`, or `substring` is a substring of a method invocation, the line contains source values.
    """
    spec = SynSpec(
        fn_name="find_ci_src",
        df_type="source",
        rules=rules,
        examples=[Example.from_str(e) for e in ci_source_examples],
    )
    return synthesize(model, spec)


def synthesize_ci_sink(model: LLM) -> tuple[str, int]:
    rules = """
    - If `exec` is a substring of method invocation, then all the arguments of the method invocation are sinks. Give all the arguments as they are and do not decompose each argument.
    """
    spec = SynSpec(
        fn_name="find_ci_sink",
        df_type="sink",
        rules=rules,
        examples=[Example.from_str(e) for e in ci_sink_examples],
    )
    return synthesize(model, spec)


def select_model(name: str, temperature: int, output_file: str) -> LLM:
    if name == "gpt3.5":
        model = GPT(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="gpt-3.5-turbo-1106",
            temperature=temperature,
            log_file=output_file,
        )
    elif name == "gpt4":
        model = GPT(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="gpt-4-0125-preview",
            temperature=temperature,
            log_file=output_file,
        )
    elif name == "gpt-4o-mini":
        model = GPT(
            api_key=os.environ.get("OPENAI_API_KEY"),
            model="gpt-4o-mini",
            temperature=temperature,
            log_file=output_file,
        )
    elif name == "gemini-pro":
        model = Gemini(
            api_key=os.environ.get("GOOGLE_API_KEY"),
            model="gemini-pro",
            temperature=temperature,
            log_file=output_file,
        )
    elif name == "claude-haiku":
        model = Claude(
            api_key=os.environ.get("CLAUDE_API_KEY"),
            model="claude-3-haiku-20240307",
            temperature=temperature,
            log_file=output_file,
        )
    else:
        raise ValueError(f"Unknown model name {name}")
    return model


def run(
    fn_name: str,
    model_name: str,
    temperature: int = 0,
    output_file: str = "",
    log_file: str = "",
):
    logging.info(f"Synthesizing {fn_name} using {model_name}")
    start_at = time.time()
    model = select_model(model_name, temperature, log_file)
    if fn_name == "dbz_src":
        parser, iterations = synthesize_dbz_source(model)
    elif fn_name == "dbz_sink":
        parser, iterations = synthesize_dbz_sink(model)
    elif fn_name == "xss_src":
        parser, iterations = synthesize_xss_source(model)
    elif fn_name == "xss_sink":
        parser, iterations = synthesize_xss_sink(model)
    elif fn_name == "ci_src":
        parser, iterations = synthesize_ci_source(model)
    elif fn_name == "ci_sink":
        parser, iterations = synthesize_ci_sink(model)
    else:
        raise ValueError(f"Unknown function name {fn_name}")
    logging.info(f"Synthesized successfully in {iterations} iterations")
    logging.info(f"Total Iterations: {iterations}")
    logging.info(f"Total Input Token Cost: {model.input_token_cost}")
    logging.info(f"Total Output Token Cost: {model.output_token_cost}")
    logging.info(f"Total Time: {time.time() - start_at}")
    model.log(f"Total Iterations: {iterations}")
    model.log(f"Total Input Token Cost: {model.input_token_cost}")
    model.log(f"Total Output Token Cost: {model.output_token_cost}")
    model.log(f"Total Time: {time.time() - start_at}")
    with open(output_file, "w") as f:
        f.write(parser + "\n")
    logging.info(f"Parser written to {output_file}")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = ArgumentParser("Synthesis source/sink tree-sitter parser")
    parser.add_argument(
        "--extractor",
        type=str,
        default="dbz_src",
        choices=["dbz_src", "dbz_sink", "xss_src", "xss_sink", "ci_src", "ci_sink"],
        help="The source/sink extractor to synthesize",
    )
    parser.add_argument(
        "--model",
        type=str,
        default="gpt3.5",
        choices=["gpt3.5", "gpt4", "gpt-4o-mini", "gemini-pro", "claude-haiku"],
        help="The model to use",
    )
    parser.add_argument(
        "--temperature", type=float, default=0, help="The temperature of the model"
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default="TS_synbot.py",
        help="The output python file (the extractor) being synthesized",
    )
    args = parser.parse_args()
    run(
        args.extractor,
        args.model,
        temperature=args.temperature,
        output_file=args.output_file,
    )
