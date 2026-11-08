# Sources

A source is a public listing that apply checks on a schedule. A **search** then picks what's worth a look;
only that is scored by your model, and lands in **Matches**, best fit first.

## A company's job board

In **Sources → Add a source**, paste the address of a company's job board, or of one of its jobs. apply
recognises the supported boards from their address and fills in what it needs; you can change the company name
it shows. Each board is read only through the public listings API or feed it publishes for others to read, and
no more often than its terms allow: at most hourly for some, every 6 or 12 hours for others, sometimes only the
newest postings. The terms are shown when you add it.

An address apply doesn't recognise can't be a source. Track the posting from the page you have open instead
(the browser extension's **Track this job**, or paste its link in **Applications**), and the extension fills its
form there.

## Public-sector listings

| Source | Pack | What it reads | Terms apply keeps to |
|---|---|---|---|
| Contracts Finder | Tenders | UK public sector tenders (open OCDS search) | at most every 6 hours, the last 30 days; Open Government Licence v3.0, attributed |
| Grants.gov | Grants | US federal funding opportunities (public REST API) | at most every 6 hours; details for the first 20 per check |

A listing found again (on another board, or the next day) isn't added twice. A listing that disappears from its
source is marked closed.

US federal tenders need a personal API key, so they wait until sources can hold secrets.

**Not sources, on purpose:** sites without a public listings API, or whose terms forbid collecting their
listings, aren't sources. Their postings come in by link, and the extension fills their forms.

Adding a platform: see CONTRIBUTING.md, "Adding a platform".
