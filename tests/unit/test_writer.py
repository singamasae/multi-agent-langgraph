"""Tests for the writer node contract."""

from langchain_core.language_models.fake_chat_models import GenericFakeChatModel
from langchain_core.messages import AIMessage

from app.agents.writer import build_writer_agent, make_writer_node
from tests.fakes import FakeWriterAgent


def test_writer_node_tags_output_with_writer_name():
    node = make_writer_node(FakeWriterAgent("written content"))

    result = node({"messages": [], "next": ""})

    messages = result["messages"]
    assert len(messages) == 1
    assert messages[0].content == "written content"
    assert messages[0].name == "Writer"


def test_build_writer_agent_composes_prompt_and_llm():
    # Exercise the real build path with a fake chat model (no network).
    llm = GenericFakeChatModel(messages=iter([AIMessage(content="drafted answer")]))
    agent = build_writer_agent(llm)

    result = agent.invoke({"messages": [("human", "write it")]})

    assert result.content == "drafted answer"
