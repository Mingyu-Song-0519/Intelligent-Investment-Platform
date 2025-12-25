"""Dashboard Views 패키지"""
from .profile_assessment_view import (
    show_assessment_page,
    render_investment_profile_tab,
    get_assessment_service
)
from .ranking_view import (
    show_ranking_page,
    show_recommendation_page,
    render_ranking_tab
)

__all__ = [
    "show_assessment_page",
    "render_investment_profile_tab",
    "get_assessment_service",
    "show_ranking_page",
    "show_recommendation_page",
    "render_ranking_tab"
]
