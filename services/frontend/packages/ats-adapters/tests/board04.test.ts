import { describe, expect, it } from "vitest";

import {
  BOARD04, wireBoard04Dropdowns, board04Job, board04MyExperience, board04MyInformation, board04SignIn,
} from "../fixtures";
import { adapterFor, apply, employerNamed, plan, readForm, signInShowing, workedFor } from "../src";
import { load, setFiles, sheet } from "./helpers";

const at = (path: string) => `https://${BOARD04.host}${path}`;
const board04 = adapterFor(at(BOARD04.job))!;

/** The page as board04's script would leave it, at an address it moved to without loading a page. */
function show(html: string, path: string): Document {
  const doc = load(html, at(path));
  window.history.pushState({}, "", path);
  return doc;
}

describe("board04: the job, signing in, then the form in steps at one address", () => {
  it("is board04 on its career sites' hosts, and not anywhere else", () => {
    expect(board04.board).toBe("board04");
    expect(adapterFor("https://wd3.myworkdaysite.com/recruiting/himaltech/External/job/X/Y_1/apply")?.board).toBe("board04");
    expect(adapterFor("https://myworkdayjobs.com.example/External/job/X/Y_1/apply")?.board).not.toBe("board04");
  });

  it("offers nothing on the job page: the person presses Apply", () => {
    const doc = show(board04Job(), BOARD04.job);
    expect(board04.isForm(new URL(at(BOARD04.job)), doc)).toBe(false);
  });

  it("leaves signing in to the person: a sign-in form is never the application", () => {
    const path = `${BOARD04.job}/apply/applyManually`;
    const doc = show(board04SignIn(), path);
    expect(signInShowing(doc)).toBe(true);
    expect(board04.isForm(new URL(at(path)), doc)).toBe(false);
  });

  it("fills My Information's text by board04's own names, and leaves its dropdowns untouched, with the answer to choose", () => {
    const path = `${BOARD04.job}/apply/applyManually`;
    const doc = show(board04MyInformation(), path);
    wireBoard04Dropdowns(doc);
    expect(board04.isForm(new URL(at(path)), doc)).toBe(true);
    expect(board04.steps).toBe(true);

    const fields = readForm(doc, board04);
    const employed = "Have you ever previously been employed by Himal Tech Group, including any of its subsidiaries?";
    expect(fields.map((f) => [f.label, f.kind])).toEqual([
      ["How Did You Hear About Us?", "dropdown"], ["First Name", "text"], ["Last Name", "text"],
      ["Address Line 1", "text"], ["City", "text"], ["Email Address", "text"], ["Phone Number", "text"],
      ["Phone Device Type", "dropdown"], [employed, "dropdown"],
    ]);
    const saved = sheet();
    saved.answers.find((a) => a.key === "heard_from")!.answer = "Job fair";
    saved.values.past_employers = "Everest Bank\nHimal Tech";
    const result = apply(plan(fields, saved, board04), { adapter: board04 });

    const value = (id: string) => (doc.querySelector(`[data-automation-id="${id}"]`) as HTMLInputElement).value;
    const text = (id: string) => doc.querySelector(`[data-automation-id="${id}"]`)!.textContent;
    expect(value("legalNameSection_firstName")).toBe("Sam");
    expect(value("legalNameSection_lastName")).toBe("Rai");
    expect(value("email")).toBe("sam@example.com");
    expect(value("phone-number")).toBe("+977 980 000 0000");
    expect(result.filled).toBe(4);

    // Its dropdowns: never opened, typed into or pressed. Each is the person's, with the answer to choose.
    expect(doc.querySelector("[data-automation-id=wd-popup]")).toBeNull();
    expect(value("searchBox")).toBe("");
    expect(doc.querySelector("[data-automation-id=selectedItem]")).toBeNull();
    expect(text("previousWorker")).toBe("Select One");
    expect(text("phone-device-type")).toBe("Select One");
    const blank = Object.fromEntries(result.leftBlank.map((b) => [b.label, b]));
    expect(blank["How Did You Hear About Us?"]).toMatchObject({ reason: "custom", suggestion: "Job fair" });
    expect(blank[employed]).toMatchObject({ reason: "custom", suggestion: "Yes" }); // Himal Tech is in the profile
    expect(blank["Phone Device Type"]).toMatchObject({ reason: "unknown" }); // nothing in a profile says
    expect(blank["Phone Device Type"]!.suggestion).toBeUndefined();
    expect(Object.keys(blank)).toContain("City");
    // Never its Next: the person moves on.
    expect(doc.querySelector("[data-automation-id=bottom-navigation-next-button]")).not.toBeNull();
  });

  it("doesn't list a dropdown the person has chosen already, and says nothing about an employer not in the profile", () => {
    const path = `${BOARD04.job}/apply/applyManually`;
    const doc = show(board04MyInformation(), path);
    wireBoard04Dropdowns(doc);
    doc.querySelector("[data-automation-id=previousWorker]")!.textContent = "No";
    const saved = sheet();
    saved.answers.find((a) => a.key === "heard_from")!.answer = "Job fair";
    saved.values.past_employers = "Everest Bank";
    const result = apply(plan(readForm(doc, board04), saved, board04), { adapter: board04 });
    const labels = result.leftBlank.map((b) => b.label);
    expect(labels.some((l) => l.startsWith("Have you ever"))).toBe(false);

    const fresh = show(board04MyInformation(), path);
    const notThere = apply(plan(readForm(fresh, board04), saved, board04), { adapter: board04 });
    const employed = notThere.leftBlank.find((b) => b.label.startsWith("Have you ever"))!;
    expect(employed).toMatchObject({ reason: "no_value" }); // not in the profile: theirs to say
    expect(employed.suggestion).toBeUndefined();
  });

  it("reads the next step when board04 draws it, at the same address, with the resume on its unlabelled uploader", () => {
    const path = `${BOARD04.job}/apply/applyManually`;
    show(board04MyInformation(), path);
    const doc = show(board04MyExperience(), path);
    expect(board04.isForm(new URL(at(path)), doc)).toBe(true);
    const fields = readForm(doc, board04);
    expect(fields.map((f) => f.label)).toEqual(["Resume/CV", "LinkedIn"]);

    const resume = new File(["%PDF-1.7"], "Sam Rai – Resume.pdf", { type: "application/pdf" });
    const result = apply(plan(fields, sheet(), board04), { files: { resume }, setFiles });
    const upload = doc.querySelector("[data-automation-id=file-upload-input-ref]") as HTMLInputElement;
    expect(upload.files?.[0]?.name).toBe("Sam Rai – Resume.pdf");
    expect((doc.querySelector("[data-automation-id=linkedinQuestion]") as HTMLInputElement).value)
      .toBe("https://www.linkedin.com/in/example");
    expect(result.attached).toEqual(["resume"]);
  });

  it("knows the employer a question names, and whether the profile's employers include it", () => {
    const tamu = "Have you ever previously been employed by the Texas A&M University System, including any of its campuses or agencies?";
    expect(employerNamed(tamu)).toBe("the Texas A&M University System");
    expect(workedFor(tamu, "Walmart\nEast Texas A&M University")).toBe(true);
    expect(workedFor(tamu, "University of Texas at Dallas")).toBe(false);
    expect(workedFor("Have you previously worked for Acme Inc.?", "ACME")).toBe(true);
    expect(workedFor("Have you ever worked for us before?", "Acme")).toBe(false); // who "us" is isn't said
    expect(workedFor(tamu, "")).toBe(false);
  });

  it("knows the posting by its job page's address from any step", () => {
    const url = new URL(at(`${BOARD04.job}/apply/applyManually`));
    expect(board04.postingUrls(url)).toContain(at(BOARD04.job));
  });
});
