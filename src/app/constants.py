"""Single source of truth for the agent roster.

Everything that needs to know "which workers exist" — the supervisor's routing
prompt, the structured-output schema, and the graph's conditional edges — derives
from :class:`AgentName` and the :data:`RESEARCH_TOPICS` registry here. The
researcher roster is a set of *topic specialists*: the supervisor analyses the
request and routes to the best-fit specialist(s), which all share the same ReAct
implementation and differ only by a topic-focused system prompt.

Adding or renaming a topic is a change in this file (plus the specialist's prompt,
which is generated from its description) — the enum, ``MEMBERS``, the supervisor
prompt, and the graph nodes all derive from what is declared here.
"""

from enum import Enum


class AgentName(str, Enum):
    """Names of the worker agents managed by the supervisor.

    Subclasses ``str`` (rather than ``enum.StrEnum``, which is 3.11+) so the
    values are usable directly as LangGraph node keys and message ``name`` tags.

    The six ``*_RESEARCHER`` members are topic specialists; ``WRITER`` composes
    the final answer from whatever research the specialists gathered.
    """

    SCIENCE_RESEARCHER = "ScienceResearcher"
    FOOD_BEVERAGE_RESEARCHER = "FoodBeverageResearcher"
    TECHNOLOGY_RESEARCHER = "TechnologyResearcher"
    AUTOMOTIVE_RESEARCHER = "AutomotiveResearcher"
    ART_CULTURE_RESEARCHER = "ArtCultureResearcher"
    ENVIRONMENT_SOCIAL_RESEARCHER = "EnvironmentSocialResearcher"
    WRITER = "Writer"


# Sentinel the supervisor returns when the workflow is complete.
FINISH = "FINISH"

# Topic registry: researcher name -> one-line focus description. This is the
# source of truth for the specialist roster. The supervisor lists these to
# decide where to route, and each specialist's system prompt is built from its
# description. Keys must be AgentName values (guarded by test_constants).
RESEARCH_TOPICS: dict[str, str] = {
    AgentName.SCIENCE_RESEARCHER.value: (
        "science and academic research — physics, biology, chemistry, space, "
        "mathematics, health and medicine"
    ),
    AgentName.FOOD_BEVERAGE_RESEARCHER.value: (
        "food and beverages — cuisine, cooking, recipes, ingredients, nutrition, "
        "restaurants and drinks"
    ),
    AgentName.TECHNOLOGY_RESEARCHER.value: (
        "technology — software, hardware, AI, gadgets, the internet, startups and "
        "computing"
    ),
    AgentName.AUTOMOTIVE_RESEARCHER.value: (
        "automotive — cars, motorcycles, EVs, engines, the motor industry and "
        "vehicle reviews"
    ),
    AgentName.ART_CULTURE_RESEARCHER.value: (
        "art and culture — visual arts, music, film, literature, history, "
        "heritage and entertainment"
    ),
    AgentName.ENVIRONMENT_SOCIAL_RESEARCHER.value: (
        "environment and society — climate, sustainability, ecology, social "
        "issues, politics and community"
    ),
}

# Researcher roster in declaration order (registry insertion order).
RESEARCHER_MEMBERS: list[str] = list(RESEARCH_TOPICS)

# Deterministic fallback the supervisor uses when a request fits no clear topic
# or the router tries to skip research. The first specialist in the roster;
# change the registry order (or this line) to pick a different default.
DEFAULT_RESEARCHER: str = RESEARCHER_MEMBERS[0]

# Worker roster in declaration order — the canonical list of members
# (every topic specialist, then the writer).
MEMBERS: list[str] = [*RESEARCHER_MEMBERS, AgentName.WRITER.value]

# Every value the supervisor is allowed to route to (workers + FINISH).
ROUTE_OPTIONS: list[str] = [FINISH, *MEMBERS]
