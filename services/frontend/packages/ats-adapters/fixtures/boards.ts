/**
 * Application forms as each board draws them: their ids, names, label markup, required markers and
 * equal-opportunity questions, trimmed to one posting each. The unit tests read them in jsdom; the browser
 * journeys serve them from local fake boards (fixtures/server.ts). Nothing here talks to a real board.
 */

export const POSTINGS = {
  board01: { path: "/acme/jobs/4012345", title: "Senior Backend Engineer", company: "Acme Robotics" },
  board02: {
    path: "/himal/a1b2c3d4-0000-4000-8000-000000000001/apply",
    title: "Backend Engineer (Python)",
    company: "Himal",
  },
  board03: {
    path: "/example-analytics/f3e1c2b4-1111-4111-8111-111111111111/application",
    title: "Data Engineer",
    company: "Example Analytics",
  },
  // A company's own careers site, on no board apply knows: the extension's generic filler.
  other: { path: "/careers/42/apply", title: "Platform Engineer", company: "Yeti Cloud" },
} as const;

function jsonLd(title: string, company: string, description: string): string {
  const posting = {
    "@context": "https://schema.org",
    "@type": "JobPosting",
    title,
    hiringOrganization: { "@type": "Organization", name: company },
    description,
    datePosted: "2026-10-20",
    employmentType: "FULL_TIME",
  };
  return `<script type="application/ld+json">${JSON.stringify(posting)}</script>`;
}

