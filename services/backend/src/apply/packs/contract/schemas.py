"""The contract pack's fields: a freelancer or consultancy, and a piece of work a client wants done."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from apply.i18n import label as en_ne

from ..base import labelled as L

Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Medium = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100_000)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Service(_Strict):
    name: Short = L("Service", "सेवा")
    description: Medium = L("What's included", "के समावेश छ", default="", long=True)
    rate: Short = L("Rate", "दर", default="")


class Project(_Strict):
    client: Short = L("Client", "ग्राहक")
    title: Short = L("What it was", "के थियो")
    year: Short = L("Year", "वर्ष", default="")
    outcome: Medium = L("What you delivered", "तपाईंले के दिनुभयो", default="", long=True)
    link: Short = L("Link", "लिङ्क", default="")


class ContractProfile(_Strict):
    """What a proposal may say about the freelancer or firm. Nothing else gets claimed."""

    business_name: Short = L("Business name", "व्यवसायको नाम", default="")
    email: Short = L("Email", "इमेल", default="")
    phone: Short = L("Phone", "फोन", default="")
    website: Short = L("Website", "वेबसाइट", default="")
    location: Short = L("Where you work from", "कहाँबाट काम गर्नुहुन्छ", default="")
    services: list[Service] = L("Services", "सेवाहरू", default_factory=list, max_length=30)
    skills: list[Short] = L("Skills and tools", "सीप र उपकरणहरू", default_factory=list, max_length=100)
    projects: list[Project] = L("Past projects", "पहिलेका परियोजनाहरू", default_factory=list, max_length=50)
    availability: Short = L("Availability", "उपलब्धता", default="")


Workplace = Literal["", "onsite", "hybrid", "remote"]


class ContractOpportunity(_Strict):
    """A piece of work. Every field may be empty: a brief or the model may not say."""

    title: Short = L("Title", "शीर्षक", default="")
    client: Short = L("Client", "ग्राहक", default="")
    description_markdown: Long = L("The brief", "विवरण", default="", long=True)
    deliverables: Medium = L("Deliverables", "दिनुपर्ने कुरा", default="", long=True)
    budget: Short = L("Budget", "बजेट", default="")
    duration: Short = L("How long", "कति समय", default="")
    start_date: Short = L("Start", "सुरु", default="")
    location: Short = L("Location", "स्थान", default="")
    workplace: Workplace = L(
        "Where the work is",
        "काम गर्ने ठाउँ",
        default="",
        options={
            "": en_ne("Not said", "भनिएको छैन"),
            "onsite": en_ne("On site", "साइटमा"),
            "hybrid": en_ne("Hybrid", "मिश्रित"),
            "remote": en_ne("Remote", "टाढाबाट"),
        },
    )
    contact: Medium = L("Contact", "सम्पर्क", default="")
