import type { Profile } from "@apply/api";
import { describe, expect, it } from "vitest";

import { emptyForm, formField, toBody, toForm } from "@/lib/profile-form";

describe("profile form", () => {
  it("drops empty rows and turns lines into lists", () => {
    const form = { ...emptyForm(), name: " Backend ", skills: "Python\n\n Django \n",
      experience: [{ title: "Engineer", organisation: "Himal Tech", start: "2019", end: "", location: "",
                     highlights: "Built APIs\n\nMoved work to Celery" }, { title: "", organisation: "", start: "", end: "", location: "", highlights: "" }],
      links: [{ label: "Profile", url: "https://linkedin.com/in/example" }, { label: "empty", url: " " }] };
    const body = toBody(form);
    expect(body.name).toBe("Backend");
    expect(body.attributes.skills).toEqual(["Python", "Django"]);
    expect(body.attributes.experience).toEqual([{ title: "Engineer", organisation: "Himal Tech", start: "2019", end: "",
      location: "", highlights: ["Built APIs", "Moved work to Celery"] }]);
    expect(body.attributes.links).toEqual([{ label: "Profile", url: "https://linkedin.com/in/example" }]);
  });

  it("round-trips a profile from the API", () => {
    const profile = { id: "p", pack: "job", kind: "individual", name: "Data", summary: "S", tone_instructions: "Warm",
      is_default: true, created_at: "", updated_at: "",
      attributes: { full_name: "Sam", skills: ["SQL"], experience: [{ title: "Analyst", organisation: "Example Retail", highlights: ["Dashboards"] }],
                    education: [{ qualification: "BSc", institution: "TU", year: "2020" }] } } as Profile;
    const back = toBody(toForm(profile));
    expect(back.attributes.full_name).toBe("Sam");
    expect(back.attributes.experience).toEqual([{ title: "Analyst", organisation: "Example Retail", start: "", end: "", location: "", highlights: ["Dashboards"] }]);
    expect(back.attributes.education).toEqual([{ qualification: "BSc", institution: "TU", year: "2020" }]);
    expect(back.is_default).toBe(true);
  });

  it("puts an API field error next to its field", () => {
    expect(formField("attributes.experience.0.title")).toBe("experience.0.title");
    expect(formField("name")).toBe("name");
  });
});
