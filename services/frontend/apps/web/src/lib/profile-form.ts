import type { NewProfile, Profile } from "@apply/api";

/** The job profile as a form edits it: lists as text, one item per line. */
export interface ExperienceForm {
  title: string;
  organisation: string;
  start: string;
  end: string;
  location: string;
  highlights: string;
}

export interface EducationForm {
  qualification: string;
  institution: string;
  year: string;
}

export interface LinkForm {
  label: string;
  url: string;
}

export interface ProfileForm {
  name: string;
  summary: string;
  full_name: string;
  email: string;
  phone: string;
  location: string;
  links: LinkForm[];
  skills: string;
  languages: string;
  certifications: string;
  work_authorization: string;
  experience: ExperienceForm[];
  education: EducationForm[];
  tone_instructions: string;
  is_default: boolean;
}

export const emptyExperience = (): ExperienceForm => ({ title: "", organisation: "", start: "", end: "", location: "", highlights: "" });
export const emptyEducation = (): EducationForm => ({ qualification: "", institution: "", year: "" });

export function emptyForm(): ProfileForm {
  return {
    name: "", summary: "", full_name: "", email: "", phone: "", location: "", links: [], skills: "", languages: "",
    certifications: "", work_authorization: "", experience: [emptyExperience()], education: [], tone_instructions: "",
    is_default: false,
  };
}

const lines = (text: string) => text.split("\n").map((l) => l.trim()).filter(Boolean);
const join = (items: unknown) => (Array.isArray(items) ? items.map(String).join("\n") : "");
const str = (value: unknown) => (typeof value === "string" ? value : "");

export function toForm(profile: Profile): ProfileForm {
  const a = profile.attributes as Record<string, unknown>;
  const list = <T,>(key: string) => (Array.isArray(a[key]) ? (a[key] as T[]) : []);
  return {
    name: profile.name, summary: profile.summary, tone_instructions: profile.tone_instructions,
    is_default: profile.is_default,
    full_name: str(a.full_name), email: str(a.email), phone: str(a.phone), location: str(a.location),
    work_authorization: str(a.work_authorization),
    links: list<Record<string, unknown>>("links").map((l) => ({ label: str(l.label), url: str(l.url) })),
    skills: join(a.skills), languages: join(a.languages), certifications: join(a.certifications),
    experience: list<Record<string, unknown>>("experience").map((e) => ({
      title: str(e.title), organisation: str(e.organisation), start: str(e.start), end: str(e.end),
      location: str(e.location), highlights: join(e.highlights),
    })),
    education: list<Record<string, unknown>>("education").map((e) => ({
      qualification: str(e.qualification), institution: str(e.institution), year: str(e.year),
    })),
  };
}

/** The form as the API takes it. Empty rows are dropped, not sent as blanks. */
export function toBody(form: ProfileForm): Required<Pick<NewProfile, "name" | "summary" | "attributes" | "tone_instructions">> & { is_default: boolean } {
  return {
    name: form.name.trim(),
    summary: form.summary.trim(),
    tone_instructions: form.tone_instructions.trim(),
    is_default: form.is_default,
    attributes: {
      full_name: form.full_name.trim(), email: form.email.trim(), phone: form.phone.trim(),
      location: form.location.trim(), work_authorization: form.work_authorization.trim(),
      links: form.links.filter((l) => l.url.trim()).map((l) => ({ label: l.label.trim(), url: l.url.trim() })),
      skills: lines(form.skills), languages: lines(form.languages), certifications: lines(form.certifications),
      experience: form.experience
        .filter((e) => e.title.trim() || e.organisation.trim() || e.highlights.trim())
        .map((e) => ({ title: e.title.trim(), organisation: e.organisation.trim(), start: e.start.trim(),
                       end: e.end.trim(), location: e.location.trim(), highlights: lines(e.highlights) })),
      education: form.education
        .filter((e) => e.qualification.trim() || e.institution.trim())
        .map((e) => ({ qualification: e.qualification.trim(), institution: e.institution.trim(), year: e.year.trim() })),
    },
  };
}

/**
 * An API field error's location ("attributes.experience.0.title") as the form field it belongs to
 * ("experience.0.title"), so the message can sit next to the field.
 */
export function formField(loc: string): string {
  return loc.replace(/^attributes\./, "");
}
