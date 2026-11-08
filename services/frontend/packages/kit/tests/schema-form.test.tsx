import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { useState } from "react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { cleanValue, fieldsOf, isFilled, type JsonSchema, SchemaForm, type SchemaFormLabels, SchemaView, toFormValue, type Value } from "../src";

afterEach(cleanup);

// The shape the API serves for a pack (pydantic's JSON schema with apply's x-labels), cut down.
const schema: JsonSchema = {
  type: "object",
  properties: {
    legal_name: { type: "string", maxLength: 300, "x-label": { en: "Legal name", ne: "कानुनी नाम" } },
    address: { type: "string", maxLength: 2000, "x-label": { en: "Address", ne: "ठेगाना" } },
    workplace: {
      type: "string", enum: ["", "onsite", "remote"], "x-label": { en: "Where the work is", ne: "काम गर्ने ठाउँ" },
      "x-options": { "": { en: "Not said", ne: "भनिएको छैन" }, onsite: { en: "On site", ne: "साइटमा" }, remote: { en: "Remote", ne: "टाढाबाट" } },
    },
    certifications: { type: "array", items: { type: "string" }, "x-label": { en: "Certifications", ne: "प्रमाणपत्रहरू" } },
    past_performance: { type: "array", items: { $ref: "#/$defs/PastContract" }, "x-label": { en: "Past contracts", ne: "पहिलेका ठेक्काहरू" } },
  },
  $defs: {
    PastContract: {
      type: "object",
      properties: {
        client: { type: "string", "x-label": { en: "Client", ne: "ग्राहक" } },
        outcome: { type: "string", "x-long": true, "x-label": { en: "What you delivered", ne: "तपाईंले के दिनुभयो" } },
      },
    },
  },
};

const labels: SchemaFormLabels = {
  add: (l) => `Add: ${l}`,
  remove: (l, n) => `Remove ${l} ${n}`,
  item: (l, n) => `${l} ${n}`,
  onePerLine: "One per line.",
};

describe("reading the schema", () => {
  it("gives each field its kind, labels and options, following $refs", () => {
    const fields = fieldsOf(schema);
    expect(fields.map((f) => [f.key, f.kind])).toEqual([
      ["legal_name", "text"], ["address", "long"], ["workplace", "choice"], ["certifications", "list"], ["past_performance", "group"],
    ]);
    expect(fields[2]!.options.map((o) => o.label.ne)).toEqual(["भनिएको छैन", "साइटमा", "टाढाबाट"]);
    expect(fields[4]!.fields.map((f) => [f.key, f.kind])).toEqual([["client", "text"], ["outcome", "long"]]);
  });

  it("fills in what's missing, drops what the schema lacks, and cleans before saving", () => {
    const fields = fieldsOf(schema);
    const form = toFormValue(fields, { legal_name: "Example Software", stray: "x", past_performance: [{ client: "Example Borough" }] });
    expect(form).toEqual({
      legal_name: "Example Software", address: "", workplace: "", certifications: [], past_performance: [{ client: "Example Borough", outcome: "" }],
    });
    const cleaned = cleanValue(fields, {
      ...form, legal_name: "  Example Software  ", certifications: ["ISO 27001", "", "  "], past_performance: [{ client: "Example Borough", outcome: "" }, { client: " ", outcome: "" }],
    });
    expect(cleaned.legal_name).toBe("Example Software");
    expect(cleaned.certifications).toEqual(["ISO 27001"]);
    expect(cleaned.past_performance).toEqual([{ client: "Example Borough", outcome: "" }]);
  });

  it("knows a filled field from an empty one", () => {
    const [, , , list, group] = fieldsOf(schema);
    expect(isFilled(list!, ["", " "])).toBe(false);
    expect(isFilled(list!, ["a"])).toBe(true);
    expect(isFilled(group!, [{ client: "", outcome: "" }])).toBe(false);
    expect(isFilled(group!, [{ client: "Example Borough", outcome: "" }])).toBe(true);
  });
});

