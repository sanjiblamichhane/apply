import type { Text } from "../types";

/**
 * What each API error code means to a person. Keys are the backend's ErrorCode values (openapi.json);
 * tests/errors.test.ts fails when the API gains a code that isn't here.
 */
export const errors = {
  INTERNAL: { en: "Something went wrong on our side. Try again.", ne: "हाम्रो तर्फबाट केही गडबड भयो। फेरि प्रयास गर्नुहोस्।" },
  VALIDATION_FAILED: { en: "Some of this isn't right. Check the marked fields.", ne: "यसमा केही मिलेन। चिन्ह लगाइएका ठाउँहरू जाँच्नुहोस्।" },
  NOT_FOUND: { en: "That isn't here any more.", ne: "त्यो अब यहाँ छैन।" },
  METHOD_NOT_ALLOWED: { en: "That can't be done here.", ne: "यहाँ त्यो गर्न मिल्दैन।" },
  TOO_MANY_REQUESTS: { en: "Too many tries. Wait a moment and try again.", ne: "धेरै प्रयास भयो। एकछिन पर्खेर फेरि प्रयास गर्नुहोस्।" },
  DATABASE_NOT_READY: {
    en: "The database isn't ready. Run “apply migrate” on this machine.",
    ne: "डेटाबेस तयार छैन। यो कम्प्युटरमा “apply migrate” चलाउनुहोस्।",
  },
  UNAUTHENTICATED: { en: "Sign in to carry on.", ne: "जारी राख्न साइन इन गर्नुहोस्।" },
  SIGN_IN_FAILED: { en: "That email and password don't match.", ne: "त्यो इमेल र पासवर्ड मिलेनन्।" },
  SIGN_IN_LOCKED: { en: "Too many tries. Wait a while, then sign in.", ne: "धेरै प्रयास भयो। केही बेर पर्खेर साइन इन गर्नुहोस्।" },
  ORIGIN_NOT_ALLOWED: {
    en: "This request came from somewhere apply doesn't accept.",
    ne: "यो अनुरोध apply ले स्वीकार नगर्ने ठाउँबाट आयो।",
  },
  OWNER_EXISTS: { en: "apply already has an owner.", ne: "apply को मालिक पहिल्यै छ।" },
  PASSWORD_TOO_SHORT: { en: "A password needs at least 12 characters.", ne: "पासवर्डमा कम्तीमा १२ अक्षर चाहिन्छ।" },
  TOKEN_INVALID: {
    en: "That token doesn't work: it's wrong, revoked or expired. Make a new one in apply's Settings.",
    ne: "त्यो टोकनले काम गर्दैन: यो गलत, खारेज वा म्याद सकिएको छ। apply को सेटिङमा नयाँ बनाउनुहोस्।",
  },
  TOKEN_NOT_ALLOWED: {
    en: "A token can't do that. Sign in to apply to do it there.",
    ne: "टोकनले त्यो गर्न सक्दैन। त्यहीँ गर्न apply मा साइन इन गर्नुहोस्।",
  },
  TOKEN_SCOPE_MISSING: {
    en: "This token isn't allowed to do that. Make one with that permission in apply's Settings.",
    ne: "यो टोकनलाई त्यो गर्ने अनुमति छैन। apply को सेटिङमा त्यो अनुमतिसहित नयाँ बनाउनुहोस्।",
  },
  TOKEN_NOT_FOUND: { en: "That token isn't here any more.", ne: "त्यो टोकन अब यहाँ छैन।" },
  PACK_NOT_FOUND: { en: "That kind of opportunity isn't installed.", ne: "त्यस्तो किसिमको अवसर स्थापना गरिएको छैन।" },
  DOCUMENT_TYPE_NOT_FOUND: { en: "That kind of document isn't available.", ne: "त्यस्तो किसिमको कागजात उपलब्ध छैन।" },
  DOCUMENT_TYPE_NOT_GENERATABLE: { en: "That document isn't written by the model.", ne: "त्यो कागजात मोडेलले लेख्दैन।" },
  INVALID_ATTRIBUTES: { en: "Some fields aren't right. Check the marked ones.", ne: "केही ठाउँ मिलेनन्। चिन्ह लगाइएका जाँच्नुहोस्।" },
  PROFILE_NOT_FOUND: { en: "That profile isn't here any more.", ne: "त्यो प्रोफाइल अब यहाँ छैन।" },
  PROFILE_REQUIRED: {
    en: "Add a profile first: documents are written from it.",
    ne: "पहिले प्रोफाइल थप्नुहोस्: कागजातहरू त्यसैबाट लेखिन्छन्।",
  },
  PROFILE_PACK_MISMATCH: { en: "That profile is for another kind of opportunity.", ne: "त्यो प्रोफाइल अर्को किसिमको अवसरका लागि हो।" },
  PROFILE_NOT_READ: { en: "This profile wasn't made from a document.", ne: "यो प्रोफाइल कुनै कागजातबाट बनाइएको होइन।" },
  UPLOAD_TOO_LARGE: { en: "That file is too large: upload one of 5 MB or less.", ne: "त्यो फाइल धेरै ठूलो छ: ५ MB वा सोभन्दा सानो अपलोड गर्नुहोस्।" },
  UPLOAD_UNSUPPORTED: { en: "apply reads PDF, .docx and text files. Save it as one of those and try again.", ne: "apply ले PDF, .docx र पाठ फाइल पढ्छ। यसलाई तीमध्ये एकमा सेभ गरेर फेरि प्रयास गर्नुहोस्।" },
  UPLOAD_NO_TEXT: { en: "There's no text in that file to read: it may be a scan. Upload the PDF or .docx file the document was made in.", ne: "त्यो फाइलमा पढ्ने पाठ छैन: यो स्क्यान हुन सक्छ। कागजात बनाइएको PDF वा .docx फाइल अपलोड गर्नुहोस्।" },
  REGISTRATION_CLOSED: { en: "New accounts are closed here. Ask the person who runs this apply.", ne: "यहाँ नयाँ खाता बन्द छन्। यो apply चलाउने व्यक्तिलाई सोध्नुहोस्।" },
  EMAIL_TAKEN: { en: "There's an account with that email already. Sign in instead.", ne: "त्यो इमेलको खाता पहिल्यै छ। बरु साइन इन गर्नुहोस्।" },
  ACCOUNT_DISABLED: { en: "This account is turned off. Ask the person who runs this apply.", ne: "यो खाता बन्द गरिएको छ। यो apply चलाउने व्यक्तिलाई सोध्नुहोस्।" },
  OWNER_ONLY: { en: "Only the owner of this apply can change that.", ne: "यो apply को मालिकले मात्र त्यो बदल्न सक्नुहुन्छ।" },
  RESET_LINK_INVALID: { en: "This link has been used or is more than 30 minutes old. Ask for a new one.", ne: "यो लिङ्क प्रयोग भइसकेको छ वा ३० मिनेटभन्दा पुरानो छ। नयाँ माग्नुहोस्।" },
  MAIL_NOT_SET_UP: { en: "This apply can't send email. Ask the person who runs it.", ne: "यो apply ले इमेल पठाउन सक्दैन। यसलाई चलाउने व्यक्तिलाई सोध्नुहोस्।" },
  ACCOUNT_IS_OWNER: { en: "The owner's account can't be turned off or deleted here.", ne: "मालिकको खाता यहाँ बन्द गर्न वा मेटाउन सकिँदैन।" },
  TEMPLATE_PROBLEMS: { en: "That template has things to fix before it can be used.", ne: "त्यो टेम्प्लेट प्रयोग गर्नुअघि केही कुरा मिलाउनुपर्छ।" },
  STORAGE_UNAVAILABLE: { en: "Your files can't be reached just now. Try again in a moment.", ne: "तपाईंका फाइलहरू अहिले पुग्न सकिएन। केही बेरमा फेरि प्रयास गर्नुहोस्।" },
  OPPORTUNITY_NOT_FOUND: { en: "That opportunity isn't here any more.", ne: "त्यो अवसर अब यहाँ छैन।" },
  URL_OR_TEXT_REQUIRED: { en: "Paste a link or the text.", ne: "लिङ्क वा पाठ टाँस्नुहोस्।" },
  URL_NOT_ALLOWED: { en: "Only web links (http or https) can be read.", ne: "वेब लिङ्क (http वा https) मात्र पढ्न सकिन्छ।" },
  ADDRESS_NOT_ALLOWED: {
    en: "That link points inside this network, so it isn't fetched.",
    ne: "त्यो लिङ्कले यही नेटवर्कभित्र देखाउँछ, त्यसैले ल्याइँदैन।",
  },
  FETCH_FAILED: {
    en: "The page couldn't be reached. Check the link, or paste the text instead.",
    ne: "पेजसम्म पुग्न सकिएन। लिङ्क जाँच्नुहोस्, वा पाठ टाँस्नुहोस्।",
  },
  FETCH_BLOCKED: { en: "The site didn't let apply read the page. Paste the text instead.", ne: "साइटले apply लाई पेज पढ्न दिएन। बरु पाठ टाँस्नुहोस्।" },
  FETCH_NOT_HTML: { en: "That link isn't a web page. Paste the text instead.", ne: "त्यो लिङ्क वेब पेज होइन। बरु पाठ टाँस्नुहोस्।" },
  FETCH_TOO_LARGE: { en: "That page is too large to read. Paste the text instead.", ne: "त्यो पेज पढ्न धेरै ठूलो छ। बरु पाठ टाँस्नुहोस्।" },
  FETCH_TOO_LITTLE_TEXT: { en: "The page had almost no text (it may need a browser to show it). Paste the text instead.", ne: "पेजमा लगभग कुनै पाठ थिएन (देखाउन ब्राउजर चाहिन सक्छ)। बरु पाठ टाँस्नुहोस्।" },
  FETCH_TOO_MANY_REDIRECTS: { en: "That link redirects too many times.", ne: "त्यो लिङ्क धेरै पटक अन्यत्र पठाउँछ।" },
  EXTRACT_FAILED: { en: "Your model couldn't make sense of it. Fill in the details.", ne: "तपाईंको मोडेलले यसलाई बुझ्न सकेन। विवरण भर्नुहोस्।" },
  APPLICATION_NOT_FOUND: { en: "That application isn't here any more.", ne: "त्यो आवेदन अब यहाँ छैन।" },
  APPLICATION_EXISTS: { en: "You're already tracking this one.", ne: "तपाईं यसलाई पहिल्यै ट्र्याक गर्दै हुनुहुन्छ।" },
  STAGE_NOT_FOUND: { en: "That stage isn't in this pipeline.", ne: "त्यो चरण यो पाइपलाइनमा छैन।" },
  DOCUMENT_NOT_FOUND: { en: "That document isn't here any more.", ne: "त्यो कागजात अब यहाँ छैन।" },
  LLM_UNREACHABLE: {
    en: "Your model didn't answer. Is its server running? Check in Settings → Model, then try again.",
    ne: "तपाईंको मोडेलले जवाफ दिएन। के यसको सर्भर चलिरहेको छ? सेटिङहरू → मोडेलमा जाँचेर फेरि प्रयास गर्नुहोस्।",
  },
  LLM_TIMEOUT: {
    en: "Your model took too long. It may still be loading; try again in a minute.",
    ne: "तपाईंको मोडेलले धेरै समय लियो। यो अझै लोड हुँदै होला; एक मिनेटपछि फेरि प्रयास गर्नुहोस्।",
  },
  LLM_BAD_REPLY: { en: "Your model's answer couldn't be used. Try again.", ne: "तपाईंको मोडेलको जवाफ प्रयोग गर्न सकिएन। फेरि प्रयास गर्नुहोस्।" },
  LLM_EMPTY_REPLY: { en: "Your model answered with nothing. Try again.", ne: "तपाईंको मोडेलले केही जवाफ दिएन। फेरि प्रयास गर्नुहोस्।" },
  LLM_MODEL_MISSING: {
    en: "Your model server doesn't have that model any more. Choose one in Settings → Model.",
    ne: "तपाईंको मोडेल सर्भरमा त्यो मोडेल अब छैन। सेटिङहरू → मोडेलमा एउटा छान्नुहोस्।",
  },
  MODEL_NOT_FOUND: {
    en: "That model isn't on this computer any more. Look again, and choose another.",
    ne: "त्यो मोडेल अब यो कम्प्युटरमा छैन। फेरि खोज्नुहोस्, र अर्को छान्नुहोस्।",
  },
  MODEL_TEST_FAILED: {
    en: "That model couldn't give a usable answer, so apply kept the one it was using.",
    ne: "त्यो मोडेलले काम लाग्ने जवाफ दिन सकेन, त्यसैले apply ले पहिलेकै मोडेल राख्यो।",
  },
  SOURCE_NOT_FOUND: { en: "That source isn't here any more.", ne: "त्यो स्रोत अब यहाँ छैन।" },
  SOURCE_KIND_NOT_FOUND: { en: "That kind of source isn't available.", ne: "त्यस्तो किसिमको स्रोत उपलब्ध छैन।" },
  SOURCE_NOT_RECOGNISED: {
    en: "apply doesn't recognise that address. Paste the address of the company's job board page.",
    ne: "apply ले त्यो ठेगाना चिन्दैन। कम्पनीको जागिर बोर्ड पेजको ठेगाना टाँस्नुहोस्।",
  },
  SOURCE_TOO_SOON: {
    en: "This board asks not to be checked that often. Try again later.",
    ne: "यो बोर्डले यति धेरै जाँच नगर्न भन्छ। पछि फेरि प्रयास गर्नुहोस्।",
  },
  SOURCE_FAILED: {
    en: "The board answered with something unexpected. Check the name, or try again later.",
    ne: "बोर्डले अनपेक्षित जवाफ दियो। नाम जाँच्नुहोस्, वा पछि फेरि प्रयास गर्नुहोस्।",
  },
  SEARCH_NOT_FOUND: { en: "That search isn't here any more.", ne: "त्यो खोज अब यहाँ छैन।" },
  MATCH_NOT_FOUND: { en: "That match isn't here any more.", ne: "त्यो मेल खाएको अब यहाँ छैन।" },
  SCORE_CAP_REACHED: {
    en: "Today's scoring limit is reached; the rest are scored tomorrow.",
    ne: "आजको अङ्क दिने सीमा पुग्यो; बाँकीलाई भोलि अङ्क दिइन्छ।",
  },
  DOCUMENT_NOT_READY: { en: "That document isn't written yet.", ne: "त्यो कागजात अहिलेसम्म लेखिएको छैन।" },
  WARNING_NOT_FOUND: { en: "That warning isn't on this version any more.", ne: "त्यो चेतावनी अब यो संस्करणमा छैन।" },
  NOTHING_TO_REWRITE: {
    en: "Mark a warning wrong, or say what to change, first.",
    ne: "पहिले कुनै चेतावनी गलत भनी चिनो लगाउनुहोस्, वा के परिवर्तन गर्ने भन्नुहोस्।",
  },
  RENDER_PENDING: { en: "The PDF is being made. Try again in a moment.", ne: "PDF बन्दैछ। एकछिनमा फेरि प्रयास गर्नुहोस्।" },
  ANSWER_NOT_FOUND: { en: "That answer isn't here any more.", ne: "त्यो जवाफ अब यहाँ छैन।" },
  ANSWER_EXISTS: { en: "There's already an answer with that short name.", ne: "त्यो छोटो नामको जवाफ पहिल्यै छ।" },
  SUBMISSION_NOT_FOUND: { en: "That submission isn't here any more.", ne: "त्यो पठाइएको रेकर्ड अब यहाँ छैन।" },
  UNDO_TOO_LATE: { en: "It can only be undone for 10 minutes.", ne: "यसलाई १० मिनेटसम्म मात्र पूर्ववत् गर्न सकिन्छ।" },
  AUTO_RUN_NOT_FOUND: { en: "That isn't here any more.", ne: "त्यो अब यहाँ छैन।" },
  AUTO_ACTION_NOT_ALLOWED: {
    en: "That can't be done now: look at where it's up to.",
    ne: "अहिले त्यो गर्न मिल्दैन: यो कहाँसम्म पुग्यो हेर्नुहोस्।",
  },
  RUNNER_TASK_NOT_FOUND: { en: "That step was taken back from the runner.", ne: "त्यो चरण रनरबाट फिर्ता लिइयो।" },
  AUTO_PAUSED: {
    en: "Auto is paused, so this waits for you. Turn Auto back on, or apply yourself.",
    ne: "स्वचालित रोकिएको छ, त्यसैले यो तपाईंलाई पर्खन्छ। स्वचालित फेरि खोल्नुहोस्, वा आफैँ आवेदन दिनुहोस्।",
  },
  AUTO_CAP_REACHED: {
    en: "Today's limit for automatic applications is reached. Try again tomorrow, or apply yourself.",
    ne: "आजका स्वचालित आवेदनको सीमा पुग्यो। भोलि फेरि प्रयास गर्नुहोस्, वा आफैँ आवेदन दिनुहोस्।",
  },
  AUTO_SAME_ISSUER: {
    en: "You've applied to this employer in the last 30 days, so apply leaves this one to you.",
    ne: "तपाईंले पछिल्लो ३० दिनमा यो रोजगारदातालाई आवेदन दिनुभएको छ, त्यसैले apply ले यो तपाईंलाई छोड्छ।",
  },
  AUTO_CLOSED: { en: "The posting has closed.", ne: "सूचना बन्द भइसक्यो।" },
  AUTO_UNSUPPORTED_BOARD: {
    en: "Its form isn't on a board apply can fill. Apply with the kit.",
    ne: "यसको फारम apply ले भर्न सक्ने बोर्डमा छैन। किटबाट आवेदन दिनुहोस्।",
  },
  AUTO_PROFILE_REQUIRED: {
    en: "There's no profile to write from. Add one, then try again.",
    ne: "लेख्नका लागि प्रोफाइल छैन। एउटा थपेर फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_DOCUMENT_FAILED: {
    en: "A document couldn't be written. Open the application and write it again.",
    ne: "एउटा कागजात लेख्न सकिएन। आवेदन खोलेर फेरि लेखाउनुहोस्।",
  },
  AUTO_CLAIMS_UNCHECKED: {
    en: "Your model couldn't check the documents, and nothing unchecked is sent. Check them again, then try again.",
    ne: "तपाईंको मोडेलले कागजात जाँच्न सकेन, र नजाँचेको केही पठाइँदैन। फेरि जाँचेर फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_CLAIM_WARNINGS: {
    en: "The documents say things your profile doesn't back up. Review them, then try again.",
    ne: "कागजातमा तपाईंको प्रोफाइलले पुष्टि नगर्ने कुरा छन्। समीक्षा गरेर फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_TIMED_OUT: {
    en: "Writing the documents took too long (is the model running?). Try again.",
    ne: "कागजात लेख्न धेरै समय लाग्यो (के मोडेल चलिरहेको छ?)। फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_CAPTCHA: {
    en: "The form asks to prove you're a person. apply never gets around that: apply yourself.",
    ne: "फारमले तपाईं मान्छे हो भनी प्रमाण माग्छ। apply ले त्यो कहिल्यै छल्दैन: आफैँ आवेदन दिनुहोस्।",
  },
  AUTO_SIGN_IN: { en: "The board wants you to sign in first. Apply yourself.", ne: "बोर्डले पहिले साइन इन गर्न भन्छ। आफैँ आवेदन दिनुहोस्।" },
  AUTO_FORM_MISSING: {
    en: "The application form wasn't on the page. Open it to see why.",
    ne: "पेजमा आवेदन फारम थिएन। किन भनेर हेर्न खोल्नुहोस्।",
  },
  AUTO_CONSENT_REQUIRED: {
    en: "The form asks you to agree to something. That's yours to do: apply yourself.",
    ne: "फारमले केहीमा सहमति माग्छ। त्यो तपाईं आफैँले गर्ने हो: आफैँ आवेदन दिनुहोस्।",
  },
  AUTO_REQUIRED_UNANSWERED: {
    en: "The form asks questions apply has no answer for. Answer them yourself, or save answers, then try again.",
    ne: "फारमले apply सँग जवाफ नभएका प्रश्न सोध्छ। आफैँ जवाफ दिनुहोस्, वा जवाफ सेभ गरेर फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_DRAFT_UNSUPPORTED: {
    en: "Some drafted answers weren't backed by your profile, so nothing was sent. Answer them yourself.",
    ne: "केही मस्यौदा जवाफ तपाईंको प्रोफाइलले पुष्टि गरेनन्, त्यसैले केही पठाइएन। आफैँ जवाफ दिनुहोस्।",
  },
  AUTO_DOCUMENTS_CHANGED: {
    en: "The documents changed while it was waiting. Look them over, then try again.",
    ne: "पर्खिँदा कागजात बदलिए। हेरेर फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_FORM_CHANGED: {
    en: "The form changed since apply read it, so nothing was sent. Try again.",
    ne: "apply ले पढेपछि फारम बदलियो, त्यसैले केही पठाइएन। फेरि प्रयास गर्नुहोस्।",
  },
  AUTO_VALIDATION_ERROR: {
    en: "The board didn't accept the form. Open it and send it yourself.",
    ne: "बोर्डले फारम स्वीकार गरेन। खोलेर आफैँ पठाउनुहोस्।",
  },
  AUTO_NO_CONFIRMATION: {
    en: "The board didn't confirm it got the application. Check the board before anything else.",
    ne: "बोर्डले आवेदन पायो भनी पुष्टि गरेन। अरू केही गर्नुअघि बोर्ड जाँच्नुहोस्।",
  },
  AUTO_SEND_UNKNOWN: {
    en: "apply can't tell whether this was sent. Check the board (or your email) before applying again.",
    ne: "यो पठाइयो कि भनेर apply ले थाहा पाउन सक्दैन। फेरि आवेदन दिनुअघि बोर्ड (वा इमेल) जाँच्नुहोस्।",
  },
  AUTO_RUNNER_FAILED: {
    en: "Something went wrong in the runner's browser. Try again, or apply yourself.",
    ne: "रनरको ब्राउजरमा केही गडबड भयो। फेरि प्रयास गर्नुहोस्, वा आफैँ आवेदन दिनुहोस्।",
  },
  NETWORK: {
    en: "apply's server didn't answer. Is it running?",
    ne: "apply को सर्भरले जवाफ दिएन। के यो चलिरहेको छ?",
  },
} as const satisfies Record<string, Text>;

export type ErrorKey = keyof typeof errors;