function page(title: string, head: string, body: string): string {
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><title>${title}</title>${head}</head><body>${body}</body></html>`;
}

const yesNo = `<option value="">Select...</option><option value="1">Yes</option><option value="0">No</option>`;

export function board01Form(): string {
  const { title, company, path } = POSTINGS.board01;
  return page(`Job Application for ${title} at ${company}`, jsonLd(title, company, "<p>Build APIs in Python and Django on PostgreSQL.</p>"), `
<main>
  <div class="job__header"><h1 class="section-header">${title}</h1><p class="job__location">Remote - US</p></div>
  <div class="job__description"><p>Build APIs in Python and Django on PostgreSQL. 5+ years Python.</p></div>
  <form id="application-form" action="${path}/confirmation" method="post" enctype="multipart/form-data">
    <h2>Apply for this job</h2>
    <div class="field"><label for="first_name" id="first_name-label">First Name<span aria-hidden="true">*</span></label>
      <input id="first_name" name="first_name" type="text" aria-required="true" autocomplete="given-name"></div>
    <div class="field"><label for="last_name" id="last_name-label">Last Name<span aria-hidden="true">*</span></label>
      <input id="last_name" name="last_name" type="text" aria-required="true" autocomplete="family-name"></div>
    <div class="field"><label for="email" id="email-label">Email<span aria-hidden="true">*</span></label>
      <input id="email" name="email" type="email" aria-required="true" autocomplete="email"></div>
    <div class="field"><label for="phone" id="phone-label">Phone</label>
      <input id="phone" name="phone" type="tel" autocomplete="tel"></div>
    <div class="field file-upload"><div class="label upload-label" id="upload-label-resume">Resume/CV<span aria-hidden="true">*</span></div>
      <input type="file" id="resume" name="resume" aria-labelledby="upload-label-resume" aria-required="true" accept=".pdf,.doc,.docx,.txt,.rtf"></div>
    <div class="field file-upload"><div class="label upload-label" id="upload-label-cover_letter">Cover Letter</div>
      <input type="file" id="cover_letter" name="cover_letter" aria-labelledby="upload-label-cover_letter" accept=".pdf,.doc,.docx,.txt,.rtf"></div>
    <div class="field"><label for="question_31337001">LinkedIn Profile</label>
      <input id="question_31337001" name="question_31337001" type="text"></div>
    <div class="field"><label for="question_31337002">Website</label>
      <input id="question_31337002" name="question_31337002" type="text"></div>
    <div class="field"><label for="question_31337003">Are you legally authorized to work in the United States?<span aria-hidden="true">*</span></label>
      <select id="question_31337003" name="question_31337003" aria-required="true">${yesNo}</select></div>
    <div class="field"><label for="question_31337004">Will you now or in the future require sponsorship for employment visa status (e.g. H-1B)?<span aria-hidden="true">*</span></label>
      <select id="question_31337004" name="question_31337004" aria-required="true">${yesNo}</select></div>
    <div class="field"><label for="question_31337005">Why do you want to work at ${company}?<span aria-hidden="true">*</span></label>
      <textarea id="question_31337005" name="question_31337005" aria-required="true"></textarea></div>
    <div class="field"><label for="question_31337006">How did you hear about this job?</label>
      <input id="question_31337006" name="question_31337006" type="text"></div>
    <div class="field"><label for="question_31337007">Which office would you prefer?</label>
      <input id="question_31337007" name="question_31337007" role="combobox" aria-expanded="false" type="text"></div>
    <fieldset class="eeoc"><legend>Voluntary Self-Identification</legend>
      <div class="field"><label for="gender">Gender</label>
        <select id="gender" name="gender"><option value="">Select...</option><option value="1">Male</option><option value="2">Female</option><option value="3">Decline To Self Identify</option></select></div>
      <div class="field"><label for="hispanic_ethnicity">Are you Hispanic/Latino?</label>
        <select id="hispanic_ethnicity" name="hispanic_ethnicity"><option value="">Select...</option><option value="Yes">Yes</option><option value="No">No</option><option value="Decline">Decline To Self Identify</option></select></div>
      <div class="field"><label for="veteran_status">Veteran Status</label>
        <select id="veteran_status" name="veteran_status"><option value="">Select...</option><option value="1">I am not a protected veteran</option><option value="2">I identify as one or more of the classifications of protected veteran</option><option value="3">I don't wish to answer</option></select></div>
      <div class="field"><label for="disability_status">Disability Status</label>
        <select id="disability_status" name="disability_status"><option value="">Select...</option><option value="1">Yes, I have a disability (or previously had a disability)</option><option value="2">No, I do not have a disability and have not had one in the past</option><option value="3">I do not want to answer</option></select></div>
    </fieldset>
    <div class="field checkbox"><input type="checkbox" id="gdpr_consent" name="gdpr_consent" aria-required="true">
      <label for="gdpr_consent">I agree to the processing of my personal data as described in the privacy policy.</label></div>
    <button type="submit" class="btn btn--pill">Submit application</button>
  </form>
</main>`);
}

export function board01Confirmation(): string {
  return page("Thank you for applying", "", `<main><h1>Thank you for applying.</h1><p>Your application has been received. We will review it and be in touch.</p></main>`);
}

export function board02Form(): string {
  const { title, company, path } = POSTINGS.board02;
  const question = (label: string, control: string, required = false) => `
      <li class="application-question"><label><div class="application-label">${label}${required ? '<span class="required">✱</span>' : ""}</div>
        <div class="application-field">${control}</div></label></li>`;
  const card = (label: string, control: string, required = false) => `
        <li class="application-question custom-question"><div class="application-label full-width"><div class="text">${label}${required ? '<span class="required">✱</span>' : ""}</div></div>
          <div class="application-field full-width">${control}</div></li>`;
  const decline = `<option value="Decline to self-identify">Decline to self-identify</option>`;
  return page(`${company} - ${title}`, jsonLd(title, company, "<p>Design Django APIs and own Postgres.</p>"), `
<div class="main-header page-full-width"><div class="main-header-content page-centered"><h2>${title}</h2><div class="posting-categories"><div class="sort-by-time posting-category">Kathmandu, Nepal</div></div></div></div>
<div class="content-wrapper application-page">
  <form id="application-form" method="POST" action="${path}" enctype="multipart/form-data">
    <div class="section page-centered application-form"><h4>Submit your application</h4>
      <ul>
        <li class="application-question resume"><label><div class="application-label">Resume/CV<span class="required">✱</span></div>
          <div class="application-field"><input type="file" name="resume" id="resume-upload-input" class="application-file-input" required></div></label></li>
        ${question("Full name", '<input type="text" name="name" required>', true)}
        ${question("Email", '<input type="email" name="email" required>', true)}
        ${question("Phone", '<input type="text" name="phone">')}
        ${question("Current location", '<input type="text" name="location" id="location-input">')}
        ${question("Current company", '<input type="text" name="org">')}
      </ul>
    </div>
    <div class="section page-centered application-form"><h4>Links</h4>
      <ul>
        ${question("LinkedIn URL", '<input type="text" name="urls[LinkedIn]">')}
        ${question("GitHub URL", '<input type="text" name="urls[GitHub]">')}
        ${question("Portfolio URL", '<input type="text" name="urls[Portfolio]">')}
        ${question("Other website", '<input type="text" name="urls[Other]">')}
      </ul>
    </div>
    <div class="section page-centered application-form application-additional"><h4>Questions</h4>
      <ul>
        ${card("What is your notice period?", '<input type="text" name="cards[0b1c][field0]" required>', true)}
        ${card("Are you willing to relocate to Kathmandu?", `<ul data-qa="multiple-choice">
            <li><label><input type="radio" name="cards[0b1c][field1]" value="Yes" required><span class="application-answer-alternative">Yes</span></label></li>
            <li><label><input type="radio" name="cards[0b1c][field1]" value="No"><span class="application-answer-alternative">No</span></label></li></ul>`, true)}
        ${card("Tell us about a project you are proud of", '<textarea name="cards[0b1c][field2]" class="card-field-input"></textarea>')}
      </ul>
    </div>
    <div class="section page-centered application-form"><h4>Additional information</h4>
      <textarea name="comments" id="additional-information" placeholder="Add a cover letter or anything else you want to share."></textarea>
    </div>
    <div class="section page-centered application-form eeo-section"><h4>U.S. Equal Employment Opportunity information</h4>
      <ul>
        ${question("Gender", `<select name="eeo[gender]"><option value="">Select ...</option><option value="Female">Female</option><option value="Male">Male</option>${decline}</select>`)}
        ${question("Race", `<select name="eeo[race]"><option value="">Select ...</option><option value="Asian">Asian (Not Hispanic or Latino)</option><option value="White">White (Not Hispanic or Latino)</option>${decline}</select>`)}
        ${question("Veteran status", `<select name="eeo[veteran]"><option value="">Select ...</option><option value="I am a veteran">I am a veteran</option><option value="I am not a veteran">I am not a veteran</option>${decline}</select>`)}
      </ul>
    </div>
    <div class="section page-centered last-section-in-form"><div class="h-captcha" data-sitekey="00000000-0000-0000-0000-000000000000"></div>
      <button type="submit" class="template-btn-submit postings-btn" data-qa="btn-submit">Submit application</button></div>
  </form>
</div>`);
}

export function board02Confirmation(): string {
  return page("Application submitted", "", `<div class="content-wrapper"><div class="section page-centered"><h3>Application submitted!</h3><p>Thanks for applying. We'll be in touch.</p></div></div>`);
}

