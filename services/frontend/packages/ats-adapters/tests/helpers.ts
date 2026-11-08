import type { Sheet } from "../src";

/** A fill sheet as GET /applications/{id}/fill sends it (the parts filling reads). */
export function sheet(overrides: Partial<Sheet> = {}): Sheet {
  const text = (en: string) => ({ en, ne: en });
  return {
    values: {
      full_name: "Sam Rai",
      first_name: "Sam",
      last_name: "Rai",
      email: "sam@example.com",
      phone: "+977 980 000 0000",
      linkedin: "https://www.linkedin.com/in/example",
      github: "https://github.com/example",
      current_company: "Himal Tech",
      current_title: "Backend Engineer",
    },
    answers: [
      {
        key: "work_authorization", question: text("Are you legally allowed to work in the country of this job?"),
        answer_type: "yes_no", answer: "yes", choices: [], is_sensitive: false
      },
      {
        key: "needs_sponsorship", question: text("Will you now or in future need visa sponsorship?"),
        answer_type: "yes_no", answer: "no", choices: [], is_sensitive: false
      },
      {
        key: "notice_period", question: text("What is your notice period?"), answer_type: "text",
        answer: "One month", choices: [], is_sensitive: false
      },
      {
        key: "relocate", question: text("Are you willing to relocate?"), answer_type: "yes_no", answer: "yes",
        choices: [], is_sensitive: false
      },
      {
        key: "heard_from", question: text("How did you hear about this job?"), answer_type: "text",
        answer: "apply", choices: [], is_sensitive: false
      },
      {
        key: "gender", question: text("Gender (equal-opportunity question)"), answer_type: "choice", answer: "decline",
        choices: [
          { value: "decline", label: { en: "Decline to answer", ne: "जवाफ दिन चाहन्नँ" } },
          { value: "female", label: { en: "Female", ne: "महिला" } },
          { value: "male", label: { en: "Male", ne: "पुरुष" } },
        ], is_sensitive: true
      },
      {
        key: "ethnicity", question: text("Race or ethnicity (equal-opportunity question)"), answer_type: "choice",
        answer: "decline", choices: [{ value: "decline", label: { en: "Decline to answer", ne: "x" } }], is_sensitive: true
      },
      {
        key: "veteran", question: text("Veteran status (equal-opportunity question)"), answer_type: "choice",
        answer: "no", choices: [
          { value: "decline", label: { en: "Decline to answer", ne: "x" } },
          { value: "yes", label: { en: "I am a veteran", ne: "x" } },
          { value: "no", label: { en: "I am not a veteran", ne: "x" } },
        ], is_sensitive: true
      },
      {
        key: "disability", question: text("Disability (equal-opportunity question)"), answer_type: "choice",
        answer: "decline", choices: [{ value: "decline", label: { en: "Decline to answer", ne: "x" } }], is_sensitive: true
      },
    ],
    documents: [
      { document_type: "resume", filename: "Sam Rai – Resume.pdf" },
      { document_type: "cover_letter", filename: "Sam Rai – Cover letter.pdf" },
    ],
    ...overrides,
  };
}

export function load(html: string, url: string): Document {
  document.open();
  document.write(html);
  document.close();
  window.history.replaceState({}, "", new URL(url).pathname);
  return document;
}

/** jsdom has no DataTransfer (and checks FileList's type): the files go straight on the input. */
export function setFiles(input: HTMLInputElement, files: File[]): void {
  const list = Object.assign([...files], { item: (i: number) => files[i] ?? null });
  Object.defineProperty(input, "files", { value: list, configurable: true });
}
