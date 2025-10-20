"""
Daily Planet API Routes
Handles user preferences, layout customization, topics, and exclusions
"""

import uuid
import json
import logging
from datetime import datetime
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field
import google.generativeai as genai

from daily_planet_models import (
    UserPreference,
    UserTopic,
    UserLayoutSection,
    ExcludedContent,
    EnhancedUserInteraction,
    RegionType,
    ReadingLevel,
    UpdateFrequency,
    ThemeType,
    TopicType,
    SectionType,
    InteractionType,
    ExclusionType,
    get_default_sections,
    get_default_topics,
)

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/daily-planet", tags=["daily-planet"])


# ===========================
# Pydantic Models (Request/Response)
# ===========================

class PreferenceUpdate(BaseModel):
    region: Optional[str] = None
    reading_level: Optional[str] = None
    update_frequency: Optional[str] = None
    layout_density: Optional[int] = Field(None, ge=1, le=3)
    theme: Optional[str] = None
    show_breaking_news: Optional[bool] = None
    show_market_snapshot: Optional[bool] = None
    enable_ai_learning: Optional[bool] = None


class TopicCreate(BaseModel):
    topic_name: str
    topic_type: str = "industry"
    priority: int = Field(3, ge=1, le=5)


class TopicUpdate(BaseModel):
    priority: Optional[int] = Field(None, ge=1, le=5)
    is_active: Optional[bool] = None


class SectionCreate(BaseModel):
    section_type: str
    section_name: str
    config_json: Dict[str, Any] = {}


class SectionUpdate(BaseModel):
    section_name: Optional[str] = None
    is_visible: Optional[bool] = None
    config_json: Optional[Dict[str, Any]] = None


class SectionReorder(BaseModel):
    section_orders: List[Dict[str, int]]  # [{"section_id": "abc", "display_order": 0}, ...]


class ExclusionCreate(BaseModel):
    exclusion_type: str
    exclusion_value: str
    reason: Optional[str] = None


class OnboardingData(BaseModel):
    region: str = "Global"
    reading_level: str = "standard"
    topics: List[str] = []
    tickers: List[str] = []
    layout_density: int = 2


class NaturalLanguagePreferenceRequest(BaseModel):
    message: str
    user_id: Optional[str] = None


class ArticleRemoval(BaseModel):
    reason: Optional[str] = "not_interested"
    article_category: Optional[str] = None
    article_tags: Optional[List[str]] = None
    article_source: Optional[str] = None


class ReadTracking(BaseModel):
    duration_seconds: int = 0
    scroll_depth: float = 0.0


# ===========================
# Helper Functions
# ===========================

def get_or_create_user_preference(db: Session, user_id: str) -> UserPreference:
    """Get existing user preference or create new one with defaults"""
    preference = db.query(UserPreference).filter(UserPreference.user_id == user_id).first()

    if not preference:
        # Create new preference
        preference_id = str(uuid.uuid4())
        preference = UserPreference(
            id=preference_id,
            user_id=user_id,
            region=RegionType.GLOBAL,
            reading_level=ReadingLevel.STANDARD,
            update_frequency=UpdateFrequency.REALTIME,
            layout_density=2,
            theme=ThemeType.LIGHT,
            onboarding_completed=False,
        )
        db.add(preference)
        db.commit()
        db.refresh(preference)

        # Create default sections
        default_sections = get_default_sections(user_id, preference_id)
        for section_data in default_sections:
            section = UserLayoutSection(**section_data)
            db.add(section)

        db.commit()

    return preference


# ===========================
# User Preferences Endpoints
# ===========================

