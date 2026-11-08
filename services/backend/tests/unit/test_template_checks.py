"""An uploaded template is kept only if it's safe and, filled with a sample, passes WCAG 2.2 AA."""

import pytest

from apply.libs.render import check_template, default_template
from apply.libs.render.checks import contrast

RESUME = default_template("sections")


def problems(html: str, kind="sections") -> set[tuple[str, str]]:
    return {(p.code, p.wcag) for p in check_template(html, kind)}


def test_a_template_changed_within_the_rules_passes():
    mine = (
        RESUME.replace("--accent: #1f3864", "--accent: #0b4f2c")
        .replace("font: 11pt/1.4 Arial, Helvetica, sans-serif", "font: 10.5pt/1.5 Georgia, serif")
        .replace("  </main>", "  <footer><p>References on request.</p></footer>\n  </main>")
        .replace("<main>", '<main>\n  <img alt="" src="data:image/png;base64,iVBORw0KGgo=">')
    )
    assert check_template(mine, "sections") == []


@pytest.mark.parametrize(
    ("change", "expected"),
    [
        (('<main>', '<main><script>alert(1)</script>'), ("unsafe", "")),
        (('<h1>', '<h1 onclick="x()">'), ("unsafe", "")),
        (('<main>', '<main><img alt="" src="https://tracker.example/p.gif">'), ("unsafe", "")),
        (("* { box-sizing", '@import url("https://x.example/a.css"); * { box-sizing'), ("unsafe", "")),
        (("<main>", '<main><iframe title="x"></iframe>'), ("unsafe", "")),
        (("{{title}}", "{{titel}}"), ("placeholder", "")),
        (('lang="{{lang}}"', ""), ("lang", "3.1.1")),
        (("<title>{{title}}</title>", "<title></title>"), ("placeholder", "")),
        (("initial-scale=1", "initial-scale=1, maximum-scale=1"), ("zoom", "1.4.4")),
        (("<main>", "<div>"), ("landmark", "1.3.1")),
        (("<body>", "<body>\n  <p>Outside</p>"), ("landmark", "1.3.1")),
        (("<h1>{{name}}</h1>", "<h1>{{name}}</h1><h1>Again</h1>"), ("heading", "1.3.1")),
        (("<main>", '<main><img src="data:image/png;base64,iVBORw0KGgo=">'), ("image", "1.1.1")),
        (("--text: #000000", "--text: #8a8a8a"), ("contrast", "1.4.3")),
        (("--bg: #ffffff", "--bg: #333333"), ("contrast", "1.4.3")),
        (("color: var(--accent); }", "color: rgba(31, 56, 100, 0.3); }"), ("contrast", "1.4.3")),
        (("a { color: var(--accent); }", "a { color: #1a1a1a; text-decoration: none; }"), ("link_colour", "1.4.1")),
        (("a:focus-visible { outline: 3px solid var(--accent);", "a:focus-visible { outline: none;"),
         ("focus", "2.4.7")),
        (("a:focus-visible { outline: 3px solid var(--accent);", "a:focus-visible { outline: 3px solid #eeeeee;"),
         ("focus", "1.4.11")),
        (("max-width: 8.5in", "width: 8.5in"), ("reflow", "1.4.10")),
        (("li { margin-bottom: 0.2rem; }", "li { height: 14px; overflow: hidden; }"), ("spacing", "1.4.12")),
        (("<main>", '<main tabindex="3">'), ("focus_order", "2.4.3")),
    ],
)  # fmt: skip
def test_what_stops_a_template(change, expected):
    old, new = change
    assert old in RESUME, old
    assert expected in problems(RESUME.replace(old, new))


def test_print_rules_are_checked_as_printed():
    printed = RESUME.replace("a { color: var(--text); text-decoration: none; }", "a { color: #bbbbbb; }")
    found = check_template(printed, "sections")
    assert [p.wcag for p in found] == ["1.4.3"] and "printed" in found[0].message


def test_the_defaults_colours_as_reported():
    assert round(contrast((31 / 255, 56 / 255, 100 / 255, 1), (1, 1, 1, 1)), 1) == 11.6
    assert round(contrast((0, 0, 0, 1), (1, 1, 1, 1))) == 21
