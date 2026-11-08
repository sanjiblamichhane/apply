"""The grant pack: funding opportunities, an applicant's mission and track record, letters of inquiry and project
narratives, and the funding pipeline."""

from apply.i18n import label as en_ne

from ..base import DocumentTypeSpec, PipelineSpec, StageSpec
from ..simple import DeclarativePack
from .questions import QUESTIONS
from .schemas import GrantOpportunity, GrantProfile
from .sources import SOURCES

PIPELINE = PipelineSpec(
    key="grant",
    label=en_ne("Funding", "अनुदान"),
    stages=(
        StageSpec("prospect", en_ne("Prospect", "सम्भावित"), "active"),
        StageSpec("drafting", en_ne("Drafting", "मस्यौदा"), "active", "document"),
        StageSpec("submitted", en_ne("Submitted", "पेस गरिएको"), "active", follow_up_after_days=30),
        StageSpec("under_review", en_ne("Under review", "समीक्षामा"), "active", expected_duration_days=60),
        StageSpec("awarded", en_ne("Awarded", "प्राप्त"), "success", "decision", is_terminal=True),
        StageSpec("declined", en_ne("Declined", "अस्वीकृत"), "failure", "decision", is_terminal=True),
        StageSpec("withdrawn", en_ne("Withdrawn", "फिर्ता लिइएको"), "failure", "decision", is_terminal=True),
    ),
)

DOCUMENT_TYPES = (
    DocumentTypeSpec(
        "letter_of_inquiry",
        en_ne("Letter of inquiry", "जिज्ञासा पत्र"),
        en_ne("A short first letter to the funder.", "अनुदानदातालाई छोटो पहिलो पत्र।"),
        generatable=True,
        prompt="letter_of_inquiry.md",
        layout="letter",
    ),
    DocumentTypeSpec(
        "project_narrative",
        en_ne("Project narrative", "परियोजना विवरण"),
        en_ne("What you'll do, why, and how: the heart of the proposal.", "तपाईं के, किन र कसरी गर्नुहुन्छ: प्रस्तावको मुटु।"),
        generatable=True,
        prompt="project_narrative.md",
    ),
    DocumentTypeSpec(
        "guidelines",
        en_ne("Funder's guidelines", "अनुदानदाताका निर्देशिका"),
        en_ne("The guidelines as they were when you apply.", "आवेदन दिँदाका निर्देशिका।"),
        generatable=False,
    ),
)


class GrantPack(DeclarativePack):
    key = "grant"
    version = "1"
    label = en_ne("Grants", "अनुदानहरू")
    description = en_ne(
        "Funding from governments and foundations, for organisations and researchers.",
        "सरकार र प्रतिष्ठानहरूबाट संस्था र अनुसन्धानकर्ताका लागि अनुदान।",
    )
    noun = en_ne("a grant", "अनुदान")
    profile_kinds = ("organisation", "individual")
    profile_model = GrantProfile
    opportunity_model = GrantOpportunity
    document_types = DOCUMENT_TYPES
    pipeline = PIPELINE
    prompts_package = "apply.packs.grant.prompts"
    profile_document = "organisation's profile or annual report"
    sources = SOURCES
    standard_questions = QUESTIONS
    submitted_stage = "submitted"
    issuer_field = "funder"
    name_field = "legal_name"
    reference_field = "number"
