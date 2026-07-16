"""Tests for the researcher node contract."""

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.researcher import make_researcher_node
from tests.fakes import FakeReactAgent


def test_researcher_node_surfaces_only_the_last_message_tagged():
    agent = FakeReactAgent(
        [
            AIMessage(content="intermediate tool chatter"),
            AIMessage(content="- final summary"),
        ]
    )
    node = make_researcher_node(agent)

    result = node({"messages": [HumanMessage(content="question")], "next": ""})

    messages = result["messages"]
    assert len(messages) == 1
    assert messages[0].content == "- final summary"
    assert messages[0].name == "Researcher"
