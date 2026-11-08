import { afterEach, describe, expect, it, vi } from "vitest";

import {
  ADAPTERS, adapterFor, apply, BOARD_LIST, biggestForm, generic, hostMatches, plan, readForm, stripForm,
} from "../src";
import { load, setFiles, sheet } from "./helpers";

afterEach(() => vi.restoreAllMocks());

describe("boards.json: one list of boards", () => {
  it("matches exact hosts, and *.suffix for a company's own subdomain only", () => {
    expect(hostMatches("jobs.lever.co", "jobs.lever.co")).toBe(true);
    expect(hostMatches("*.myworkdayjobs.com", "acme.wd5.myworkdayjobs.com")).toBe(true);
    expect(hostMatches("*.myworkdayjobs.com", "myworkdayjobs.com")).toBe(false);
    expect(hostMatches("*.myworkdayjobs.com", "evil-myworkdayjobs.com")).toBe(false);
    expect(hostMatches("*.myworkdayjobs.com", "acme.myworkdayjobs.com.evil.example")).toBe(false);
  });

  it("has an adapter for every board, and every adapter is a board", () => {
    expect(ADAPTERS.map((a) => a.board).sort()).toEqual(BOARD_LIST.map((b) => b.key).sort());
    for (const adapter of ADAPTERS) {
      const info = BOARD_LIST.find((b) => b.key === adapter.board)!;
      expect(adapter.hosts).toEqual(info.hosts);
    }
  });

  it.each([
    ["https://acme.wd5.myworkdayjobs.com/en-US/External/job/Remote/Engineer_JR1/apply", "board04"],
    ["https://jobs.smartrecruiters.com/HimalTech/744000158069037-data-engineer", "board05"],
    ["https://apply.workable.com/himaltech/j/81B46579FE/apply/", "board06"],
    ["https://himaltech.recruitee.com/o/backend-engineer/c/new", "board07"],
    ["https://himaltech.jobs.personio.de/job/1834171", "board08"],
    ["https://himaltech.breezy.hr/p/98323abf2296-support/apply", "board09"],
    ["https://himaltech.bamboohr.com/careers/42", "board10"],
    ["https://himaltech.teamtailor.com/jobs/123-engineer/applications/new", "board11"],
    ["https://jobs.jobvite.com/himaltech/job/oAbC123/apply", "board12"],
    ["https://careers-himaltech.icims.com/jobs/1234/engineer/job", "board13"],
    ["https://himaltech.applytojob.com/apply/AbC123/Engineer", "board14"],
    ["https://ats.rippling.com/himaltech/jobs/8c1e/apply", "board15"],
    ["https://www.dice.com/job-detail/0b6a4f6e-1111-4111-8111-111111111111", "board16"],
  ])("knows %s as %s", (url, board) => {
    expect(adapterFor(url)?.board).toBe(board);
  });

  it("knows a posting by its own address as well as its form's", () => {
    expect(stripForm(new URL("https://himaltech.recruitee.com/o/backend-engineer/c/new#top")))
      .toBe("https://himaltech.recruitee.com/o/backend-engineer");
    const board04 = adapterFor("https://acme.wd5.myworkdayjobs.com/External/job/Remote/Engineer_JR1/apply/applyManually")!;
    expect(board04.postingUrls(new URL("https://acme.wd5.myworkdayjobs.com/External/job/Remote/Engineer_JR1/apply/applyManually")))
      .toContain("https://acme.wd5.myworkdayjobs.com/External/job/Remote/Engineer_JR1");
  });
});

const PLAIN_FORM = `
  <header><form role="search"><input name="q" aria-label="Search jobs"></form></header>
  <main>
    <h1>Backend Engineer</h1>
    <form id="apply" action="/submit">
      <label for="fn">First name *</label><input id="fn" name="fn" required>
      <label for="ln">Last name *</label><input id="ln" name="ln" required>
      <label for="em">Email address</label><input id="em" name="em" type="email">
      <label for="ph">Phone number</label><input id="ph" name="ph" type="tel">
      <label for="cv">Resume / CV</label><input id="cv" name="cv" type="file">
      <label><input type="checkbox" name="terms"> I agree to the privacy policy</label>
      <button type="submit">Submit application</button>
    </form>
  </main>`;

describe("the generic filler: any form on a site the person allowed", () => {
  it("finds the application form, not the search box, and fills it by its labels without sending it", () => {
    load(PLAIN_FORM, "https://careers.example.org/jobs/7/apply");
    expect(biggestForm(document)?.id).toBe("apply");
    const url = new URL(location.href);
    expect(generic.isForm(url, document)).toBe(true);
    const submitted = vi.fn((e: Event) => e.preventDefault());
    document.addEventListener("submit", submitted, true);
    const result = apply(plan(readForm(document, generic), sheet(), generic), {
      files: { resume: new File(["%PDF-1.7"], "Sam Rai – Resume.pdf", { type: "application/pdf" }) }, setFiles,
    });
    expect((document.getElementById("fn") as HTMLInputElement).value).toBe("Sam");
    expect((document.getElementById("ln") as HTMLInputElement).value).toBe("Rai");
    expect((document.getElementById("em") as HTMLInputElement).value).toBe("sam@example.com");
    expect(result.attached).toEqual(["resume"]);
    expect((document.querySelector("input[name=terms]") as HTMLInputElement).checked).toBe(false); // consent: the person's
    expect(result.leftBlank.map((b) => b.reason)).toContain("consent");
    expect(submitted).not.toHaveBeenCalled();
  });

  it("knows a thank-you page", () => {
    load("<main><h1>Thank you for applying!</h1><p>We'll be in touch.</p></main>", "https://careers.example.org/thanks");
    const url = new URL(location.href);
    expect(generic.isConfirmation(url, document)).toBe(true);
    expect(generic.isForm(url, document)).toBe(false);
  });

  it("reads a form drawn inside web components (open shadow roots)", () => {
    load("<main><apply-form></apply-form></main>", "https://jobs.smartrecruiters.com/HimalTech/1-data-engineer");
    const host = document.querySelector("apply-form")!;
    const shadow = host.attachShadow({ mode: "open" });
    shadow.innerHTML = `<form><label for="first">First name</label><input id="first">
      <label for="mail">Email</label><input id="mail" type="email">
      <label for="tel">Phone</label><input id="tel" type="tel"></form>`;
    const adapter = adapterFor("https://jobs.smartrecruiters.com/HimalTech/1-data-engineer")!;
    const fields = readForm(document, { ...adapter, root: () => document.querySelector("main") });
    expect(fields.map((f) => f.label)).toEqual(["First name", "Email", "Phone"]);
  });
});
