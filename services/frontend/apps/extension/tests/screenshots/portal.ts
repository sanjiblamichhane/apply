/**
 * Dresses the fake board's bare form as a company careers page for the README's pictures: a fictional employer
 * (Acme Robotics), its top bar, the job's header, the form in a card and the role beside it. Only the look and
 * the layout change; every field keeps its id, name and label, so the extension reads the form as the journeys do.
 * Text is set in Inter (OFL, already a dependency of @apply/ui), embedded so the page needs no network.
 */
import { readFileSync } from "node:fs";
import { fileURLToPath } from "node:url";

import type { Page } from "@playwright/test";

const INTER = fileURLToPath(new URL(
  "../../../../packages/ui/node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2", import.meta.url));

const CSS = (font: string) => `
@font-face { font-family: "Inter Demo"; src: url(data:font/woff2;base64,${font}) format("woff2"); font-weight: 100 900; }
:root { --ink: #101828; --soft: #475467; --line: #e4e7ec; --field: #d0d5dd; --brand: #4338ca; --brand-2: #7c3aed;
        --page: #f5f6fa; --ok: #067647; --ok-bg: #ecfdf3; }
* { box-sizing: border-box; }
body { margin: 0; background: var(--page); color: var(--ink); font: 15px/1.5 "Inter Demo", sans-serif;
       -webkit-font-smoothing: antialiased; }
.acme-top { height: 64px; background: #fff; border-bottom: 1px solid var(--line); display: flex; align-items: center;
            justify-content: space-between; padding: 0 32px; }
.acme-brand { display: flex; align-items: center; gap: 10px; font-weight: 700; font-size: 17px; letter-spacing: -0.01em; }
.acme-brand small { font-weight: 500; color: var(--soft); font-size: 14px; padding-left: 10px; margin-left: 2px;
                    border-left: 1px solid var(--line); }
.acme-logo { width: 32px; height: 32px; border-radius: 9px; background: linear-gradient(135deg, var(--brand), var(--brand-2));
             display: grid; place-items: center; }
.acme-nav { display: flex; align-items: center; gap: 26px; font-size: 14px; color: var(--soft); font-weight: 500; }
.acme-nav b { color: #fff; background: var(--ink); padding: 8px 14px; border-radius: 999px; font-weight: 600; }
main { max-width: 1000px; margin: 0 auto; padding: 22px 32px 48px; }
.acme-crumb { font-size: 13px; color: var(--soft); margin-bottom: 10px; }
.acme-crumb span { color: var(--brand); font-weight: 600; }
main h1 { font-size: 30px; line-height: 1.2; letter-spacing: -0.02em; margin: 0 0 12px; font-weight: 700; }
.acme-chips { display: flex; flex-wrap: wrap; gap: 8px; margin-bottom: 22px; }
.acme-chips span { font-size: 13px; font-weight: 500; padding: 4px 11px; border-radius: 999px; background: #fff;
                   border: 1px solid var(--line); color: var(--soft); }
.acme-chips span.pay { background: var(--ok-bg); border-color: #abefc6; color: var(--ok); }
.acme-grid { display: grid; grid-template-columns: minmax(0, 1fr) 280px; gap: 24px; align-items: start; }
.acme-card { background: #fff; border: 1px solid var(--line); border-radius: 16px;
             box-shadow: 0 1px 2px rgb(16 24 40 / .05), 0 8px 24px -12px rgb(16 24 40 / .12); }
form.acme-card { padding: 26px 28px 28px; display: grid; grid-template-columns: 1fr 1fr; column-gap: 16px; }
form h2 { grid-column: 1 / -1; margin: 0; font-size: 19px; letter-spacing: -0.01em; }
.acme-lede { grid-column: 1 / -1; margin: 2px 0 18px; color: var(--soft); font-size: 14px; }
.field { grid-column: 1 / -1; margin-bottom: 15px; display: flex; flex-direction: column; gap: 6px; }
.field.half { grid-column: auto; }
.field > label, .field > .label { font-size: 14px; font-weight: 600; color: #344054; }
.field span[aria-hidden] { color: #d92d20; margin-left: 2px; }
input[type=text], input[type=email], input[type=tel], select, textarea {
  font: inherit; color: var(--ink); width: 100%; height: 42px; padding: 0 13px; background: #fff;
  border: 1px solid var(--field); border-radius: 9px; box-shadow: 0 1px 2px rgb(16 24 40 / .05); }
textarea { height: 92px; padding: 10px 13px; resize: none; }
select { appearance: none; padding-right: 36px; background: #fff url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='8'%3E%3Cpath d='M1 1l5 5 5-5' fill='none' stroke='%23667085' stroke-width='1.8'/%3E%3C/svg%3E") no-repeat right 14px center; }
input[type=file] { font: inherit; font-size: 14px; color: var(--soft); width: 100%; padding: 9px; border: 1.5px dashed var(--field);
                   border-radius: 10px; background: #fafbff; }
input[type=file]::file-selector-button { font: inherit; font-size: 13px; font-weight: 600; color: var(--brand);
  background: #eef0ff; border: 0; border-radius: 7px; padding: 7px 12px; margin-right: 12px; }
fieldset.eeoc { grid-column: 1 / -1; border: 1px solid var(--line); border-radius: 12px; padding: 14px 16px 2px; margin: 4px 0 16px; }
fieldset.eeoc legend { font-weight: 600; font-size: 14px; padding: 0 6px; }
.field.checkbox { flex-direction: row; align-items: flex-start; gap: 10px; font-size: 14px; color: var(--soft); }
.field.checkbox input { width: 18px; height: 18px; margin-top: 2px; accent-color: var(--brand); }
.field.checkbox label { font-weight: 400; }
button[type=submit] { grid-column: 1 / -1; justify-self: start; font: inherit; font-weight: 600; color: #fff;
  background: linear-gradient(135deg, var(--brand), var(--brand-2)); border: 0; border-radius: 10px; padding: 12px 22px; }
aside .acme-card { padding: 20px 22px; margin-bottom: 16px; }
aside h3 { margin: 0 0 8px; font-size: 15px; }
aside p, aside li { font-size: 14px; color: var(--soft); margin: 0 0 8px; }
aside ul { padding-left: 18px; margin: 0; }
aside dl { margin: 0; display: grid; grid-template-columns: auto 1fr; gap: 6px 12px; font-size: 14px; }
aside dt { color: var(--soft); }
aside dd { margin: 0; font-weight: 500; text-align: right; }
`;