@router.get("/preferences")
async def get_user_preferences(
    request: Request,
    db: Session = Depends(lambda: None)  # Will be injected by main app
):
    """Get user's Daily Planet preferences"""
    try:
        # TODO: Get user_id from auth token
        user_id = "demo_user_1"  # Placeholder

        preference = get_or_create_user_preference(db, user_id)

        return {
            "id": preference.id,
            "user_id": preference.user_id,
            "region": preference.region.value if preference.region else "Global",
            "reading_level": preference.reading_level.value if preference.reading_level else "standard",
            "update_frequency": preference.update_frequency.value if preference.update_frequency else "realtime",
            "layout_density": preference.layout_density,
            "theme": preference.theme.value if preference.theme else "light",
            "show_breaking_news": preference.show_breaking_news,
            "show_market_snapshot": preference.show_market_snapshot,
            "enable_ai_learning": preference.enable_ai_learning,
            "onboarding_completed": preference.onboarding_completed,
            "created_at": preference.created_at.isoformat() if preference.created_at else None,
            "updated_at": preference.updated_at.isoformat() if preference.updated_at else None,
        }
    except Exception as e:
        logger.error(f"Error fetching preferences: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/preferences")
async def update_user_preferences(
    preference_update: PreferenceUpdate,
    db: Session = Depends(lambda: None)
):
    """Update user's Daily Planet preferences"""
    try:
        user_id = "demo_user_1"  # TODO: Get from auth

        preference = get_or_create_user_preference(db, user_id)

        # Update fields if provided
        if preference_update.region:
            preference.region = RegionType(preference_update.region)
        if preference_update.reading_level:
            preference.reading_level = ReadingLevel(preference_update.reading_level)
        if preference_update.update_frequency:
            preference.update_frequency = UpdateFrequency(preference_update.update_frequency)
        if preference_update.layout_density is not None:
            preference.layout_density = preference_update.layout_density
        if preference_update.theme:
            preference.theme = ThemeType(preference_update.theme)
        if preference_update.show_breaking_news is not None:
            preference.show_breaking_news = preference_update.show_breaking_news
        if preference_update.show_market_snapshot is not None:
            preference.show_market_snapshot = preference_update.show_market_snapshot
        if preference_update.enable_ai_learning is not None:
            preference.enable_ai_learning = preference_update.enable_ai_learning

        preference.updated_at = datetime.utcnow()

        db.commit()
        db.refresh(preference)

        return {"success": True, "message": "Preferences updated successfully"}
    except Exception as e:
        logger.error(f"Error updating preferences: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Topic Management Endpoints
# ===========================

@router.get("/topics")
async def get_user_topics(db: Session = Depends(lambda: None)):
    """Get user's topic interests"""
    try:
        user_id = "demo_user_1"

        preference = get_or_create_user_preference(db, user_id)

        topics = db.query(UserTopic).filter(
            UserTopic.user_id == user_id
        ).order_by(UserTopic.priority.desc(), UserTopic.topic_name).all()

        return {
            "topics": [
                {
                    "id": topic.id,
                    "topic_name": topic.topic_name,
                    "topic_type": topic.topic_type.value if topic.topic_type else "industry",
                    "priority": topic.priority,
                    "is_active": topic.is_active,
                    "created_at": topic.created_at.isoformat() if topic.created_at else None,
                }
                for topic in topics
            ],
            "suggested_topics": get_default_topics()
        }
    except Exception as e:
        logger.error(f"Error fetching topics: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/topics")
async def add_user_topic(
    topic_data: TopicCreate,
    db: Session = Depends(lambda: None)
):
    """Add a new topic interest"""
    try:
        user_id = "demo_user_1"

        preference = get_or_create_user_preference(db, user_id)

        # Check if topic already exists
        existing = db.query(UserTopic).filter(
            UserTopic.user_id == user_id,
            UserTopic.topic_name == topic_data.topic_name
        ).first()

        if existing:
            return {"success": False, "message": "Topic already exists"}

        # Create new topic
        topic = UserTopic(
            id=str(uuid.uuid4()),
            user_id=user_id,
            preference_id=preference.id,
            topic_name=topic_data.topic_name,
            topic_type=TopicType(topic_data.topic_type),
            priority=topic_data.priority,
            is_active=True,
        )

        db.add(topic)
        db.commit()
        db.refresh(topic)

        return {
            "success": True,
            "topic": {
                "id": topic.id,
                "topic_name": topic.topic_name,
                "topic_type": topic.topic_type.value,
                "priority": topic.priority,
            }
        }
    except Exception as e:
        logger.error(f"Error adding topic: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/topics/{topic_id}")
async def update_user_topic(
    topic_id: str,
    topic_update: TopicUpdate,
    db: Session = Depends(lambda: None)
):
    """Update a topic's priority or active status"""
    try:
        user_id = "demo_user_1"

        topic = db.query(UserTopic).filter(
            UserTopic.id == topic_id,
            UserTopic.user_id == user_id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        if topic_update.priority is not None:
            topic.priority = topic_update.priority
        if topic_update.is_active is not None:
            topic.is_active = topic_update.is_active

        db.commit()

        return {"success": True, "message": "Topic updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating topic: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/topics/{topic_id}")
async def delete_user_topic(
    topic_id: str,
    db: Session = Depends(lambda: None)
):
    """Delete a topic interest"""
    try:
        user_id = "demo_user_1"

        topic = db.query(UserTopic).filter(
            UserTopic.id == topic_id,
            UserTopic.user_id == user_id
        ).first()

        if not topic:
            raise HTTPException(status_code=404, detail="Topic not found")

        db.delete(topic)
        db.commit()

        return {"success": True, "message": "Topic deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting topic: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Layout Section Endpoints
# ===========================

@router.get("/layout/sections")
async def get_layout_sections(db: Session = Depends(lambda: None)):
    """Get user's layout sections"""
    try:
        user_id = "demo_user_1"

        preference = get_or_create_user_preference(db, user_id)

        sections = db.query(UserLayoutSection).filter(
            UserLayoutSection.user_id == user_id
        ).order_by(UserLayoutSection.display_order).all()

        return {
            "sections": [
                {
                    "id": section.id,
                    "section_id": section.section_id,
                    "section_type": section.section_type.value if section.section_type else None,
                    "section_name": section.section_name,
                    "display_order": section.display_order,
                    "is_visible": section.is_visible,
                    "config_json": section.config_json or {},
                }
                for section in sections
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching layout sections: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/layout/sections")
async def create_layout_section(
    section_data: SectionCreate,
    db: Session = Depends(lambda: None)
):
    """Create a new layout section"""
    try:
        user_id = "demo_user_1"

        preference = get_or_create_user_preference(db, user_id)

        # Get max display_order
        max_order = db.query(UserLayoutSection).filter(
            UserLayoutSection.user_id == user_id
        ).count()

        # Create section
        section_id = f"{section_data.section_type}-{str(uuid.uuid4())[:8]}"

        section = UserLayoutSection(
            id=str(uuid.uuid4()),
            user_id=user_id,
            preference_id=preference.id,
            section_id=section_id,
            section_type=SectionType(section_data.section_type),
            section_name=section_data.section_name,
            display_order=max_order,
            is_visible=True,
            config_json=section_data.config_json,
        )

        db.add(section)
        db.commit()
        db.refresh(section)

        return {
            "success": True,
            "section": {
                "id": section.id,
                "section_id": section.section_id,
                "section_type": section.section_type.value,
                "section_name": section.section_name,
                "display_order": section.display_order,
            }
        }
    except Exception as e:
        logger.error(f"Error creating section: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.patch("/layout/sections/{section_id}")
async def update_layout_section(
    section_id: str,
    section_update: SectionUpdate,
    db: Session = Depends(lambda: None)
):
    """Update a layout section"""
    try:
        user_id = "demo_user_1"

        section = db.query(UserLayoutSection).filter(
            UserLayoutSection.section_id == section_id,
            UserLayoutSection.user_id == user_id
        ).first()

        if not section:
            raise HTTPException(status_code=404, detail="Section not found")

        if section_update.section_name:
            section.section_name = section_update.section_name
        if section_update.is_visible is not None:
            section.is_visible = section_update.is_visible
        if section_update.config_json is not None:
            section.config_json = section_update.config_json

        section.updated_at = datetime.utcnow()

        db.commit()

        return {"success": True, "message": "Section updated"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating section: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/layout/sections/reorder")
async def reorder_sections(
    reorder_data: SectionReorder,
    db: Session = Depends(lambda: None)
):
    """Reorder layout sections"""
    try:
        user_id = "demo_user_1"

        # Update display_order for each section
        for item in reorder_data.section_orders:
            section = db.query(UserLayoutSection).filter(
                UserLayoutSection.section_id == item["section_id"],
                UserLayoutSection.user_id == user_id
            ).first()

            if section:
                section.display_order = item["display_order"]
                section.updated_at = datetime.utcnow()

        db.commit()

        return {"success": True, "message": "Sections reordered"}
    except Exception as e:
        logger.error(f"Error reordering sections: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/layout/sections/{section_id}")
async def delete_layout_section(
    section_id: str,
    db: Session = Depends(lambda: None)
):
    """Delete a layout section"""
    try:
        user_id = "demo_user_1"

        section = db.query(UserLayoutSection).filter(
            UserLayoutSection.section_id == section_id,
            UserLayoutSection.user_id == user_id
        ).first()

        if not section:
            raise HTTPException(status_code=404, detail="Section not found")

        db.delete(section)
        db.commit()

        return {"success": True, "message": "Section deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting section: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Content Exclusion Endpoints
# ===========================

@router.get("/exclusions")
async def get_exclusions(db: Session = Depends(lambda: None)):
    """Get user's content exclusions"""
    try:
        user_id = "demo_user_1"

        exclusions = db.query(ExcludedContent).filter(
            ExcludedContent.user_id == user_id
        ).order_by(ExcludedContent.created_at.desc()).all()

        return {
            "exclusions": [
                {
                    "id": exc.id,
                    "exclusion_type": exc.exclusion_type.value if exc.exclusion_type else None,
                    "exclusion_value": exc.exclusion_value,
                    "reason": exc.reason,
                    "created_at": exc.created_at.isoformat() if exc.created_at else None,
                }
                for exc in exclusions
            ]
        }
    except Exception as e:
        logger.error(f"Error fetching exclusions: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/exclusions")
async def add_exclusion(
    exclusion_data: ExclusionCreate,
    db: Session = Depends(lambda: None)
):
    """Add a content exclusion"""
    try:
        user_id = "demo_user_1"

        preference = get_or_create_user_preference(db, user_id)

        # Check if exclusion already exists
        existing = db.query(ExcludedContent).filter(
            ExcludedContent.user_id == user_id,
            ExcludedContent.exclusion_type == ExclusionType(exclusion_data.exclusion_type),
            ExcludedContent.exclusion_value == exclusion_data.exclusion_value
        ).first()

        if existing:
            return {"success": False, "message": "Exclusion already exists"}

        # Create exclusion
        exclusion = ExcludedContent(
            id=str(uuid.uuid4()),
            user_id=user_id,
            preference_id=preference.id,
            exclusion_type=ExclusionType(exclusion_data.exclusion_type),
            exclusion_value=exclusion_data.exclusion_value,
            reason=exclusion_data.reason,
        )

        db.add(exclusion)
        db.commit()

        return {"success": True, "message": "Exclusion added"}
    except Exception as e:
        logger.error(f"Error adding exclusion: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/exclusions/{exclusion_id}")
async def delete_exclusion(
    exclusion_id: str,
    db: Session = Depends(lambda: None)
):
    """Delete a content exclusion"""
    try:
        user_id = "demo_user_1"

        exclusion = db.query(ExcludedContent).filter(
            ExcludedContent.id == exclusion_id,
            ExcludedContent.user_id == user_id
        ).first()

        if not exclusion:
            raise HTTPException(status_code=404, detail="Exclusion not found")

        db.delete(exclusion)
        db.commit()

        return {"success": True, "message": "Exclusion deleted"}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error deleting exclusion: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Article Interaction Endpoints
# ===========================

@router.post("/articles/{article_id}/remove")
async def remove_article(
    article_id: str,
    removal_data: ArticleRemoval,
    db: Session = Depends(lambda: None)
):
    """Track article removal for learning"""
    try:
        user_id = "demo_user_1"

        # Create interaction record
        interaction = EnhancedUserInteraction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            article_id=article_id,
            interaction_type=InteractionType.REMOVE,
            removed_reason=removal_data.reason,
            article_category=removal_data.article_category,
            article_tags=json.dumps(removal_data.article_tags) if removal_data.article_tags else None,
            article_source=removal_data.article_source,
        )

        db.add(interaction)
        db.commit()

        return {"success": True, "message": "Article removed and feedback recorded"}
    except Exception as e:
        logger.error(f"Error removing article: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/articles/{article_id}/track-read")
async def track_article_read(
    article_id: str,
    read_data: ReadTracking,
    db: Session = Depends(lambda: None)
):
    """Track article reading for learning"""
    try:
        user_id = "demo_user_1"

        # Create or update interaction record
        interaction = EnhancedUserInteraction(
            id=str(uuid.uuid4()),
            user_id=user_id,
            article_id=article_id,
            interaction_type=InteractionType.READ,
            duration_seconds=read_data.duration_seconds,
            scroll_depth=read_data.scroll_depth,
        )

        db.add(interaction)
        db.commit()

        return {"success": True}
    except Exception as e:
        logger.error(f"Error tracking read: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Onboarding Endpoint
# ===========================

@router.post("/onboarding/complete")
async def complete_onboarding(
    onboarding_data: OnboardingData,
    db: Session = Depends(lambda: None)
):
    """Complete onboarding and save all user preferences"""
    try:
        user_id = "demo_user_1"

        preference = get_or_create_user_preference(db, user_id)

        # Update preferences
        preference.region = RegionType(onboarding_data.region)
        preference.reading_level = ReadingLevel(onboarding_data.reading_level)
        preference.layout_density = onboarding_data.layout_density
        preference.onboarding_completed = True
        preference.onboarding_completed_at = datetime.utcnow()

        # Add topics
        for topic_name in onboarding_data.topics:
            existing = db.query(UserTopic).filter(
                UserTopic.user_id == user_id,
                UserTopic.topic_name == topic_name
            ).first()

            if not existing:
                topic = UserTopic(
                    id=str(uuid.uuid4()),
                    user_id=user_id,
                    preference_id=preference.id,
                    topic_name=topic_name,
                    topic_type=TopicType.INDUSTRY,
                    priority=3,
                )
                db.add(topic)

        db.commit()

        return {
            "success": True,
            "message": "Onboarding completed! Welcome to The Daily Planet.",
            "redirect_to": "/daily-planet"
        }
    except Exception as e:
        logger.error(f"Error completing onboarding: {e}", exc_info=True)
        db.rollback()
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Natural Language Preferences (Gemini-powered)
# ===========================

@router.post("/preferences/natural-language")
async def natural_language_preference(
    request_data: NaturalLanguagePreferenceRequest,
    db: Session = Depends(lambda: None)
):
    """Parse natural language preference request and update database"""
    try:
        user_id = request_data.user_id or "demo_user_1"
        message = request_data.message

        # Use Gemini to parse intent
        # TODO: Implement Gemini parsing logic
        # For now, return placeholder response

        return {
            "success": True,
            "message": "I understand you want to adjust your preferences. This feature is coming soon!",
            "parsed_intent": {
                "action": "unknown",
                "entities": [],
            },
            "confirmation": "Preference updated based on your request."
        }
    except Exception as e:
        logger.error(f"Error processing natural language preference: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


# ===========================
# Helper function to add routes to main app
# ===========================

def add_daily_planet_routes(app, get_db_dependency):
    """
    Add Daily Planet routes to the main FastAPI app

    Args:
        app: FastAPI application instance
        get_db_dependency: Database session dependency function
    """
    # Update router dependencies
    for route in router.routes:
        # Replace the placeholder dependency with actual DB dependency
        if hasattr(route, "dependencies"):
            route.dependencies = [Depends(get_db_dependency)]

    # Include router in app
    app.include_router(router)

    logger.info("✅ Daily Planet routes added successfully")
