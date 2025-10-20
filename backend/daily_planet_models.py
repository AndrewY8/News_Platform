"""
Daily Planet Database Models
Enhanced user preferences, layout customization, and personalization tables
"""

from sqlalchemy import (
    Column,
    String,
    Integer,
    Boolean,
    Float,
    DateTime,
    Text,
    ForeignKey,
    Enum as SQLEnum,
    JSON,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import enum

Base = declarative_base()


# Enums for type safety
class RegionType(str, enum.Enum):
    US = "US"
    EU = "EU"
    APAC = "APAC"
    GLOBAL = "Global"


class ReadingLevel(str, enum.Enum):
    QUICK = "quick"
    STANDARD = "standard"
    IN_DEPTH = "in-depth"


class UpdateFrequency(str, enum.Enum):
    REALTIME = "realtime"
    HOURLY = "hourly"
    DAILY = "daily"


class ThemeType(str, enum.Enum):
    LIGHT = "light"
    DARK = "dark"
    NEWSPAPER = "newspaper"


class TopicType(str, enum.Enum):
    INDUSTRY = "industry"
    THEME = "theme"
    CUSTOM = "custom"


class SectionType(str, enum.Enum):
    PORTFOLIO = "portfolio"
    INDUSTRY = "industry"
    BREAKING = "breaking"
    MARKET_ANALYSIS = "market_analysis"
    MACRO_POLITICAL = "macro_political"
    CUSTOM = "custom"


class InteractionType(str, enum.Enum):
    CLICK = "click"
    READ = "read"
    REMOVE = "remove"
    SAVE = "save"
    SHARE = "share"


class ExclusionType(str, enum.Enum):
    TICKER = "ticker"
    TOPIC = "topic"
    SOURCE = "source"
    KEYWORD = "keyword"


class UserPreference(Base):
    """Store user-level preferences for The Daily Planet"""
    __tablename__ = "user_preferences"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, unique=True, index=True)

    # Geographic and content preferences
    region = Column(SQLEnum(RegionType), default=RegionType.GLOBAL)
    reading_level = Column(SQLEnum(ReadingLevel), default=ReadingLevel.STANDARD)
    update_frequency = Column(SQLEnum(UpdateFrequency), default=UpdateFrequency.REALTIME)

    # UI preferences
    layout_density = Column(Integer, default=2)  # 1, 2, or 3 columns
    theme = Column(SQLEnum(ThemeType), default=ThemeType.LIGHT)

    # Feature flags
    show_breaking_news = Column(Boolean, default=True)
    show_market_snapshot = Column(Boolean, default=True)
    enable_ai_learning = Column(Boolean, default=True)

    # Onboarding
    onboarding_completed = Column(Boolean, default=False)
    onboarding_completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User", back_populates="daily_planet_preferences")
    topics = relationship("UserTopic", back_populates="user_preference", cascade="all, delete-orphan")
    layout_sections = relationship("UserLayoutSection", back_populates="user_preference", cascade="all, delete-orphan")
    exclusions = relationship("ExcludedContent", back_populates="user_preference", cascade="all, delete-orphan")


class UserTopic(Base):
    """User's topic interests with priority weighting"""
    __tablename__ = "user_topics"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    preference_id = Column(String, ForeignKey("user_preferences.id"), nullable=False)

    # Topic details
    topic_name = Column(String, nullable=False)
    topic_type = Column(SQLEnum(TopicType), default=TopicType.INDUSTRY)

    # Priority for weighting (1-5, higher = more important)
    priority = Column(Integer, default=3)

    # Active/inactive toggle
    is_active = Column(Boolean, default=True)

    # Metadata
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    user_preference = relationship("UserPreference", back_populates="topics")


class UserLayoutSection(Base):
    """User's customized layout sections with order and configuration"""
    __tablename__ = "user_layout_sections"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    preference_id = Column(String, ForeignKey("user_preferences.id"), nullable=False)

    # Section identification
    section_id = Column(String, nullable=False, unique=True)  # e.g., "portfolio-1", "tech-news"
    section_type = Column(SQLEnum(SectionType), nullable=False)
    section_name = Column(String, nullable=False)

    # Display settings
    display_order = Column(Integer, default=0)
    is_visible = Column(Boolean, default=True)

    # Section-specific configuration (JSON)
    # Examples:
    # - For PORTFOLIO: {"tickers": ["AAPL", "GOOGL"], "show_charts": true}
    # - For INDUSTRY: {"industry": "Technology", "article_limit": 10}
    # - For CUSTOM: {"keywords": ["AI", "Machine Learning"], "sources": ["TechCrunch"]}
    config_json = Column(JSON, default={})

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    user = relationship("User")
    user_preference = relationship("UserPreference", back_populates="layout_sections")


