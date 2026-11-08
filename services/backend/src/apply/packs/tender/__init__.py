"""The tender pack: public procurement notices, an organisation's capabilities, capability statements and tender
responses, and the bid pipeline."""

from apply.i18n import label as en_ne

from ..base import DocumentTypeSpec, PipelineSpec, StageSpec
from ..simple import DeclarativePack
from .questions import QUESTIONS
from .schemas import TenderOpportunity, TenderProfile
from .sources import SOURCES

PIPELINE = PipelineSpec(
    key="tender",
    label=en_ne("Bids", "बोलपत्रहरू"),
    stages=(
        StageSpec("identified", en_ne("Identified", "पहिचान गरिएको"), "active"),
        StageSpec("bid_decision", en_ne("Bid / no-bid", "बोलपत्र हाल्ने / नहाल्ने"), "active", "decision"),
        StageSpec("preparing", en_ne("Preparing", "तयारी"), "active", "document"),
        StageSpec("submitted", en_ne("Submitted", "पेस गरिएको"), "active", follow_up_after_days=14),
        StageSpec("clarification", en_ne("Clarification", "स्पष्टीकरण"), "active", "follow_up"),
        StageSpec("awarded", en_ne("Awarded", "प्राप्त"), "success", "decision", is_terminal=True),
        StageSpec("lost", en_ne("Not awarded", "प्राप्त भएन"), "failure", "decision", is_terminal=True),
        StageSpec("withdrawn", en_ne("Withdrawn", "फिर्ता लिइएको"), "failure", "decision", is_terminal=True),
    ),
)

DOCUMENT_TYPES = (
    DocumentTypeSpec(
        "capability_statement",
        en_ne("Capability statement", "क्षमता विवरण"),
        en_ne("What your organisation does, aimed at this buyer.", "तपाईंको संस्थाले के गर्छ, यो खरिदकर्तालाई लक्षित।"),
        generatable=True,
        prompt="capability_statement.md",
    ),
    DocumentTypeSpec(
        "tender_response",
        en_ne("Tender response", "बोलपत्र जवाफ"),
        en_ne("Your answer to the buyer's requirements.", "खरिदकर्ताका आवश्यकताको तपाईंको जवाफ।"),
        generatable=True,
        prompt="tender_response.md",
    ),
    DocumentTypeSpec(
        "tender_notice",
        en_ne("Tender notice", "बोलपत्र सूचना"),
        en_ne("The notice as it was when you bid.", "बोलपत्र हाल्दाको सूचना।"),
        generatable=False,
    ),
)


class TenderPack(DeclarativePack):
    key = "tender"
    version = "1"
    label = en_ne("Tenders", "बोलपत्रहरू")
    description = en_ne(
        "Public procurement: contracts governments and public bodies put out to tender.",
        "सार्वजनिक खरिद: सरकार र सार्वजनिक निकायले बोलपत्रमा राखेका ठेक्काहरू।",
    )
    noun = en_ne("a public tender", "सार्वजनिक बोलपत्र")
    profile_kinds = ("organisation",)
    profile_model = TenderProfile
    opportunity_model = TenderOpportunity
    document_types = DOCUMENT_TYPES
    pipeline = PIPELINE
    prompts_package = "apply.packs.tender.prompts"
    profile_document = "company's capability statement"
    sources = SOURCES
    standard_questions = QUESTIONS
    submitted_stage = "submitted"
    issuer_field = "buyer"
    name_field = "legal_name"
    location_field = "place_of_performance"
    reference_field = "reference"
