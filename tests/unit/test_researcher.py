"""Tests for the researcher node contract and topic prompt."""

from langchain_core.messages import AIMessage, HumanMessage

from app.agents.researcher import build_topic_system_prompt, make_researcher_node
from tests.fakes import FakeReactAgent


def test_researcher_node_surfaces_only_the_last_message_tagged():
    agent = FakeReactAgent(
        [
            AIMessage(content="intermediate tool chatter"),
            AIMessage(content="- final summary"),
        ]
    )
    node = make_researcher_node(agent, name="ScienceResearcher")

    result = node({"messages": [HumanMessage(content="question")], "next": ""})

    messages = result["messages"]
    assert len(messages) == 1
    assert messages[0].content == "- final summary"
    assert messages[0].name == "ScienceResearcher"


def test_topic_system_prompt_embeds_the_focus():
    prompt = build_topic_system_prompt("technology — software, hardware, AI")

    assert "technology — software, hardware, AI" in prompt
    assert "search tool" in prompt
