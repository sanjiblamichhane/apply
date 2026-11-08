"""The grant pack's fields: an organisation (or a researcher) that applies, and a funding opportunity."""

from typing import Annotated

from pydantic import BaseModel, ConfigDict, StringConstraints

from ..base import labelled as L

Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Medium = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100_000)]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Programme(_Strict):
    name: Short = L("Name", "नाम")
    description: Medium = L("What it does", "यसले के गर्छ", default="", long=True)
    beneficiaries: Short = L("Who it serves", "कसलाई सेवा", default="")
    results: Medium = L("Results so far", "हालसम्मका नतिजा", default="", long=True)


class PastGrant(_Strict):
    funder: Short = L("Funder", "अनुदानदाता")
    title: Short = L("What it funded", "केका लागि", default="")
    year: Short = L("Year", "वर्ष", default="")
    amount: Short = L("Amount", "रकम", default="")
    outcome: Medium = L("What it achieved", "के हासिल भयो", default="", long=True)


class Person(_Strict):
    name: Short = L("Name", "नाम")
    role: Short = L("Role", "भूमिका")
    background: Medium = L("Background", "पृष्ठभूमि", default="", long=True)


class GrantProfile(_Strict):
    """What a letter or narrative may say about the applicant. Nothing else gets claimed."""

    legal_name: Short = L("Legal name", "कानुनी नाम", default="")
    registration_numbers: list[Short] = L(
        "Registration numbers (EIN, UEI, charity)",
        "दर्ता नम्बरहरू (EIN, UEI, परोपकारी)",
        default_factory=list,
        max_length=20,
    )
    mission: Medium = L("Mission", "उद्देश्य", default="", long=True)
    location: Short = L("Where you work", "काम गर्ने ठाउँ", default="")
    email: Short = L("Email", "इमेल", default="")
    phone: Short = L("Phone", "फोन", default="")
    website: Short = L("Website", "वेबसाइट", default="")
    programmes: list[Programme] = L("Programmes", "कार्यक्रमहरू", default_factory=list, max_length=30)
    past_grants: list[PastGrant] = L("Past grants", "पहिलेका अनुदानहरू", default_factory=list, max_length=50)
    team: list[Person] = L("Key people", "मुख्य व्यक्तिहरू", default_factory=list, max_length=30)
    annual_budget: Short = L("Annual budget", "वार्षिक बजेट", default="")


class GrantOpportunity(_Strict):
    """A funding opportunity. Every field may be empty: a notice or the model may not say."""

    title: Short = L("Title", "शीर्षक", default="")
    funder: Short = L("Funder", "अनुदानदाता", default="")
    programme: Short = L("Programme", "कार्यक्रम", default="")
    number: Short = L("Opportunity number", "अवसर नम्बर", default="")
    description_markdown: Long = L("What it funds", "केका लागि अनुदान", default="", long=True)
    award_ceiling: Short = L("Largest award", "अधिकतम रकम", default="")
    award_floor: Short = L("Smallest award", "न्यूनतम रकम", default="")
    closing_date: Short = L("Closing date", "अन्तिम मिति", default="")
    eligibility: Medium = L("Who may apply", "को आवेदन दिन सक्छ", default="", long=True)
    assistance_listings: Short = L("Assistance listings (CFDA)", "सहायता सूची (CFDA)", default="")
    contact: Medium = L("Contact", "सम्पर्क", default="")
