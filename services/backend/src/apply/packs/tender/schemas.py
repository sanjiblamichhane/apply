"""The tender pack's fields: an organisation that bids, and a public tender notice."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from ..base import labelled as L

Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Medium = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100_000)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class PastContract(_Strict):
    client: Short = L("Client", "ग्राहक")
    title: Short = L("What it was", "के थियो")
    year: Short = L("Year", "वर्ष", default="")
    value: Short = L("Value", "मूल्य", default="")
    outcome: Medium = L("What you delivered", "तपाईंले के दिनुभयो", default="", long=True)


class TeamMember(_Strict):
    name: Short = L("Name", "नाम")
    role: Short = L("Role", "भूमिका")
    experience: Medium = L("Experience", "अनुभव", default="", long=True)


class TenderProfile(_Strict):
    """What a capability statement or tender response may say about the organisation. Nothing else gets claimed."""

    legal_name: Short = L("Legal name", "कानुनी नाम", default="")
    trading_name: Short = L("Trading name", "व्यापारिक नाम", default="")
    registration_numbers: list[Short] = L(
        "Company and tax numbers", "कम्पनी र कर नम्बरहरू", default_factory=list, max_length=20
    )
    address: Medium = L("Address", "ठेगाना", default="")
    email: Short = L("Email", "इमेल", default="")
    phone: Short = L("Phone", "फोन", default="")
    website: Short = L("Website", "वेबसाइट", default="")
    sectors: list[Short] = L(
        "Sectors and codes (CPV, NAICS)", "क्षेत्र र कोडहरू (CPV, NAICS)", default_factory=list, max_length=50
    )
    capabilities: list[Medium] = L("What you do", "तपाईंले गर्ने काम", default_factory=list, max_length=50)
    past_performance: list[PastContract] = L("Past contracts", "पहिलेका ठेक्काहरू", default_factory=list, max_length=50)
    certifications: list[Short] = L(
        "Certifications and accreditations", "प्रमाणपत्र र मान्यताहरू", default_factory=list, max_length=50
    )
    team: list[TeamMember] = L("Key people", "मुख्य व्यक्तिहरू", default_factory=list, max_length=30)
    employees: Short = L("How many people", "कति जना", default="")
    annual_turnover: Short = L("Annual turnover", "वार्षिक कारोबार", default="")


class TenderOpportunity(_Strict):
    """A public tender notice. Every field may be empty: a notice or the model may not say."""

    title: Short = L("Title", "शीर्षक", default="")
    buyer: Short = L("Buyer", "खरिदकर्ता", default="")
    reference: Short = L("Reference", "सन्दर्भ नम्बर", default="")
    description_markdown: Long = L("What's wanted", "के चाहिएको", default="", long=True)
    estimated_value: Short = L("Estimated value", "अनुमानित मूल्य", default="")
    closing_date: Short = L("Closing date", "अन्तिम मिति", default="")
    procedure: Short = L("Procedure", "प्रक्रिया", default="")
    classification: Short = L("Codes (CPV, NAICS)", "कोडहरू (CPV, NAICS)", default="")
    place_of_performance: Short = L("Where the work is", "काम हुने ठाउँ", default="")
    contact: Medium = L("Contact", "सम्पर्क", default="")
    how_to_respond: Medium = L("How to respond", "कसरी जवाफ दिने", default="")
