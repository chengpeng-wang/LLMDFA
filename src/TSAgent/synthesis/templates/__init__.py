from pathlib import Path

from TSAgent.synthesis.utils import SynSpec


def gen_skeleton(spec: SynSpec) -> str:
    if spec.df_type == "source":
        template_file = Path(__file__).resolve().parent.absolute() / "source.py"
    elif spec.df_type == "sink":
        template_file = Path(__file__).resolve().parent.absolute() / "sink.py"
    else:
        raise ValueError(f"Unknown DFType {spec.df_type}")
    template = template_file.read_text()
    template = template.replace("__T__FN_NAME__T__", spec.fn_name)
    return template
