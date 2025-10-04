"""
Macro and Political Research Contexts

Defines MarketContext for macro/political news research that doesn't require company information.
"""

from dataclasses import dataclass
from typing import List, Dict, Any
from enum import Enum
from .interfaces import ResearchContext, ResearchType


class MacroCategory(Enum):
    """Predefined macro/political news categories"""
    MONETARY_POLICY = "monetary_policy"
    FISCAL_POLICY = "fiscal_policy"
    GEOPOLITICS = "geopolitics"
    TRADE_POLICY = "trade_policy"
    INFLATION_ECONOMY = "inflation_economy"
    ENERGY_COMMODITIES = "energy_commodities"
    REGULATION = "regulation"
    ELECTIONS_POLITICS = "elections_politics"


@dataclass
class MarketContext(ResearchContext):
    """Context for macro/political news research"""
    category: MacroCategory
    topic_type: str  # "macro" or "political"
    focus_areas: List[str]
    display_name: str
    sector: str = None  # Optional sector categorization

    def get_research_type(self) -> ResearchType:
        if self.topic_type == "political":
            return ResearchType.POLITICAL
        return ResearchType.MACRO

    def get_display_name(self) -> str:
        return self.display_name

    def get_search_keywords(self) -> List[str]:
        """Generate search keywords for this macro category"""
        keywords = [self.display_name]
        keywords.extend(self.focus_areas)
        return keywords

    def get_focus_areas(self) -> List[str]:
        return self.focus_areas

    def should_use_earnings(self) -> bool:
        """Macro topics don't use earnings transcripts"""
        return False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "category": self.category.value,
            "topic_type": self.topic_type,
            "display_name": self.display_name,
            "focus_areas": self.focus_areas,
            "sector": self.sector,
            "research_type": self.get_research_type().value
        }


# Predefined macro research contexts
PREDEFINED_MACRO_CONTEXTS = {
    MacroCategory.MONETARY_POLICY: MarketContext(
        category=MacroCategory.MONETARY_POLICY,
        topic_type="macro",
        display_name="Federal Reserve & Monetary Policy",
        sector="Monetary Policy",
        focus_areas=[
            "Federal Reserve interest rate decisions",
            "Fed communications and forward guidance",
            "Quantitative easing or tightening",
            "Central bank policy changes globally",
            "Inflation targeting strategies"
        ]
    ),

    MacroCategory.FISCAL_POLICY: MarketContext(
        category=MacroCategory.FISCAL_POLICY,
        topic_type="macro",
        display_name="Government Spending & Fiscal Policy",
        sector="Fiscal Policy",
        focus_areas=[
            "Federal budget proposals and debates",
            "Infrastructure spending initiatives",
            "Tax policy changes",
            "Government stimulus programs",
            "Debt ceiling negotiations"
        ]
    ),

    MacroCategory.GEOPOLITICS: MarketContext(
        category=MacroCategory.GEOPOLITICS,
        topic_type="political",
        display_name="Geopolitical Events & International Relations",
        sector="Geopolitics",
        focus_areas=[
            "International conflicts and tensions",
            "Diplomatic negotiations",
            "Sanctions and trade restrictions",
            "Military actions and defense policy",
            "Global alliance shifts"
        ]
    ),

    MacroCategory.TRADE_POLICY: MarketContext(
        category=MacroCategory.TRADE_POLICY,
        topic_type="macro",
        display_name="Trade Policy & Tariffs",
        sector="Trade",
        focus_areas=[
            "Tariff announcements and changes",
            "Trade agreement negotiations",
            "Export/import restrictions",
            "Supply chain disruptions",
            "Trade war developments"
        ]
    ),

    MacroCategory.INFLATION_ECONOMY: MarketContext(
        category=MacroCategory.INFLATION_ECONOMY,
        topic_type="macro",
        display_name="Inflation & Economic Indicators",
        sector="Economy",
        focus_areas=[
            "CPI and inflation reports",
            "Employment and jobs data",
            "GDP growth and recession indicators",
            "Consumer spending trends",
            "Manufacturing and industrial production"
        ]
    ),

    MacroCategory.ENERGY_COMMODITIES: MarketContext(
        category=MacroCategory.ENERGY_COMMODITIES,
        topic_type="macro",
        display_name="Energy Markets & Commodities",
        sector="Energy",
        focus_areas=[
            "Oil and gas price movements",
            "OPEC decisions and production",
            "Energy transition policies",
            "Commodity price volatility",
            "Strategic petroleum reserve actions"
        ]
    ),

    MacroCategory.REGULATION: MarketContext(
        category=MacroCategory.REGULATION,
        topic_type="macro",
        display_name="Financial Regulation & Policy",
        sector="Regulation",
        focus_areas=[
            "Banking regulation changes",
            "SEC enforcement actions",
            "Antitrust investigations",
            "Cryptocurrency regulation",
            "Financial system stress tests"
        ]
    ),

    MacroCategory.ELECTIONS_POLITICS: MarketContext(
        category=MacroCategory.ELECTIONS_POLITICS,
        topic_type="political",
        display_name="Elections & Political Developments",
        sector="Politics",
        focus_areas=[
            "Presidential and congressional elections",
            "Policy proposals from candidates",
            "Political polling and predictions",
            "Legislative battles and votes",
            "Political appointments and nominations"
        ]
    )
}


def get_all_macro_contexts() -> List[MarketContext]:
    """Get all predefined macro research contexts"""
    return list(PREDEFINED_MACRO_CONTEXTS.values())


def get_macro_context_by_category(category: MacroCategory) -> MarketContext:
    """Get specific macro context by category"""
    return PREDEFINED_MACRO_CONTEXTS[category]