/**
 * board03's form as React draws it (checked against a live page on 2026-10-26): a container, not a <form>;
 * "required" as a class on the label; an unlabelled "autofill from resume" uploader; yes/no as buttons; and
 * equal-opportunity checkboxes each named after their option.
 */
export function board03FormMarkup(): string {
  const entry = (id: string, label: string, control: string, required = false) => `
    <div class="_fieldEntry_1e3gg_28 ashby-application-form-field-entry" data-field-path="${id}"><label class="_heading_f7cvd_52${required ? " _required_f7cvd_91" : ""} ashby-application-form-question-title" for="${id}">${label}</label><div>${control}</div></div>`;
  const box = (group: string, i: number, text: string) =>
    `<span><input type="checkbox" id="${group}-labeled-checkbox-${i}" name="${text}"><label for="${group}-labeled-checkbox-${i}">${text}</label></span>`;
  return `
  <div class="ashby-application-form-container _container_f7cvd_28">
    <div class="_autofill"><input type="file" style="display:none"><h3>Autofill from resume</h3><button type="submit">Upload file</button></div>
    <div class="ashby-application-form-section-container">
    ${entry("_systemfield_name", "Name", '<input id="_systemfield_name" name="_systemfield_name" type="text" placeholder="Type here..." required>', true)}
    ${entry("_systemfield_email", "Email", '<input id="_systemfield_email" name="_systemfield_email" type="email" placeholder="hello@example.com..." required>', true)}
    ${entry("_systemfield_resume", "Resume", '<input id="_systemfield_resume" type="file" style="display:none"><button type="submit">Upload File</button>', true)}
    ${entry("4f1e0d6c-phone", "Phone Number", '<input id="4f1e0d6c-phone" name="4f1e0d6c-phone" type="tel">')}
    ${entry("9a2b-linkedin", "LinkedIn Profile", '<input id="9a2b-linkedin" name="9a2b-linkedin" type="text">')}
    ${entry("7c3d-notice", "What is your notice period?", '<input id="7c3d-notice" name="7c3d-notice" type="text">')}
    <div class="_fieldEntry_1e3gg_28 ashby-application-form-field-entry"><label class="_heading_f7cvd_52 _required_f7cvd_91 ashby-application-form-question-title">Will you require visa sponsorship?</label>
      <div class="_yesno_container"><button type="submit" class="_option_1svni_32">Yes</button><button type="submit" class="_option_1svni_32">No</button></div></div>
    ${entry("5e6f-why", "Why Example Analytics?", '<textarea id="5e6f-why" name="5e6f-why"></textarea>')}
    <div class="_fieldEntry_1e3gg_28 ashby-application-form-field-entry"><label class="_heading_f7cvd_52 ashby-application-form-question-title">Race/ethnicity</label>
      <div>${["Asian or Asian American", "White", "Other", "I prefer not to answer"].map((t, i) => box("ae95_1e21", i, t)).join("")}</div></div>
    </div>
    <button type="submit" class="_button_zyh3g_28 _primary_zyh3g_97 ashby-application-form-submit-button">Submit Application</button>
  </div>`;
}