function Harness({ locale = "en", onSave }: { locale?: "en" | "ne"; onSave?: (v: Value) => void }) {
  const fields = fieldsOf(schema);
  const [value, setValue] = useState<Value>(() => toFormValue(fields, {}));
  return (
    <form onSubmit={(e) => { e.preventDefault(); onSave?.(cleanValue(fields, value)); }}>
      <SchemaForm schema={schema} value={value} onChange={setValue} locale={locale} labels={labels}
        errors={{ "past_performance.0.client": "Too long." }} />
      <button type="submit">Save</button>
    </form>
  );
}

describe("SchemaForm", () => {
  it("draws labelled controls and edits nested lists", () => {
    const onSave = vi.fn();
    render(<Harness onSave={onSave} />);
    fireEvent.change(screen.getByLabelText("Legal name"), { target: { value: "Example Software" } });
    fireEvent.change(screen.getByLabelText("Where the work is"), { target: { value: "remote" } });
    fireEvent.change(screen.getByLabelText("Certifications"), { target: { value: "ISO 27001\n\nCyber Essentials" } });
    expect(screen.getByLabelText("Certifications")).toHaveProperty("value", "ISO 27001\n\nCyber Essentials");
    expect(screen.getByLabelText("Address").tagName).toBe("TEXTAREA");

    fireEvent.click(screen.getByRole("button", { name: "Add: Past contracts" }));
    fireEvent.click(screen.getByRole("button", { name: "Add: Past contracts" }));
    const first = screen.getByRole("group", { name: "Past contracts 1" });
    fireEvent.change(within(first).getByLabelText("Client"), { target: { value: "Example Borough Council" } });
    expect(within(first).getByLabelText("Client").getAttribute("aria-invalid")).toBe("true");
    expect(within(first).getByText("Too long.")).toBeTruthy();
    fireEvent.click(screen.getByRole("button", { name: "Remove Past contracts 2" }));
    expect(screen.queryByRole("group", { name: "Past contracts 2" })).toBeNull();

    fireEvent.click(screen.getByRole("button", { name: "Save" }));
    expect(onSave).toHaveBeenCalledWith({
      legal_name: "Example Software", address: "", workplace: "remote", certifications: ["ISO 27001", "Cyber Essentials"],
      past_performance: [{ client: "Example Borough Council", outcome: "" }],
    });
  });

  it("speaks Nepali when the person does", () => {
    render(<Harness locale="ne" />);
    expect(screen.getByLabelText("कानुनी नाम")).toBeTruthy();
    expect(screen.getByRole("option", { name: "साइटमा" })).toBeTruthy();
  });
});

describe("SchemaView", () => {
  it("shows only the filled fields, with options by their labels", () => {
    render(<SchemaView schema={schema} locale="en" item={labels.item} value={{
      legal_name: "Example Software", address: "", workplace: "remote", certifications: ["ISO 27001", ""],
      past_performance: [{ client: "Example Borough", outcome: "Live in 9 months" }, { client: "", outcome: "" }],
    }} />);
    const terms = screen.getAllByRole("term").map((t) => t.textContent);
    expect(terms).toEqual(["Legal name", "Where the work is", "Certifications", "Past contracts", "Client", "What you delivered"]);
    expect(screen.getByText("Remote")).toBeTruthy();
    expect(screen.getAllByRole("listitem").map((li) => li.textContent)).toContain("ISO 27001");
    expect(screen.queryByText("Address")).toBeNull();
  });

  it("shows nothing when nothing is filled, and skips what the screen shows elsewhere", () => {
    const { container } = render(<SchemaView schema={schema} locale="en" item={labels.item} value={{}} />);
    expect(container.innerHTML).toBe("");
    render(<SchemaView schema={schema} locale="en" item={labels.item} value={{ legal_name: "N", workplace: "onsite" }} skip={["legal_name"]} />);
    expect(screen.queryByText("Legal name")).toBeNull();
    expect(screen.getByText("On site")).toBeTruthy();
  });
});
