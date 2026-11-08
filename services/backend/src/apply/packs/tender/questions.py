"""Questions tender forms (selection questionnaires) ask again and again."""

from apply.i18n import label as en_ne

from ..base import QuestionSpec

YES_NO = (("yes", en_ne("Yes", "हो")), ("no", en_ne("No", "होइन")))

QUESTIONS = (
    QuestionSpec("company_number", en_ne("Company registration number", "कम्पनी दर्ता नम्बर")),
    QuestionSpec("vat_number", en_ne("VAT or tax number", "भ्याट वा कर नम्बर")),
    QuestionSpec("uei", en_ne("UEI or DUNS number", "UEI वा DUNS नम्बर")),
    QuestionSpec(
        "years_trading", en_ne("How many years have you been trading?", "तपाईं कति वर्षदेखि कारोबारमा हुनुहुन्छ?"), "number"
    ),
    QuestionSpec(
        "sme",
        en_ne("Are you a small or medium-sized enterprise (SME)?", "के तपाईं साना वा मझौला उद्यम (SME) हो?"),
        "yes_no",
        YES_NO,
    ),
    QuestionSpec("insurance", en_ne("What insurance cover do you hold?", "तपाईंसँग कस्तो बीमा छ?")),
    QuestionSpec(
        "quality_certifications",
        en_ne("Which quality or security certifications do you hold?", "तपाईंसँग कुन गुणस्तर वा सुरक्षा प्रमाणपत्र छन्?"),
    ),
    QuestionSpec("contact_name", en_ne("Who is the contact for this bid?", "यो बोलपत्रको सम्पर्क व्यक्ति को हो?")),
    QuestionSpec(
        "policies_url",
        en_ne(
            "Link to your policies (modern slavery, environment, equality)",
            "तपाईंका नीतिहरूको लिङ्क (आधुनिक दासत्व, वातावरण, समानता)",
        ),
        "url",
    ),
)