export function board03SuccessMarkup(): string {
  return `<div class="ashby-application-form-success-container"><h2>Thank you for applying!</h2><p>Your application was submitted. We'll be in touch.</p></div>`;
}

/**
 * The board03 page: an empty shell that draws the form a moment after loading, keeps every value in its own
 * state from input and change events (as React does: a value set without them isn't sent), and on submit
 * posts that state, then says thank you in place.
 */
export function board03Page(submitTo: string): string {
  const { title, company } = POSTINGS.board03;
  const script = `
  const state = {}; const files = {};
  setTimeout(() => {
    document.getElementById("root").innerHTML = ${JSON.stringify(board03FormMarkup())};
    const form = document.querySelector(".ashby-application-form-container");
    form.addEventListener("input", (e) => { if (e.target.type !== "file" && e.target.type !== "checkbox") state[e.target.name] = e.target.value; });
    form.addEventListener("change", (e) => {
      if (e.target.type === "file" && e.target.id) files[e.target.id] = e.target.files[0];
      if (e.target.type === "checkbox") state["eeo:" + e.target.name] = String(e.target.checked);
    });
    for (const button of document.querySelectorAll("._yesno_container button")) {
      button.addEventListener("click", () => {
        const label = button.closest(".ashby-application-form-field-entry").querySelector("label").textContent;
        state["choice:" + label] = button.textContent;
        for (const b of button.parentElement.children) b.setAttribute("aria-pressed", String(b === button));
      });
    }
    document.querySelector(".ashby-application-form-submit-button").addEventListener("click", async () => {
      const body = new FormData();
      for (const [k, v] of Object.entries(state)) body.append(k, v);
      for (const [k, f] of Object.entries(files)) if (f) body.append(k, f, f.name);
      await fetch(${JSON.stringify(submitTo)}, { method: "POST", body });
      document.getElementById("root").innerHTML = ${JSON.stringify(board03SuccessMarkup())};
    });
  }, 300);`;
  return page(`${title} @ ${company}`, jsonLd(title, company, "<p>SQL, dashboards and Python.</p>"),
    `<div id="root"><p>Loading…</p></div><script>${script}</script>`);
}

