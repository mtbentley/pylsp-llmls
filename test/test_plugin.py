from pylsp_llmls import plugin
import pytest
from test.conftest import *


def test_calc_new_start_no_newline():
    old_start = {"line": 1, "character": 2}
    text = "test_text"
    assert plugin._calc_new_start(text, old_start) == {
        "line": 1,
        "character": 11,
    }


def test_calc_new_start_empty():
    old_start = {"line": 1, "character": 2}
    text = ""
    assert plugin._calc_new_start(text, old_start) == old_start


def test_calc_new_start_one_newline():
    old_start = {"line": 1, "character": 2}
    text = "test\ntest2"
    assert plugin._calc_new_start(text, old_start) == {
        "line": 2,
        "character": 5,
    }


def test_calc_new_start_many_newline():
    old_start = {"line": 1, "character": 2}
    text = "test\ntest2\ntest3\n"
    assert plugin._calc_new_start(text, old_start) == {
        "line": 4,
        "character": 0,
    }


def test_parse_instructions_code_simple():
    inp = """
# do stuff
# but actually
code
code again
"""
    assert (
        plugin._parse_instructions_code(inp)
        == """INSTRUCTIONS
# do stuff
# but actually
CODE
code
code again
"""
    )


def test_parse_instructions_code_simple2():
    inp = """
# do stuff
# but actually

code
code again
"""
    assert (
        plugin._parse_instructions_code(inp)
        == """INSTRUCTIONS
# do stuff
# but actually
CODE

code
code again
"""
    )


def test_parse_instructions_code_no_code():
    inp = """
# do stuff
# but actually
"""
    assert (
        plugin._parse_instructions_code(inp)
        == """INSTRUCTIONS
# do stuff
# but actually
CODE
"""
    )


@pytest.mark.skip("not done")
def test_code_action(config, workspace, document, code_action_context):
    selection = {
        "start": {
            "line": 3,
            "character": 0,
        },
        "end": {
            "line": 4,
            "character": 0,
        },
    }

    response = plugin.pylsp_code_actions(
        config=config,
        workspace=workspace,
        document=document,
        range=selection,
        context=code_action_context,
    )

    expected = [
        {
            "title": "Extract method",
            "kind": "refactor.extract",
            "command": {
                "command": "example.refactor.extract",
                "arguments": [document.uri, selection],
            },
        },
    ]

    assert response == expected

    command = response[0]["command"]["command"]
    arguments = response[0]["command"]["arguments"]

    response = plugin.pylsp_execute_command(
        config=config,
        workspace=workspace,
        command=command,
        arguments=arguments,
    )

    workspace._endpoint.request.assert_called_once_with(
        "workspace/applyEdit",
        {
            "edit": {
                "changes": {
                    document.uri: [
                        {
                            "range": {
                                "start": {"line": 3, "character": 0},
                                "end": {"line": 4, "character": 0},
                            },
                            "newText": "replacement text",
                        },
                    ],
                },
            },
        },
    )
