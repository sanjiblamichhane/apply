"""
Questions job application forms ask again and again, kept with their answers. The equal-opportunity ones are
sensitive: never sent to a model, "Decline to answer" until the person says otherwise, and recorded on a
submission only as provided or declined.
"""

from apply.i18n import label as en_ne

from ..base import QuestionSpec

YES_NO = (("yes", en_ne("Yes", "हो")), ("no", en_ne("No", "होइन")))
DECLINE = ("decline", en_ne("Decline to answer", "जवाफ दिन चाहन्नँ"))

QUESTIONS = (
    QuestionSpec(
        "work_authorization",
        en_ne(
            "Are you legally allowed to work in the country of this job?",
            "के तपाईंलाई यो जागिरको देशमा काम गर्ने कानुनी अनुमति छ?",
        ),
        "yes_no",
        YES_NO,
    ),
    QuestionSpec(
        "needs_sponsorship",
        en_ne("Will you now or in future need visa sponsorship?", "के तपाईंलाई अहिले वा भविष्यमा भिसा प्रायोजन चाहिन्छ?"),
        "yes_no",
        YES_NO,
    ),
    QuestionSpec("notice_period", en_ne("What is your notice period?", "तपाईंको सूचना अवधि कति हो?")),
    QuestionSpec("start_date", en_ne("When could you start?", "तपाईं कहिलेदेखि सुरु गर्न सक्नुहुन्छ?")),
    QuestionSpec("salary_expectation", en_ne("What are your salary expectations?", "तपाईंको तलब अपेक्षा कति हो?")),
    QuestionSpec("relocate", en_ne("Are you willing to relocate?", "के तपाईं बसाइँ सर्न तयार हुनुहुन्छ?"), "yes_no", YES_NO),
    QuestionSpec("linkedin", en_ne("Professional network profile", "पेसागत सञ्जाल प्रोफाइल"), "url"),
    QuestionSpec("portfolio", en_ne("Portfolio or website", "पोर्टफोलियो वा वेबसाइट"), "url"),
    QuestionSpec("heard_from", en_ne("How did you hear about this job?", "तपाईंले यो जागिरबारे कसरी थाहा पाउनुभयो?")),
    QuestionSpec(
        "gender",
        en_ne("Gender (equal-opportunity question)", "लिङ्ग (समान अवसर प्रश्न)"),
        "choice",
        (
            DECLINE,
            # Labelled as most forms label them (so a copied answer pastes as the form expects); the values stay.
            ("man", en_ne("Male", "पुरुष")),
            ("woman", en_ne("Female", "महिला")),
            ("non_binary", en_ne("Non-binary", "गैर-द्विलिङ्गी")),
            ("self_describe", en_ne("I'll describe it myself", "म आफैँ वर्णन गर्छु")),
        ),
        sensitive=True,
        default="decline",
    ),
    QuestionSpec(
        "ethnicity",
        en_ne("Race or ethnicity (equal-opportunity question)", "जाति वा जातीयता (समान अवसर प्रश्न)"),
        "choice",
        (DECLINE,),
        sensitive=True,
        default="decline",
    ),
    QuestionSpec(
        "veteran",
        en_ne("Veteran status (equal-opportunity question)", "पूर्वसैनिक स्थिति (समान अवसर प्रश्न)"),
        "choice",
        (
            DECLINE,
            ("yes", en_ne("I am a veteran", "म पूर्वसैनिक हुँ")),
            ("no", en_ne("I am not a veteran", "म पूर्वसैनिक होइन")),
        ),
        sensitive=True,
        default="decline",
    ),
    QuestionSpec(
        "disability",
        en_ne("Disability (equal-opportunity question)", "अपाङ्गता (समान अवसर प्रश्न)"),
        "choice",
        (
            DECLINE,
            ("yes", en_ne("Yes, I have a disability", "हो, मलाई अपाङ्गता छ")),
            ("no", en_ne("No, I don't have a disability", "होइन, मलाई अपाङ्गता छैन")),
        ),
        sensitive=True,
        default="decline",
    ),
)
