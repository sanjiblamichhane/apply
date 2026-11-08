"""Questions grant applications ask again and again."""

from apply.i18n import label as en_ne

from ..base import QuestionSpec

QUESTIONS = (
    QuestionSpec("ein", en_ne("Employer Identification Number (EIN)", "रोजगारदाता पहिचान नम्बर (EIN)")),
    QuestionSpec("uei", en_ne("Unique Entity ID (UEI)", "अद्वितीय निकाय परिचय (UEI)")),
    QuestionSpec("organisation_type", en_ne("What kind of organisation are you?", "तपाईं कस्तो संस्था हो?")),
    QuestionSpec("annual_budget", en_ne("What is your annual budget?", "तपाईंको वार्षिक बजेट कति हो?")),
    QuestionSpec("founded", en_ne("When was the organisation founded?", "संस्था कहिले स्थापना भयो?")),
    QuestionSpec(
        "authorised_representative", en_ne("Who is your authorised representative?", "तपाईंको अधिकृत प्रतिनिधि को हो?")
    ),
    QuestionSpec("website", en_ne("Website", "वेबसाइट"), "url"),
)
