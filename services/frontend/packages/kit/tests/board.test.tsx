import { cleanup, fireEvent, render, screen, within } from "@testing-library/react";
import { afterEach, describe, expect, it, vi } from "vitest";

import { groupByColumn, KanbanBoard, moveItem, ViewSwitcher } from "../src";

afterEach(cleanup);

const columns = [{ id: "new", label: "New" }, { id: "interview", label: "Interview" }, { id: "offer", label: "Offer" }];
const items = [
  { id: "a", columnId: "new", title: "Backend" },
  { id: "b", columnId: "interview", title: "Data" },
  { id: "c", columnId: "gone", title: "Old stage" },
];

describe("board logic", () => {
  it("groups by column, in column order, and puts an unknown column's items in the first", () => {
    const grouped = groupByColumn(columns, items);
    expect([...grouped.keys()]).toEqual(["new", "interview", "offer"]);
    expect(grouped.get("new")!.map((i) => i.id)).toEqual(["a", "c"]);
    expect(grouped.get("offer")).toEqual([]);
  });

  it("moves an item, and changes nothing when it's already there", () => {
    expect(moveItem(items, "a", "offer").find((i) => i.id === "a")!.columnId).toBe("offer");
    expect(moveItem(items, "a", "new")).toBe(items);
    expect(moveItem(items, "zzz", "new")).toBe(items);
  });
});

describe("KanbanBoard", () => {
  it("is a region of sections, each with a heading, a count and a list (or an empty note)", () => {
    render(<KanbanBoard label="Applications" emptyLabel="None here" columns={columns} items={items}
      formatCount={(n) => `#${n}`} renderCard={(item) => <a href={`/a/${item.id}`}>{item.title}</a>} />);
    const board = screen.getByRole("region", { name: "Applications" });
    const interview = within(board).getByRole("region", { name: /Interview/ });
    expect(within(interview).getByRole("heading").textContent).toContain("#1");
    expect(within(interview).getAllByRole("listitem")).toHaveLength(1);
    const offer = within(board).getByRole("region", { name: /Offer/ });
    expect(within(offer).getByText("None here")).toBeTruthy();
    expect(within(offer).queryByRole("list")).toBeNull();
  });

  it("a drop moves the card, and a failed move puts it back", async () => {
    const onMove = vi.fn().mockRejectedValueOnce(new Error("no"));
    render(<KanbanBoard label="B" emptyLabel="-" columns={columns} items={items} onMove={onMove}
      renderCard={(item) => <span>{item.title}</span>} />);
    const card = screen.getByText("Backend").closest("li")!;
    const offer = screen.getByRole("region", { name: /Offer/ });
    const data = { getData: () => "a", setData: () => {}, effectAllowed: "", dropEffect: "" };
    fireEvent.dragStart(card, { dataTransfer: data });
    fireEvent.drop(offer, { dataTransfer: data });
    expect(onMove).toHaveBeenCalledWith("a", "offer");
    await vi.waitFor(() => expect(within(screen.getByRole("region", { name: /New/ })).queryByText("Backend")).toBeTruthy());
  });
});

describe("ViewSwitcher", () => {
  it("says which view is on, and switches", () => {
    const onChange = vi.fn();
    render(<ViewSwitcher label="View" value="board" onChange={onChange}
      options={[{ value: "board", label: "Board" }, { value: "list", label: "List" }]} />);
    expect(screen.getByRole("button", { name: "Board" }).getAttribute("aria-pressed")).toBe("true");
    fireEvent.click(screen.getByRole("button", { name: "List" }));
    expect(onChange).toHaveBeenCalledWith("list");
  });
});