class ExcludedContent(Base):
    """Content that user wants to exclude from their feed"""
    __tablename__ = "excluded_content"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    preference_id = Column(String, ForeignKey("user_preferences.id"), nullable=False)

    # Exclusion details
    exclusion_type = Column(SQLEnum(ExclusionType), nullable=False)
    exclusion_value = Column(String, nullable=False)

    # Optional reason
    reason = Column(String, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    user_preference = relationship("UserPreference", back_populates="exclusions")


class EnhancedUserInteraction(Base):
    """Enhanced user interactions with articles for learning"""
    __tablename__ = "enhanced_user_interactions"

    id = Column(String, primary_key=True, index=True)
    user_id = Column(String, ForeignKey("users.id"), nullable=False, index=True)
    article_id = Column(String, ForeignKey("articles.id"), nullable=False, index=True)

    # Interaction details
    interaction_type = Column(SQLEnum(InteractionType), nullable=False)

    # Reading metrics
    duration_seconds = Column(Integer, default=0)  # Time spent on article
    scroll_depth = Column(Float, default=0.0)  # Percentage scrolled (0-1)

    # Removal reason (if interaction_type == REMOVE)
    removed_reason = Column(String, nullable=True)  # 'not_interested', 'irrelevant', 'poor_quality', etc.

    # Context at time of interaction
    article_category = Column(String, nullable=True)
    article_tags = Column(Text, nullable=True)  # JSON string
    article_source = Column(String, nullable=True)

    # Timestamp
    timestamp = Column(DateTime, default=datetime.utcnow)

    # Relationships
    user = relationship("User")
    article = relationship("Article")


# Helper functions for creating default sections
def get_default_sections(user_id: str, preference_id: str) -> list:
    """Generate default layout sections for new users"""
    import uuid

    sections = [
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "preference_id": preference_id,
            "section_id": "hero-section",
            "section_type": SectionType.BREAKING,
            "section_name": "Above the Fold",
            "display_order": 0,
            "is_visible": True,
            "config_json": {"article_limit": 1, "show_full_preview": True}
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "preference_id": preference_id,
            "section_id": "portfolio-news",
            "section_type": SectionType.PORTFOLIO,
            "section_name": "My Portfolio",
            "display_order": 1,
            "is_visible": True,
            "config_json": {"article_limit": 15, "show_charts": True}
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "preference_id": preference_id,
            "section_id": "market-analysis",
            "section_type": SectionType.MARKET_ANALYSIS,
            "section_name": "Market Analysis",
            "display_order": 2,
            "is_visible": True,
            "config_json": {"article_limit": 10}
        },
        {
            "id": str(uuid.uuid4()),
            "user_id": user_id,
            "preference_id": preference_id,
            "section_id": "breaking-news",
            "section_type": SectionType.BREAKING,
            "section_name": "Breaking News",
            "display_order": 3,
            "is_visible": True,
            "config_json": {"article_limit": 8, "max_age_hours": 24}
        },
    ]

    return sections


def get_default_topics() -> list:
    """Get default topic suggestions"""
    return [
        {"name": "Technology", "type": TopicType.INDUSTRY, "priority": 3},
        {"name": "Healthcare", "type": TopicType.INDUSTRY, "priority": 3},
        {"name": "Finance", "type": TopicType.INDUSTRY, "priority": 3},
        {"name": "Energy", "type": TopicType.INDUSTRY, "priority": 3},
        {"name": "Consumer", "type": TopicType.INDUSTRY, "priority": 3},
        {"name": "Artificial Intelligence", "type": TopicType.THEME, "priority": 3},
        {"name": "Climate Change", "type": TopicType.THEME, "priority": 3},
        {"name": "Cryptocurrency", "type": TopicType.THEME, "priority": 3},
    ]
