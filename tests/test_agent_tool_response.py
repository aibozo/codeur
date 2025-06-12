import sys
from pathlib import Path
from unittest.mock import MagicMock

sys.path.insert(0, str(Path(__file__).parent.parent))

from src.coding_agent import CodingAgent
from src.coding_agent.models import CodeContext
from src.proto_gen import messages_pb2


def test_refine_context_tool_response_dict(monkeypatch):
    agent = CodingAgent(repo_path=".")
    agent.llm_client = MagicMock()

    response_dict = {"tool": "read_file", "args": {"path": "README.md"}}
    agent.llm_client.generate_with_json.return_value = response_dict

    executed = []

    def mock_execute_tool_call(tool_call, context):
        executed.append(tool_call)

    monkeypatch.setattr(agent, "_execute_tool_call", mock_execute_tool_call)

    task = messages_pb2.CodingTask()
    task.goal = "dummy"

    context = CodeContext(task_goal="dummy")
    agent._refine_context_with_tools(task, context)

    assert executed == [response_dict]
