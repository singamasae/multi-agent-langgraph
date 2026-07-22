"""Tests for the agent-roster single source of truth."""

from app.constants import (
    DEFAULT_RESEARCHER,
    FINISH,
    MEMBERS,
    RESEARCH_TOPICS,
    RESEARCHER_MEMBERS,
    ROUTE_OPTIONS,
    AgentName,
)


def test_members_are_derived_from_the_enum():
    # MEMBERS must stay in lock-step with the AgentName enum so the roster
    # has exactly one source of truth.
    assert MEMBERS == [member.value for member in AgentName]
    assert MEMBERS == [
        "ScienceResearcher",
        "FoodBeverageResearcher",
        "TechnologyResearcher",
        "AutomotiveResearcher",
        "ArtCultureResearcher",
        "EnvironmentSocialResearcher",
        "Writer",
    ]


def test_researcher_members_match_the_topic_registry():
    # The topic registry is the source of truth for the specialist roster.
    assert RESEARCHER_MEMBERS == list(RESEARCH_TOPICS)
    # Researchers are exactly the members minus the Writer.
    assert RESEARCHER_MEMBERS == MEMBERS[:-1]
    assert AgentName.WRITER.value not in RESEARCHER_MEMBERS
    # Every topic key is a real AgentName value with a non-empty description.
    valid = {member.value for member in AgentName}
    for name, description in RESEARCH_TOPICS.items():
        assert name in valid
        assert description.strip()


def test_default_researcher_is_a_specialist():
    assert DEFAULT_RESEARCHER in RESEARCHER_MEMBERS
    assert DEFAULT_RESEARCHER == RESEARCHER_MEMBERS[0]


def test_route_options_prepend_finish_to_members():
    assert ROUTE_OPTIONS == [FINISH, *MEMBERS]
    assert ROUTE_OPTIONS[0] == "FINISH"


def test_agent_name_behaves_as_a_string():
    # Because AgentName subclasses str, values compare/serialize as plain
    # strings, which is what LangGraph node keys and message names expect.
    assert AgentName.SCIENCE_RESEARCHER == "ScienceResearcher"
    assert f"{AgentName.WRITER}" == "Writer" or AgentName.WRITER.value == "Writer"
