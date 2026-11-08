# Packs

A pack is one kind of thing to apply for. Each has its own profile fields, notice fields, documents, pipeline,
standard questions and sources. Choose one with **Working on** at the top of the sidebar: the screens then show
and make that pack's things. Today covers all of them.

| Pack | Profile | Documents written | Pipeline | Sources |
|---|---|---|---|---|
| **Jobs** | a person: experience, education, skills | resume, cover letter | New → … → Offer, Accepted | companies' own job boards, added by their address |
| **Tenders** | an organisation: capabilities, past contracts, certifications, team | capability statement, tender response | Identified, Bid / no-bid, Preparing, Submitted, Clarification, Awarded / Not awarded / Withdrawn | Contracts Finder (UK) |
| **Grants** | an organisation or a researcher: mission, programmes, past grants, team | letter of inquiry, project narrative | Prospect, Drafting, Submitted, Under review, Awarded / Declined / Withdrawn | Grants.gov (US) |
| **Contracts** | a freelancer or firm: services and rates, projects, availability | proposal, statement of work | Lead, Proposal sent, Negotiating, Won / Lost | none: paste the brief |

Whatever the pack, the rule is the same: documents say only what the profile says, and anything missing is
written as `[CONFIRM: …]` for you to fill in. The claim check, PDFs, the kit and submissions work the same way
in every pack. Auto prepares job applications only, and never sends them: you do.

## Writing a pack

The engine names no pack, and a test checks that it doesn't. So a new pack is a module under
`services/backend/src/apply/packs/` and nothing else:

1. **Models.** A profile model and an opportunity model, with `L("English", "नेपाली")` on every field. The
   labels draw the forms. `options=` labels a choice's values, and `long=True` asks for a text area.
2. **The pack.** A subclass of `DeclarativePack`. Set `key`, `label`, `noun`, `profile_kinds`,
   `document_types` and `pipeline`. Also say which fields hold the title, the issuer, the description and
   the name (`issuer_field`, `name_field`, …), and which search options mean something (`search_options`).
3. **Prompts.** One per written document, in the pack's `prompts/` folder. Copy one from another pack and keep
   its first rule: write only from PROFILE. Scoring, reading notices, the claim check and answers use the
   shared prompts unless the pack has its own.
4. **Sources** (optional). A `SourceAdapter` with its terms, attribution and the least time between fetches.
5. **Register it** in `packs/__init__.py`, and add tests (see [CONTRIBUTING](../CONTRIBUTING.md)).

The web app draws the new pack's forms and pages from its schema with no new screen code. Give it its own
words only where the generic text reads badly (`applications.paste.label.<pack>` and similar, in English,
Nepali and Spanish).
