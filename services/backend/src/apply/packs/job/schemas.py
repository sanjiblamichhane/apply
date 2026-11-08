"""The job pack's fields: a person's profile, and a job opening."""

from typing import Annotated, Literal

from pydantic import BaseModel, ConfigDict, StringConstraints

from apply.i18n import label as en_ne

from ..base import labelled as L

Short = Annotated[str, StringConstraints(strip_whitespace=True, max_length=300)]
Medium = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
Long = Annotated[str, StringConstraints(strip_whitespace=True, max_length=100_000)]
Url = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2048, pattern=r"^(https?://\S+)?$")]


class _Strict(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Link(_Strict):
    label: Short = L("Name", "नाम", default="")
    url: Url = L("Address", "ठेगाना")


class Experience(_Strict):
    title: Short = L("Title", "पद")
    organisation: Short = L("Organisation", "संस्था")
    start: Short = L("From", "देखि", default="")
    end: Short = L("Until (empty: still there)", "सम्म (खाली: अझै त्यहीँ)", default="")
    location: Short = L("Place", "ठाउँ", default="")
    highlights: list[Medium] = L("What you did", "तपाईंले गरेका काम", default_factory=list, max_length=40)


class Education(_Strict):
    qualification: Short = L("Qualification", "योग्यता")
    institution: Short = L("Institution", "संस्था")
    year: Short = L("Year", "वर्ष", default="")
    notes: Medium = L("Notes", "टिप्पणी", default="")


class JobProfile(_Strict):
    """Everything a resume or cover letter may say about the person. Nothing else gets claimed."""

    full_name: Short = L("Full name", "पूरा नाम", default="")
    email: Short = L("Email", "इमेल", default="")
    phone: Short = L("Phone", "फोन", default="")
    phone_country_code: Short = L("Phone country code (like +1)", "फोनको देश कोड (जस्तै +1)", default="")
    location: Short = L("Where you live", "बसोबास", default="")
    address_line1: Short = L("Address line 1", "ठेगाना लाइन १", default="")
    address_line2: Short = L("Address line 2", "ठेगाना लाइन २", default="")
    city: Short = L("City", "सहर", default="")
    region: Short = L("State, province or region", "प्रदेश वा क्षेत्र", default="")
    postal_code: Short = L("Postcode or ZIP", "हुलाक कोड", default="")
    country: Short = L("Country", "देश", default="")
    links: list[Link] = L("Links", "लिङ्कहरू", default_factory=list, max_length=20)
    skills: list[Short] = L("Skills", "सीपहरू", default_factory=list, max_length=200)
    experience: list[Experience] = L("Experience", "अनुभव", default_factory=list, max_length=50)
    education: list[Education] = L("Education", "शिक्षा", default_factory=list, max_length=20)
    certifications: list[Short] = L("Certifications", "प्रमाणपत्रहरू", default_factory=list, max_length=50)
    languages: list[Short] = L("Languages", "भाषाहरू", default_factory=list, max_length=20)
    work_authorization: Medium = L("Right to work", "काम गर्ने अनुमति", default="")


Workplace = Literal["", "onsite", "hybrid", "remote"]


class JobOpportunity(_Strict):
    """A job opening. Every field may be empty: a page or the model may not say."""

    job_title: Short = L("Job title", "पद", default="")
    company_name: Short = L("Company", "कम्पनी", default="")
    description_markdown: Long = L("Description", "विवरण", default="", long=True)
    location: Short = L("Location", "स्थान", default="")
    workplace: Workplace = L(
        "Where the work is",
        "काम गर्ने ठाउँ",
        default="",
        options={
            "": en_ne("Not said", "भनिएको छैन"),
            "onsite": en_ne("On site", "कार्यालयमा"),
            "hybrid": en_ne("Hybrid", "मिश्रित"),
            "remote": en_ne("Remote", "टाढाबाट"),
        },
    )
    employment_type: Short = L("Employment type", "रोजगारीको प्रकार", default="")
    salary_text: Short = L("Salary", "तलब", default="")
    visa_sponsorship_text: Medium = L("Visa sponsorship", "भिसा प्रायोजन", default="")
    hiring_manager: Short = L("Hiring manager", "भर्ना प्रबन्धक", default="")
