"""
A fake model server for the browser tests (services/frontend/apps/web/tests/e2e): answers like a careful model would,
from what the prompt says, so journeys are deterministic and need no GPU.

- Reading a posting: the first line "Title at Company" becomes the title and company (for any pack: its title
  field, and whichever of company, buyer, funder or client it has).
- Writing: a document built only from the PROFILE block's JSON (name, organisations, skills), after a short
  pause so the "being written" state can be seen.
- Reading a resume into a profile: the first line is the name, then "Email:", "Skills: a, b", and
  "Experience: Title at Organisation" with its "- " highlights under it; nothing else is made up.
- Settings → Model: writer:8b (loaded), writer:14b, and an embedding model that can't be chosen.

    python -m tests.support.e2e_model_server --port 18434 [--write-delay 1.5]
"""

import argparse
import json
import re
import time

import uvicorn

from .servers import FakeNativeServer


def respond(body: dict, write_delay: float) -> str:
    prompt = body["messages"][0]["content"]
    if "format" in body and "claims" in body["format"].get("properties", {}):
        document = prompt.split("<<<DOCUMENT", 1)[-1]
        profile = prompt.split("<<<PROFILE", 1)[-1]
        flagged = [{"quote": "Led a team of 12 engineers", "reason": "Your profile doesn't say you led a team."}]
        # Flagged only when the profile doesn't say it, as the real model is asked to.
        return json.dumps({"claims": [c for c in flagged if c["quote"] in document and c["quote"] not in profile]})
    if "format" in body and "profile" in body["format"].get("properties", {}):
        time.sleep(write_delay / 2)  # long enough to see "Reading…"
        return json.dumps(read_resume(prompt.split("<<<DOCUMENT\n", 1)[-1].split("\nDOCUMENT>>>", 1)[0]))
    if "format" in body and "fit_score" in body["format"].get("properties", {}):
        title = re.search(r"^Title: (.*)$", prompt, re.M)
        job = title.group(1) if title else ""
        good = any(word in job.lower() for word in ("backend", "python", "engineer"))
        return json.dumps(
            {
                "fit_score": 86 if good else 45,
                "reasons": [f"Your Python and Django work fits “{job}”."] if good else ["Few of the skills match."],
                "dealbreakers": [],
            }
        )
    if "format" in body:
        found = re.search(r"<<<POSTING\n(.*?)\nPOSTING>>>", prompt, re.S)
        posting = found.group(1).strip() if found else ""
        first = posting.splitlines()[0] if posting else ""
        title, _, company = first.partition(" at ")
        fields = {key: "" for key in body["format"].get("properties", {})}
        read = {
            "job_title": title.strip(),
            "title": title.strip(),
            **{key: company.strip(" ().") for key in ("company_name", "buyer", "funder", "client")},
            "description_markdown": "\n".join(f"- {line}" for line in posting.splitlines()[1:]),
        }
        return json.dumps(fields | {k: v for k, v in read.items() if k in fields})
    time.sleep(write_delay)
    match = re.search(r"<<<PROFILE\n(.*?)\nPROFILE>>>", prompt, re.S)
    person = json.loads(match.group(1)) if match else {}
    name = (
        person.get("full_name") or person.get("legal_name") or person.get("business_name") or person.get("name")
    ) or "Applicant"
    roles = "\n".join(
        f"- **{e.get('title')}**, {e.get('organisation')}: " + "; ".join(e.get("highlights", []))
        for e in person.get("experience", [])
    )
    skills = ", ".join(person.get("skills", []) or person.get("capabilities", []))
    if "You write cover letters" in prompt:
        return f"Dear Hiring Manager,\n\nI'd like to bring my work as {roles or 'an engineer'} to this role.\n\n{name}"
    # One embellished line, as a small model writes: the claim check is there to catch it.
    return f"# {name}\n\n### Experience\n{roles}\n- Led a team of 12 engineers\n\n### Skills\n{skills}"


def read_resume(text: str) -> dict:
    lines = [line.strip() for line in text.splitlines() if line.strip()]
    profile: dict = {"full_name": lines[0] if lines else "", "email": "", "skills": [], "experience": []}
    for line in lines[1:]:
        if line.lower().startswith("email:"):
            profile["email"] = line.split(":", 1)[1].strip()
        elif line.lower().startswith("skills:"):
            profile["skills"] = [s.strip() for s in line.split(":", 1)[1].split(",") if s.strip()]
        elif line.lower().startswith("experience:"):
            title, _, organisation = line.split(":", 1)[1].strip().partition(" at ")
            profile["experience"].append({"title": title, "organisation": organisation, "highlights": []})
        elif line.startswith("- ") and profile["experience"]:
            profile["experience"][-1]["highlights"].append(line[2:])
    return {"summary": "", "profile": profile}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--port", type=int, required=True)
    parser.add_argument("--write-delay", type=float, default=1.5)
    args = parser.parse_args()
    fake = FakeNativeServer()
    fake.responder = lambda body: respond(body, args.write_delay)
    # What Settings → Model finds: the model in use (loaded), a bigger one, and an embedding model it can't choose.
    fake.models = ["writer:8b", "writer:14b", "embedder:latest"]
    fake.loaded, fake.embedding = {"writer:8b"}, {"embedder:latest"}
    uvicorn.run(fake.app(), host="127.0.0.1", port=args.port, log_level="warning")


if __name__ == "__main__":
    main()