/** A careers site apply knows nothing about: a plain form, labelled as most are, and its thank-you page. */
export function otherForm(): string {
  const { title, company } = POSTINGS.other;
  return page(`${title} · ${company} careers`, jsonLd(title, company, "<p>Run our platform on Kubernetes.</p>"), `
    <header><form role="search" action="/search"><input name="q" aria-label="Search jobs"><button>Search</button></form></header>
    <main>
      <h1>${title}</h1>
      <p>${company} · Remote</p>
      <form id="careers-form" method="post" action="/careers/42/apply" enctype="multipart/form-data">
        <p><label for="given">First name *</label><input id="given" name="given" required></p>
        <p><label for="family">Last name *</label><input id="family" name="family" required></p>
        <p><label for="mail">Email address *</label><input id="mail" name="mail" type="email" required></p>
        <p><label for="mobile">Mobile phone</label><input id="mobile" name="mobile" type="tel"></p>
        <p><label for="li">LinkedIn profile</label><input id="li" name="li" type="url"></p>
        <p><label for="cv">Resume</label><input id="cv" name="cv" type="file"></p>
        <p><label for="why">Why do you want to join ${company}?</label><textarea id="why" name="why"></textarea></p>
        <p><label><input type="checkbox" name="privacy" required> I agree to the privacy policy *</label></p>
        <button type="submit">Send application</button>
      </form>
    </main>`);
}

export function otherConfirmation(): string {
  return page("Thanks", "", `<main><h1>Thank you for applying!</h1><p>We'll be in touch.</p></main>`);
}

/**
 * board04, as its career sites draw it (made up; its markup's shape): the job page; the sign-in step; then the
 * application in steps at one address, each step drawn by script into [data-automation-id=applyFlowPage], with
 * controls named by data-automation-id, labels bound by for=, its own dropdown buttons, and an unlabelled
 * resume uploader. The steps' Next and Submit are never pressed by apply.
 */
export const BOARD04 = {
  host: "himaltech.wd5.myworkdayjobs.com",
  job: "/en-US/External/job/Kathmandu/Backend-Engineer_JR1042",
  title: "Backend Engineer",
  company: "Himal Tech",
} as const;

function board04Page(body: string, script = ""): string {
  return page(`${BOARD04.title} - ${BOARD04.company} Careers`,
    jsonLd(BOARD04.title, BOARD04.company, "<p>Build APIs in Python on PostgreSQL.</p>"),
    `<div id="root"><main>${body}</main></div><script>(${wireBoard04Dropdowns.toString()})(document);</script>${script}`);
}

/**
 * board04's own dropdowns, as its script runs them: a "Select One" button opens a list (role=listbox, drawn at
 * the end of the page) and an option, clicked, becomes the button's text; a search box ("How Did You Hear About
 * Us?") lists what matches on Enter, and a choice becomes a chip beside it. Escape closes the list. Each control's
 * options are in its data-options. On the fixture server's pages, and wired by hand in jsdom.
 */
