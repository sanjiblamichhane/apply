/**
 * The README's animated tour (demo/images/apply-tour.gif, and apply-tour.mp4 for posts) and the repository's social preview
 * (demo/images/social-preview.png, 1280 × 640: GitHub → Settings → Social preview), both made from the README's
 * screenshots in demo/images and the logo in docs/brand. Run after the screenshots change:
 *
 *   pnpm --filter @apply/web screenshots && pnpm --filter @apply/extension screenshots
 *   pnpm --filter @apply/web demo-media        # needs ffmpeg for the GIF
 *
 * The tour is a timeline played over the screenshots: a camera that zooms and pans, a drawn cursor that moves and
 * clicks, and a few overlays (the link being typed, the new card on the board). Each frame is drawn by
 * Playwright's Chromium, set in Inter (OFL, a dependency of @apply/ui), and ffmpeg joins them into a GIF.
 */
import { execFileSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { fileURLToPath } from "node:url";

import { chromium } from "@playwright/test";

const root = fileURLToPath(new URL("../../../../../", import.meta.url));
const images = join(root, "demo/images");
const inter = join(root, "services/frontend/packages/ui/node_modules/@fontsource-variable/inter/files/inter-latin-wght-normal.woff2");
const data = (path, type) => `data:${type};base64,${readFileSync(path).toString("base64")}`;
const png = (name) => data(join(images, name), "image/png");
const LOGO = data(join(root, "docs/brand/apply-logo.png"), "image/png");

const BRAND = "#07727d";
const BASE = `
@font-face { font-family: "Inter Demo"; src: url(${data(inter, "font/woff2")}) format("woff2"); font-weight: 100 900; }
* { box-sizing: border-box; margin: 0; }
html, body { width: 100%; height: 100%; }
body { font-family: "Inter Demo", sans-serif; color: #0f1d2b; -webkit-font-smoothing: antialiased; overflow: hidden;
       background: radial-gradient(1200px 600px at 85% -10%, #c9f1f6 0%, transparent 60%),
                   radial-gradient(900px 500px at -10% 110%, #dff3f1 0%, transparent 55%), #f4f8fa; }
.logo { height: 34px; display: block; }
.shot { display: block; border-radius: 14px; border: 1px solid #d5e0e7;
        box-shadow: 0 1px 2px rgb(15 29 43 / .06), 0 24px 48px -16px rgb(15 29 43 / .28); }
`;

const SOCIAL = `<style>${BASE}
  main { height: 100%; display: grid; grid-template-columns: 520px 1fr; align-items: center; padding: 0 0 0 64px; gap: 36px; }
  .logo { height: 64px; margin-bottom: 30px; }
  h1 { font-size: 46px; line-height: 1.08; letter-spacing: -0.03em; font-weight: 780; }
  p { margin-top: 18px; font-size: 21px; line-height: 1.4; color: #3b4d5e; }
  .pills { display: flex; flex-wrap: wrap; gap: 9px; margin-top: 26px; }
  .pills span { font-size: 15px; font-weight: 600; padding: 7px 13px; border-radius: 999px; background: #fff;
                border: 1px solid #cfe3e7; color: ${BRAND}; }
  .stage { height: 100%; position: relative; overflow: hidden; }
  .shot { position: absolute; top: 70px; left: 0; width: 1000px; }
</style><main>
  <div><img class="logo" src="${LOGO}" alt="">
    <h1>Your private job-search agent</h1>
    <p>Finds roles, writes tailored résumés and cover letters, fills the forms. On your machine, with your own model.</p>
    <div class="pills"><span>Local-first</span><span>Open source</span><span>English · नेपाली · Español</span></div></div>
  <div class="stage"><img class="shot" src="${png("web-application.png")}" alt=""></div>
</main>`;

// ── The tour ─────────────────────────────────────────────────────────────────────────────────────────────────
// Coordinates are in each screenshot's CSS pixels (the web shots are 1440 × 900 at 2×, the extension's 1421 × 900).
// cam: [time, centre x, centre y, zoom] (zoom 1 fits the screenshot's width to the stage); cur: [time, x, y].

const LINK = "https://acme-robotics.example/jobs/42";
const SCENES = [
  {
    image: "web-applications.png", w: 1440, h: 900, length: 6.8,
    title: "Paste a job. It lands on your board.", sub: "A link or the posting's text: apply reads it for you.",
    cam: [[0, 720, 372, 1], [0.7, 720, 372, 1], [1.5, 760, 230, 1.75], [2.8, 760, 230, 1.75], [3.6, 1000, 230, 1.75], [4.2, 1000, 230, 1.75], [5.0, 620, 380, 1.25], [6.8, 620, 380, 1.25]],
    cur: [[0, 1100, 760], [1.2, 520, 214], [3.0, 560, 230], [3.8, 1352, 216], [5.1, 470, 488], [6.8, 470, 488]],
    clicks: [1.3, 3.95, 5.25],
    typing: [1.5, 3.4],
    card: 4.3,
  },
  {
    image: "web-application.png", w: 1440, h: 900, length: 7.0,
    title: "Your résumé, written for this job.", sub: "Your own model writes it from your profile. Then every claim is checked against it.",
    cam: [[0, 720, 372, 1], [0.6, 720, 372, 1], [1.5, 1150, 400, 1.9], [2.4, 1150, 400, 1.9], [4.4, 1150, 600, 1.9], [5.4, 1150, 470, 1.6], [7.0, 1150, 470, 1.6]],
    cur: [[0, 470, 488], [1.3, 1321, 316], [2.3, 1321, 316], [4.6, 1360, 560], [7.0, 1360, 560]],
    clicks: [1.45],
    write: { what: "résumé", click: 1.45, from: 1.75, to: 4.5, check: 5.3, status: [990, 343, 330, 32], body: [995, 383, 386, 397] },
  },
  {
    image: "tour-cover-letter.png", w: 1440, h: 900, length: 6.4,
    title: "And a cover letter to match.", sub: "A full page in your voice. Anything your profile doesn't say is flagged for you to fix.",
    cam: [[0, 1150, 300, 1.5], [0.5, 1150, 300, 1.5], [1.2, 1150, 230, 1.9], [2.0, 1150, 230, 1.9], [4.2, 1150, 600, 1.9], [5.4, 1000, 450, 1.25], [6.4, 1000, 450, 1.25]],
    cur: [[0, 1360, 560], [0.9, 1321, 68], [1.8, 1321, 68], [4.0, 1350, 640], [6.4, 1350, 640]],
    clicks: [1.0],
    write: { what: "cover letter", click: 1.0, from: 1.3, to: 4.2, check: 4.9, status: [990, 98, 330, 32], body: [995, 134, 386, 718] },
  },
  {
    image: "extension-fill-preview.png", w: 1421, h: 900, length: 6.4,
    title: "The extension shows what it will fill.", sub: "Untick anything you'd rather type yourself. Nothing is written until you say so.",
    cam: [[0, 710, 380, 1], [0.6, 710, 380, 1], [1.6, 1150, 500, 1.9], [3.0, 1150, 700, 1.9], [4.2, 1130, 760, 1.6], [6.4, 1130, 760, 1.6]],
    cur: [[0, 1350, 640], [1.4, 1040, 455], [3.0, 1040, 690], [4.8, 1211, 866], [6.4, 1211, 866]],
    clicks: [5.0],
  },
  {
    image: "extension-filled.png", w: 1421, h: 900, length: 6.6,
    title: "Filled in seconds. You press Submit.", sub: "Your PDFs attached, and what only you can answer listed beside the form.",
    cam: [[0, 1130, 760, 1.6], [0.4, 1130, 760, 1.6], [1.5, 340, 420, 1.8], [3.0, 340, 640, 1.8], [4.3, 1160, 380, 1.7], [5.8, 710, 380, 1], [6.6, 710, 380, 1]],
    cur: [[0, 1211, 866], [1.4, 300, 445], [2.9, 330, 625], [4.2, 1130, 300], [6.6, 1130, 300]],
    clicks: [],
  },
];
const END_LENGTH = 3.4;
const FADE = 0.45;
const FPS = 15;

const TOUR = `<style>${BASE}
  #head { position: absolute; left: 52px; right: 52px; top: 30px; height: 112px; }
  #head .logo { position: absolute; right: 0; top: 2px; height: 30px; }
  #count { font-size: 15px; font-weight: 600; color: ${BRAND}; letter-spacing: .02em; }
  #title { margin-top: 8px; font-size: 32px; line-height: 1.15; letter-spacing: -0.025em; font-weight: 750; }
  #sub { margin-top: 6px; font-size: 18px; color: #3b4d5e; }
  #stage { position: absolute; left: 40px; top: 156px; width: 1200px; height: 620px; overflow: hidden;
           border-radius: 16px; border: 1px solid #d5e0e7; background: #fff;
           box-shadow: 0 1px 2px rgb(15 29 43 / .06), 0 24px 48px -16px rgb(15 29 43 / .28); }
  .cam { position: absolute; left: 0; top: 0; transform-origin: 0 0; }
  .cam img { display: block; }
  .typed { position: absolute; left: 291px; top: 195px; width: 1014px; height: 39px; background: #fff; border-radius: 6px;
           font-size: 14.5px; padding: 9px 0 0 12px; color: #0f1d2b; white-space: nowrap; }
  .typed i { display: inline-block; width: 1.5px; height: 17px; background: #0f1d2b; vertical-align: -3px; margin-left: 1px; }
  .add { position: absolute; left: 1316px; top: 193px; width: 75px; height: 43px; border-radius: 7px; background: ${BRAND};
         color: #fff; font-size: 14.5px; font-weight: 500; display: grid; place-items: center; }
  .newcard { position: absolute; left: 272px; top: 432px; width: 320px; height: 118px; background: #edf2f6; border-radius: 0 0 11px 11px; }
  .newcard div { position: absolute; left: 8px; right: 8px; top: 4px; height: 104px; background: #fff; border: 1px solid #d5e0e7;
                 border-radius: 10px; box-shadow: 0 0 0 3px rgb(7 114 125 / .18); padding: 13px 14px 0 60px; }
  .newcard b { position: absolute; left: 13px; top: 15px; width: 34px; height: 34px; border-radius: 8px; background: #e8eef3;
               font-size: 11.5px; display: grid; place-items: center; }
  .newcard strong { display: block; font-size: 14px; font-weight: 600; }
  .newcard span { display: block; font-size: 12px; color: #4d5f70; margin-top: 2px; }
  .newcard em { display: block; font-style: normal; font-size: 12px; color: ${BRAND}; margin-top: 8px; font-weight: 500; }
  .status { position: absolute; background: #fff; display: flex; align-items: center; gap: 8px; font-size: 13.5px; color: #3b4d5e; }
  .status b { width: 14px; height: 14px; border-radius: 50%; border: 2px solid #cfe3e7; border-top-color: ${BRAND}; flex: none; }
  .cover { position: absolute; background: #f6f9fb; border-radius: 0 0 10px 10px; }
  .cover::before { content: ""; position: absolute; left: 0; right: 0; top: -26px; height: 26px;
                   background: linear-gradient(rgb(246 249 251 / 0), #f6f9fb); }
  .cover::after { content: ""; position: absolute; left: 14px; top: 2px; width: 9px; height: 15px; background: ${BRAND}; border-radius: 1px; }
  #cursor { position: absolute; left: 0; top: 0; width: 30px; height: 30px; z-index: 5; transform-origin: 3px 3px;
            filter: drop-shadow(0 2px 3px rgb(0 0 0 / .35)); }
  #ring { position: absolute; z-index: 4; border-radius: 50%; border: 3px solid ${BRAND}; background: rgb(7 114 125 / .15); }
  #end { position: absolute; inset: 0; display: grid; place-content: center; justify-items: center;
         text-align: center; gap: 26px; opacity: 0; z-index: 6;
         background: radial-gradient(1200px 600px at 85% -10%, #c9f1f6 0%, transparent 60%), #f4f8fa; }
  #end .logo { height: 88px; }
  #end h1 { font-size: 44px; letter-spacing: -0.03em; font-weight: 750; }
  #end .pills { display: flex; gap: 12px; }
  #end .pills span { font-size: 18px; font-weight: 600; padding: 9px 18px; border-radius: 999px; background: #fff;
                     border: 1px solid #cfe3e7; color: ${BRAND}; }
  #end code { font: 600 20px/1 "Inter Demo", sans-serif; color: #3b4d5e; }
</style>
<div id="head"><img class="logo" src="${LOGO}" alt=""><div id="count"></div><div id="title"></div><div id="sub"></div></div>
<div id="stage">
  ${SCENES.map((s, i) => `<div class="cam" id="cam${i}" style="width:${s.w}px;height:${s.h}px">
      <img src="${png(s.image)}" width="${s.w}" height="${s.h}" alt="">
      ${i === 0 ? `<div class="typed" id="typed"></div><div class="add" id="add">+&nbsp; Add</div>
        <div class="newcard" id="newcard"><div><b>AR</b><strong>Senior Backend Engineer</strong><span>Acme Robotics</span><em>Reading the posting…</em></div></div>` : ""}
      ${s.write ? `<div class="status" id="status${i}" style="left:${s.write.status[0]}px;top:${s.write.status[1]}px;width:${s.write.status[2]}px;height:${s.write.status[3]}px"><b></b><span></span></div>
        <div class="cover" id="cover${i}" style="left:${s.write.body[0]}px;width:${s.write.body[2]}px"></div>` : ""}
    </div>`).join("")}
  <div id="ring"></div>
  <svg id="cursor" viewBox="0 0 30 30"><path d="M3 2 L3 24 L9 18.5 L13 27 L17 25.2 L13 17 L21 17 Z" fill="#fff" stroke="#0f1d2b" stroke-width="1.8" stroke-linejoin="round"/></svg>
</div>
<div id="end"><img class="logo" src="${LOGO}" alt=""><h1>Apply faster. Keep your data.</h1>
  <div class="pills"><span>Runs on your machine</span><span>Your own model</span><span>Open source</span><span>You press Submit</span></div>
  <code>github.com/sanjiblamichhane/apply</code></div>`;

/* global document -- draw() runs in the page, not in Node */
/** Runs in the page: draws the tour at time t (seconds). */
function draw({ t, scenes, endLength, fade, link }) {
  const ease = (x) => (x < 0.5 ? 4 * x * x * x : 1 - (-2 * x + 2) ** 3 / 2);
  const at = (keys, time) => {
    if (time <= keys[0][0]) return keys[0].slice(1);
    for (let k = 1; k < keys.length; k++) {
      if (time <= keys[k][0]) {
        const [a, b] = [keys[k - 1], keys[k]];
        const p = ease((time - a[0]) / (b[0] - a[0]));
        return a.slice(1).map((v, j) => v + (b[j + 1] - v) * p);
      }
    }
    return keys.at(-1).slice(1);
  };
  const W = 1200, H = 620;
  const view = (s, time) => {
    const [cx, cy, z] = at(s.cam, time);
    const k = (W / s.w) * z;
    const tx = Math.min(0, Math.max(W - s.w * k, W / 2 - cx * k));
    const ty = Math.min(0, Math.max(H - s.h * k, H / 2 - cy * k));
    return { k, tx, ty };
  };
  let start = 0, index = scenes.length;
  for (let i = 0; i < scenes.length; i++) {
    if (t < start + scenes[i].length) { index = i; break; }
    start += scenes[i].length;
  }
  const total = scenes.reduce((n, s) => n + s.length, 0);
  const end = document.getElementById("end");
  end.style.opacity = String(Math.min(1, Math.max(0, (t - total) / fade)));
  const i = Math.min(index, scenes.length - 1);
  const local = index === scenes.length ? scenes[i].length : t - start;
  const s = scenes[i];

  scenes.forEach((scene, j) => {
    const cam = document.getElementById(`cam${j}`);
    const shown = j === i || (j === i - 1 && local < fade);
    cam.style.display = shown ? "block" : "none";
    if (!shown) return;
    const v = view(scene, j === i ? local : scene.length);
    cam.style.transform = `translate(${v.tx}px, ${v.ty}px) scale(${v.k})`;
    cam.style.opacity = j === i && i > 0 ? String(Math.min(1, local / fade)) : "1";
    cam.style.zIndex = j === i ? "2" : "1";
  });

  document.getElementById("count").textContent = `${i + 1} / ${scenes.length}`;
  document.getElementById("title").textContent = s.title;
  document.getElementById("sub").textContent = s.sub;

  // The first scene's overlays: the link typed in, Add lit once there's text, then the new card on the board.
  if (scenes[0].typing) {
    const [from, to] = scenes[0].typing;
    const t0 = i === 0 ? local : scenes[0].length;
    const typed = document.getElementById("typed");
    const n = Math.round(Math.min(1, Math.max(0, (t0 - from) / (to - from))) * link.length);
    typed.style.display = t0 >= from ? "block" : "none";
    typed.innerHTML = `${link.slice(0, n)}${t0 < to + 0.4 && Math.floor(t0 * 3) % 2 === 0 ? "<i></i>" : ""}`;
    document.getElementById("add").style.display = n > 0 ? "grid" : "none";
    const card = document.getElementById("newcard");
    const p = Math.min(1, Math.max(0, (t0 - scenes[0].card) / 0.5));
    card.style.opacity = String(p);
    card.style.transform = `translateY(${(1 - ease(p)) * -14}px)`;
  }

  // A document being written: the old text cleared on click, the new one streaming in from the top, then the
  // claim check, then the real screenshot's "Everything here is backed by your profile."
  scenes.forEach((scene, j) => {
    if (!scene.write) return;
    const w = scene.write;
    const t1 = j === i ? local : j < i ? scene.length : 0;
    const status = document.getElementById(`status${j}`);
    const cover = document.getElementById(`cover${j}`);
    const busy = t1 >= w.click && t1 < w.check;
    status.style.display = busy ? "flex" : "none";
    status.querySelector("b").style.transform = `rotate(${t1 * 540}deg)`;
    status.querySelector("span").textContent = t1 < w.to ? `Writing your ${w.what} with your model…` : "Checking every claim against your profile…";
    const p = Math.min(1, Math.max(0, (t1 - w.from) / (w.to - w.from)));
    const [, top, , height] = w.body;
    const reveal = 18 + ease(p) * (height - 18);
    cover.style.display = t1 >= w.click && p < 0.98 ? "block" : "none";
    cover.style.top = `${top + reveal}px`;
    cover.style.height = `${Math.max(0, height - reveal - 1)}px`;
  });

  // The cursor rides with the screenshot, so it points at the same control while the camera moves.
  const cursor = document.getElementById("cursor");
  const ring = document.getElementById("ring");
  const v = view(s, local);
  const [x, y] = at(s.cur, local);
  const sx = v.tx + x * v.k, sy = v.ty + y * v.k;
  const since = Math.min(...s.clicks.map((c) => (local >= c ? local - c : Infinity)), Infinity);
  const press = since < 0.18 ? 0.82 : 1;
  cursor.style.display = index === scenes.length ? "none" : "block";
  cursor.style.transform = `translate(${sx - 3}px, ${sy - 3}px) scale(${press})`;
  if (since < 0.5) {
    const r = 6 + since * 60;
    Object.assign(ring.style, { display: "block", left: `${sx - r}px`, top: `${sy - r}px`, width: `${2 * r}px`, height: `${2 * r}px`, opacity: String(1 - since / 0.5) });
  } else ring.style.display = "none";
  return total + endLength;
}

const browser = await chromium.launch({ headless: true });
/** Waits for the page's web fonts, so no frame shows a fallback font. */
const settle = (p) => p.evaluate(async () => { await document.fonts.ready; });
const work = process.env.KEEP_FRAMES ?? mkdtempSync(join(tmpdir(), "apply-media-"));
try {
  const page = await browser.newPage({ viewport: { width: 1280, height: 640 }, deviceScaleFactor: 2 });
  await page.setContent(SOCIAL, { waitUntil: "load" });
  await settle(page);
  await page.screenshot({ path: join(images, "social-preview.png") });
  // deviceScaleFactor 2 gives 2560 × 1280; GitHub asks for at least 640 × 320 and shows it at 1280 × 640.

  const tour = await browser.newPage({ viewport: { width: 1280, height: 800 }, deviceScaleFactor: 1 });
  await tour.setContent(TOUR, { waitUntil: "load" });
  await settle(tour);
  const args = { scenes: SCENES, endLength: END_LENGTH, fade: FADE, link: LINK };
  const length = await tour.evaluate(draw, { ...args, t: 0 });
  const frames = Math.round(length * FPS);
  for (let f = 0; f < frames; f++) {
    await tour.evaluate(draw, { ...args, t: f / FPS });
    await tour.screenshot({ path: join(work, `f${String(f).padStart(4, "0")}.png`) });
  }
  // A video for posts (small and sharp), and a GIF for the README: one palette for the whole tour, and only the
  // parts of a frame that change are stored.
  const frames_ = join(work, "f%04d.png");
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", frames_, "-c:v", "libx264", "-pix_fmt", "yuv420p",
    "-crf", "20", "-preset", "slow", "-movflags", "+faststart", join(images, "apply-tour.mp4")], { stdio: "inherit" });
  // 10 fps, 800 px wide, 112 colours and no dithering keep it under 10 MB, which GitHub shows inline.
  const filter = `fps=10,scale=800:-1:flags=lanczos,split[a][b];[a]palettegen=max_colors=112:stats_mode=full[p];[b][p]paletteuse=dither=none:diff_mode=rectangle`;
  execFileSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(FPS), "-i", frames_,
    "-filter_complex", filter, "-loop", "0", join(images, "apply-tour.gif")], { stdio: "inherit" });
} finally {
  await browser.close();
  if (!process.env.KEEP_FRAMES) rmSync(work, { recursive: true, force: true });
}
console.log("demo/images/apply-tour.gif, apply-tour.mp4 and social-preview.png");