const LOGO = `<svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="#fff" stroke-width="2.4"
  stroke-linecap="round" stroke-linejoin="round" aria-hidden="true"><rect x="5" y="8" width="14" height="11" rx="3"/>
  <path d="M12 4v4M9 13h.01M15 13h.01"/></svg>`;

/** Restyle and rearrange the open board page (call before the extension reads it). */
export async function dressAsPortal(page: Page): Promise<void> {
  const font = readFileSync(INTER).toString("base64");
  await page.addStyleTag({ content: CSS(font) });
  await page.evaluate(({ logo }) => {
    const main = document.querySelector("main")!;
    const form = main.querySelector("form")!;
    const title = main.querySelector("h1")!;
    const about = main.querySelector(".job__description");

    // The form asks for a profile on a named professional network; the README's pictures name no one.
    document.querySelectorAll("label").forEach((label) => {
      if (/linkedin/i.test(label.textContent ?? "")) label.closest(".field")?.remove();
    });
    ["first_name", "last_name", "email", "phone"].forEach((id) => document.getElementById(id)?.closest(".field")?.classList.add("half"));
    form.classList.add("acme-card");
    form.querySelector("h2")?.insertAdjacentHTML("afterend",
      `<p class="acme-lede">About five minutes. Fields marked <span style="color:#d92d20">*</span> are required.</p>`);

    document.body.insertAdjacentHTML("afterbegin", `<header class="acme-top">
      <div class="acme-brand"><span class="acme-logo">${logo}</span>Acme Robotics<small>Careers</small></div>
      <nav class="acme-nav"><span>Teams</span><span>Life at Acme</span><span>Benefits</span><b>All jobs</b></nav></header>`);

    const hero = document.createElement("div");
    hero.innerHTML = `<div class="acme-crumb"><span>← All jobs</span> &nbsp;/&nbsp; Engineering &nbsp;/&nbsp; Platform</div>`;
    hero.append(title);
    hero.insertAdjacentHTML("beforeend", `<div class="acme-chips"><span>Remote · US</span><span>Full-time</span>
      <span>Engineering</span><span class="pay">$165k – $195k</span></div>`);

    const aside = document.createElement("aside");
    aside.innerHTML = `<div class="acme-card"><h3>About the role</h3><div class="acme-about"></div><ul>
        <li>Own services that move robots' work orders</li><li>Design APIs other teams love to use</li>
        <li>Mentor engineers in a team of eight</li></ul></div>
      <div class="acme-card"><dl><dt>Team</dt><dd>Fleet Platform</dd><dt>Location</dt><dd>Remote, US</dd>
        <dt>Posted</dt><dd>3 days ago</dd></dl></div>`;
    if (about) aside.querySelector(".acme-about")!.append(...Array.from(about.childNodes));
    about?.remove();
    main.querySelector(".job__header")?.remove();

    const grid = document.createElement("div");
    grid.className = "acme-grid";
    grid.append(form, aside);
    main.replaceChildren(hero, grid);
  }, { logo: LOGO });
  await page.evaluate(() => document.fonts.ready);
}