export function wireBoard04Dropdowns(doc: Document): void {
  if (doc.documentElement.hasAttribute("data-wd-wired")) return;
  doc.documentElement.setAttribute("data-wd-wired", "");
  const close = () => doc.querySelectorAll("[data-automation-id=wd-popup]").forEach((p) => p.remove());
  const open = (items: string[], onPick: (text: string) => void) => {
    close();
    const popup = doc.createElement("div");
    popup.setAttribute("data-automation-id", "wd-popup");
    const list = doc.createElement("ul");
    list.setAttribute("role", "listbox");
    for (const text of items) {
      const item = doc.createElement("li");
      item.setAttribute("role", "option");
      item.setAttribute("data-automation-id", "promptOption");
      item.textContent = text;
      item.addEventListener("click", () => { onPick(text); close(); });
      list.append(item);
    }
    popup.append(list);
    doc.body.append(popup);
  };
  doc.addEventListener("click", (event) => {
    const button = (event.target as Element).closest?.("button[aria-haspopup=listbox]");
    if (!button) return;
    open(JSON.parse(button.getAttribute("data-options") ?? "[]"), (text) => { button.textContent = text; });
  });
  doc.addEventListener("keydown", (event) => {
    if (event.key === "Escape") return close();
    const input = event.target as HTMLInputElement;
    if (event.key !== "Enter" || input.getAttribute?.("data-automation-id") !== "searchBox") return;
    const all: string[] = JSON.parse(input.getAttribute("data-options") ?? "[]");
    const query = input.value.toLowerCase();
    open(all.filter((t) => t.toLowerCase().includes(query)), (text) => {
      const chip = doc.createElement("div");
      chip.setAttribute("data-automation-id", "selectedItem");
      chip.textContent = text;
      input.before(chip);
      input.value = "";
    });
  });
}

const inner = (html: string) => html.slice(html.indexOf("<main>") + 6, html.lastIndexOf("</main>"));

/**
 * The application as board04's script runs it, at one address: sign in, then each step drawn in place when the
 * person presses its button (the journeys press them; apply never does). Its last step posts what was typed.
 */
export function board04Application(): string {
  const steps = [board04MyInformation(), board04MyExperience()].map(inner);
  const script = `
<template id="step-0">${steps[0]}</template>
<template id="step-1">${steps[1]}</template>
<script>
  const main = document.querySelector("main");
  let step = -1;
  function show(n) {
    step = n;
    main.replaceChildren(document.getElementById("step-" + n).content.cloneNode(true));
    history.pushState({ step: n }, "", location.pathname);
    if (n === 1) {
      const next = main.querySelector("[data-automation-id=bottom-navigation-next-button]");
      next.textContent = "Submit";
    }
  }
  const typed = {};
  document.addEventListener("click", async (event) => {
    const button = event.target.closest("button");
    if (!button) return;
    if (button.dataset.automationId === "signInSubmitButton") return show(0);
    if (button.dataset.automationId !== "bottom-navigation-next-button") return;
    for (const el of main.querySelectorAll("input[data-automation-id]")) {
      if (el.type === "file") { if (el.files[0]) typed[el.dataset.automationId] = el.files[0]; }
      else typed[el.dataset.automationId] = el.value;
    }
    if (step === 0) return show(1);
    const form = new FormData();
    for (const [key, value] of Object.entries(typed)) form.append(key, value);
    await fetch(location.pathname, { method: "POST", body: form });
    main.innerHTML = "<h2>Thank you for applying!</h2><p>Your application has been submitted.</p>";
  });
</script>`;
  return board04Page(inner(board04SignIn()), script);
}

const wdField = (id: string, label: string, control: string, required = false) => `
  <div data-automation-id="formField-${id}">
    <label for="input-${id}">${label}${required ? '<abbr title="required" aria-hidden="true">*</abbr>' : ""}</label>
    <div>${control.replace("{id}", `input-${id}`)}</div>
  </div>`;

