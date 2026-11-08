"""
Each person's document templates over HTTP: the default to start from, an upload checked before it's kept (and
the problems said when it isn't), a sample previewed, documents made again in the new template, and back to
the default.
"""

from apply.libs.render import default_template

from .test_review_and_kit import model, poll_pdf, written

GREEN = default_template("sections").replace("--accent: #1f3864", "--accent: #0b4f2c")


async def test_the_default_until_one_is_kept(client, owner):
    got = (await client.get("/api/v1/templates/sections")).json()
    assert got["custom"] is False and got["html"] == default_template("sections")
    assert "<h2>Professional Summary</h2>" in got["preview_html"] and "{{" not in got["preview_html"]
    letter = (await client.get("/api/v1/templates/letter/default")).json()
    assert letter["html"] == default_template("letter") and "<p>Sincerely,<br>Lorem Ipsum</p>" in letter["preview_html"]


async def test_a_template_with_problems_is_said_and_not_kept(client, owner):
    bad = (
        default_template("sections")
        .replace("--text: #000000", "--text: #9a9a9a")
        .replace("<main>", '<main>\n  <script>fetch("https://x.example")</script>')
    )
    checked = (await client.post("/api/v1/templates/sections/check", json={"html": bad})).json()
    codes = {(p["code"], p["wcag"]) for p in checked["problems"]}
    assert ("unsafe", "") in codes and ("contrast", "1.4.3") in codes
    refused = await client.put("/api/v1/templates/sections", json={"html": bad, "filename": "mine.html"})
    assert refused.status_code == 422 and refused.json()["code"] == "TEMPLATE_PROBLEMS"
    assert refused.json()["problems"] == checked["problems"]
    assert (await client.get("/api/v1/templates/sections")).json()["custom"] is False

    no_place = default_template("letter").replace("{{content}}", "")
    unfillable = (await client.post("/api/v1/templates/letter/check", json={"html": no_place})).json()
    assert unfillable["preview_html"] == "" and unfillable["problems"][0]["code"] == "placeholder"


async def test_documents_are_made_again_in_the_template_kept_and_back(client, owner, model_server, worker):
    model(model_server)
    app_id, doc = await written(client, worker)
    path = f"/api/v1/applications/{app_id}/documents/{doc['id']}"
    before = (await poll_pdf(client, f"{path}/html")).text
    assert "#1f3864" in before

    kept = await client.put("/api/v1/templates/sections", json={"html": GREEN, "filename": "green.html"})
    assert kept.status_code == 200, kept.text
    assert kept.json()["custom"] is True and kept.json()["filename"] == "green.html"
    after = (await poll_pdf(client, f"{path}/html")).text
    assert "#0b4f2c" in after and "<h1>Sam Rai</h1>" in after
    assert (await poll_pdf(client, f"{path}/pdf")).content.startswith(b"%PDF-")

    assert (await client.delete("/api/v1/templates/sections")).status_code == 204
    assert (await client.get("/api/v1/templates/sections")).json()["custom"] is False
    assert "#1f3864" in (await poll_pdf(client, f"{path}/html")).text


async def test_templates_are_ones_own(client, owner, other_client):
    await client.put("/api/v1/templates/letter", json={"html": GREEN.replace("{{content}}", "{{content}}")})
    assert (await other_client.get("/api/v1/templates/letter")).json()["custom"] is False
    assert (await client.get("/api/v1/templates/nonsense")).status_code == 422
