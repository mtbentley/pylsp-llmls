import logging

from pylsp import hookimpl  # type: ignore[import-untyped]
from litellm import completion

logger = logging.getLogger(__name__)

SYSTEM_PROMPT_COMPLETE = """
You are a helpful code assistant.
Complete the following code.
It will be inserted directly into a python source file.
* Do not include explanations
* Do not include tests
* Do include minimal comments
* Do not include markdown
* do not include backticks ("```") or anything else surrounding the result
* do not preface the resulting code with anything
"""

SYSTEM_PROMPT_INSTRUCT = """
You are a helpful code assistant.
You will get two messages: instructions then code
The format will be
INSTRUCTIONS
instructions here
CODE
code here

Follow the instructions to modify the code
* Do not include explanations
* Do not include tests
* Do include minimal comments
* Do not include markdown
* do not include backticks ("```") or anything else surrounding the result
* do not preface the resulting code with anything
* Do not include the INSTRUCTION or CODE text in your response
"""


@hookimpl
def pylsp_settings():
    logger.info("Initializing pylsp_llmls")

    return {
        "plugins": {
            "pylsp_llmls": {
                "model": "ollama/deepseek-coder-v2:16b",
                "options": {"api_base": "http://localhost:11434"},
            }
        }
    }


def _calc_new_start(text: str, old_start: dict[str, int]) -> dict[str, int]:
    start = old_start.copy()
    newlines = [i for i, c in enumerate(text) if c == "\n"] + [0]
    last_newline = max(newlines)
    num_newlines = len(newlines) - 1
    if num_newlines > 0:
        start["line"] += num_newlines
        start["character"] = len(text) - last_newline - 1
    else:
        start["character"] += len(text)
    return start


def _parse_instructions_code(text: str) -> str:
    result = "INSTRUCTIONS\n"
    text_l = text.lstrip().split("\n")
    for i, line in enumerate(text_l):
        split_i = i
        if line == "" or not line.lstrip().startswith("#"):
            break
    instructions = "\n".join(text_l[:split_i])
    code = "\n".join(text_l[split_i:])
    result += instructions
    result += "\nCODE\n"
    result += code
    return result


@hookimpl
def pylsp_execute_command(config, workspace, command, arguments):
    logger.info("workspace/executeCommand: %s %s", command, arguments)
    cfg = config.plugin_settings("pylsp_llmls")
    model = cfg.get("model")
    options = cfg.get("options", {})

    if command not in ("gay.maddie.complete", "gay.maddie.instructreplace"):
        return

    current_document, range, text = arguments

    if command == "gay.maddie.complete":
        response = completion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_COMPLETE,
                },
                {"role": "user", "content": text},
            ],
            stream=True,
            **options,
        )
    elif command == "gay.maddie.instructreplace":
        response = completion(
            model=model,
            messages=[
                {
                    "role": "system",
                    "content": SYSTEM_PROMPT_INSTRUCT,
                },
                {"role": "user", "content": _parse_instructions_code(text)},
            ],
            stream=True,
            **options,
        )

    edit = {"changes": {current_document: [{"range": range, "newText": ""}]}}
    logger.info("applying workspace edit: %s %s", command, edit)
    workspace.apply_edit(edit)

    start = range["start"]
    range["end"] = range["start"] = start
    logger.warn(range)

    for chunk in response:
        t = chunk.choices[0].delta.content
        if t is None:
            continue
        edit = {
            "changes": {current_document: [{"range": range, "newText": t}]}
        }
        logger.info("applying workspace edit: %s %s", command, edit)
        workspace.apply_edit(edit)
        start = _calc_new_start(t, start)
        range["end"] = range["start"] = start


@hookimpl
def pylsp_code_actions(config, workspace, document, range, context):
    logger.info("textDocument/codeAction: %s %s %s", document, range, context)
    start_offset = document.offset_at_position(range["start"])
    end_offset = document.offset_at_position(range["end"])
    text = document.source[start_offset:end_offset]

    return [
        {
            "title": "LLM Autocomplete",
            "kind": "source",
            "command": {
                "title": "LLM Autocomplete",
                "command": "gay.maddie.complete",
                "arguments": [document.uri, range, text],
            },
        },
        {
            "title": "LLM Instruct",
            "kind": "source",
            "command": {
                "title": "LLM Instruct",
                "command": "gay.maddie.instructreplace",
                "arguments": [document.uri, range, text],
            },
        },
        # TODO: instruct append instruction?
    ]