export function board04Job(): string {
  return board04Page(`
    <h2 data-automation-id="jobPostingHeader">${BOARD04.title}</h2>
    <div data-automation-id="jobPostingDescription"><p>Build APIs in Python on PostgreSQL.</p></div>
    <a data-automation-id="adventureButton" role="button" href="${BOARD04.job}/apply/applyManually">Apply</a>`);
}

export function board04SignIn(): string {
  return board04Page(`
    <div data-automation-id="signInContent" role="dialog" aria-labelledby="sign-in-title">
      <h2 id="sign-in-title">Sign In</h2>
      ${wdField("email", "Email Address", '<input id="{id}" data-automation-id="email" type="text" aria-required="true">', true)}
      ${wdField("password", "Password", '<input id="{id}" data-automation-id="password" type="password" aria-required="true">', true)}
      <button data-automation-id="signInSubmitButton" type="button">Sign In</button>
    </div>`);
}

/**
 * Step 1, My Information: where they heard of the job (board04's search box), names, contact, an address, a
 * phone type (its "Select One" button), and whether they've worked there before (the same button, Yes or No).
 */
export function board04MyInformation(): string {
  const options = (list: string[]) => JSON.stringify(list).replace(/"/g, "&quot;");
  return board04Page(`
    <div data-automation-id="applyFlowPage">
      <h2 data-automation-id="progressBarActiveStep">My Information</h2>
      ${wdField("sourceSection_source", "How Did You Hear About Us?", `<div data-automation-id="multiSelectContainer"><input id="{id}" data-automation-id="searchBox" type="text" placeholder="Search" data-options="${options(["Job Fair", "Online Job Board", "Company Website", "Employee Referral", "University Career Fair"])}"></div>`, true)}
      ${wdField("legalNameSection_firstName", "First Name", '<input id="{id}" data-automation-id="legalNameSection_firstName" type="text" aria-required="true">', true)}
      ${wdField("legalNameSection_lastName", "Last Name", '<input id="{id}" data-automation-id="legalNameSection_lastName" type="text" aria-required="true">', true)}
      ${wdField("addressSection_addressLine1", "Address Line 1", '<input id="{id}" data-automation-id="addressSection_addressLine1" type="text">')}
      ${wdField("addressSection_city", "City", '<input id="{id}" data-automation-id="addressSection_city" type="text">')}
      ${wdField("email", "Email Address", '<input id="{id}" data-automation-id="email" type="text" aria-required="true">', true)}
      ${wdField("phone-device-type", "Phone Device Type", `<button type="button" aria-haspopup="listbox" data-automation-id="phone-device-type" data-options="${options(["Mobile", "Home", "Work"])}">Select One</button>`, true)}
      ${wdField("phone-number", "Phone Number", '<input id="{id}" data-automation-id="phone-number" type="text" aria-required="true">', true)}
      ${wdField("previousWorker", "Have you ever previously been employed by Himal Tech Group, including any of its subsidiaries?", `<button type="button" aria-haspopup="listbox" data-automation-id="previousWorker" data-options="${options(["Yes", "No"])}">Select One</button>`, true)}
      <div data-automation-id="pageFooter"><button data-automation-id="bottom-navigation-next-button" type="button">Save and Continue</button></div>
    </div>`);
}

/** Step 2, My Experience: the resume uploader (no label of its own) and a professional-network question. */
export function board04MyExperience(): string {
  return board04Page(`
    <div data-automation-id="applyFlowPage">
      <h2 data-automation-id="progressBarActiveStep">My Experience</h2>
      <div data-automation-id="resumeSection">
        <h3>Resume/CV</h3>
        <div data-automation-id="file-upload-drop-zone"><p>Drop file here</p>
          <input data-automation-id="file-upload-input-ref" type="file" style="display:none"></div>
      </div>
      ${wdField("linkedinQuestion", "LinkedIn", '<input id="{id}" data-automation-id="linkedinQuestion" type="text">')}
      <div data-automation-id="pageFooter"><button data-automation-id="bottom-navigation-next-button" type="button">Save and Continue</button></div>
    </div>`);
}
