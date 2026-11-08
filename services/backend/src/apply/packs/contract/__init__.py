"""The contract pack: freelance and consulting work, pasted as a brief; proposals and statements of work; the
sales pipeline. No source: there's no open listings API whose terms allow it."""

from apply.i18n import label as en_ne

from ..base import DocumentTypeSpec, PipelineSpec, QuestionSpec, StageSpec
from ..simple import DeclarativePack
from .schemas import ContractOpportunity, ContractProfile

PIPELINE = PipelineSpec(
    key="contract",
    label=en_ne("Pipeline", "पाइपलाइन"),
    stages=(
        StageSpec("lead", en_ne("Lead", "सम्भावित"), "active"),
        StageSpec("proposal_sent", en_ne("Proposal sent", "प्रस्ताव पठाइएको"), "active", follow_up_after_days=5),
        StageSpec("negotiating", en_ne("Negotiating", "वार्ता"), "active", "negotiation"),
        StageSpec("won", en_ne("Won", "पाइयो"), "success", "decision", is_terminal=True),
        StageSpec("lost", en_ne("Lost", "पाइएन"), "failure", "decision", is_terminal=True),
    ),
)

DOCUMENT_TYPES = (
    DocumentTypeSpec(
        "proposal",
        en_ne("Proposal", "प्रस्ताव"),
        en_ne("Your answer to the client's brief.", "ग्राहकको विवरणको तपाईंको जवाफ।"),
        generatable=True,
        prompt="proposal.md",
    ),
    DocumentTypeSpec(
        "statement_of_work",
        en_ne("Statement of work", "कार्य विवरण"),
        en_ne("What will be delivered, by when, for how much.", "के, कहिलेसम्म, कतिमा दिइन्छ।"),
        generatable=True,
        prompt="statement_of_work.md",
    ),
    DocumentTypeSpec(
        "brief",
        en_ne("Client's brief", "ग्राहकको विवरण"),
        en_ne("The brief as the client sent it.", "ग्राहकले पठाएको विवरण।"),
        generatable=False,
    ),
)

QUESTIONS = (
    QuestionSpec("day_rate", en_ne("What is your day rate?", "तपाईंको दैनिक दर कति हो?")),
    QuestionSpec("availability", en_ne("When are you available?", "तपाईं कहिले उपलब्ध हुनुहुन्छ?")),
    QuestionSpec("company_number", en_ne("Company registration number", "कम्पनी दर्ता नम्बर")),
    QuestionSpec("insurance", en_ne("What insurance do you hold?", "तपाईंसँग कस्तो बीमा छ?")),
    QuestionSpec("portfolio", en_ne("Portfolio or website", "पोर्टफोलियो वा वेबसाइट"), "url"),
)


class ContractPack(DeclarativePack):
    key = "contract"
    version = "1"
    label = en_ne("Contracts", "ठेक्काहरू")
    description = en_ne(
        "Freelance and consulting work from clients' briefs.", "ग्राहकका विवरणबाट फ्रिल्यान्स र परामर्श काम।"
    )
    noun = en_ne("a freelance or consulting brief", "फ्रिल्यान्स वा परामर्श कामको विवरण")
    profile_kinds = ("individual", "organisation")
    profile_model = ContractProfile
    opportunity_model = ContractOpportunity
    document_types = DOCUMENT_TYPES
    pipeline = PIPELINE
    prompts_package = "apply.packs.contract.prompts"
    profile_document = "freelancer's resume, portfolio or service sheet"
    standard_questions = QUESTIONS
    submitted_stage = "proposal_sent"
    search_options = frozenset({"locations", "remote_only"})
    issuer_field = "client"
    name_field = "business_name"
    location_field = "location"
    remote_field = "workplace"
