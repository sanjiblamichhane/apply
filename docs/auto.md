# Auto

Auto gets strong job matches ready for you to send. It's off until you turn it on for a search, and **Pause
Auto** stops all of it at once. **apply never submits an application.** You do, on the board's own form.

## What happens to a match

1. **The gate.** The match must score at least your minimum (80 by default). Auto must not be paused. You must
   be under the day's limit (5 prepared a day). Nothing may have gone to the same employer in the last 30 days,
   and no other match from that employer can be waiting for you. The posting must still be open.
2. **Writing.** The match is tracked as an application. Its resume and cover letter are written from your
   profile, made into PDFs and checked against it. Any claim warning sends it to **Needs you**, so you can look
   first.
3. **Ready for you.** It waits there with its documents ready. **Open the application** opens the board's
   form. If it's a board the extension knows (or a site you allowed), the extension fills it from your profile
   and saved answers and attaches the PDFs. You check everything and press Submit yourself. The extension then
   records the submission, and the run is done. **I've submitted it** on the application does the same if you
   apply another way. **Stop** takes a match off the list and keeps its application.

## Why apply doesn't send for you

apply used to send applications itself on a few boards, with a headless browser. That stopped on 27 October
2026, because no board offers a candidate a sanctioned way to submit automatically:

- **Submission APIs need the employer's key.** The boards' public APIs let a candidate read postings, but
  submitting through them requires the employer's own credentials.
- **Terms forbid automated access.** Boards' terms of use forbid automated means of accessing or using their
  sites without their written consent.
- **Boards check for bots.** They run CAPTCHA and bot checks.

Filling a form in your own browser while you watch, then pressing Submit yourself, is what boards' own
quick-apply features do. No terms we found forbid it. That's all apply does.

The extension doesn't open a board's own dropdowns or type into them either. It shows you the answer to choose.

## Runs from before

Runs from before 27 October 2026 keep their history: what they sent, their screenshots, and their submissions.
A run that was waiting to be sent is now in **Ready for you**. One that was being sent at that moment is in
**Needs you**, because it may have gone: check the board before you send it again.
