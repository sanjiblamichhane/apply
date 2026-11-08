/** The board's logic, kept out of the component so it can be tested on its own. */

export interface BoardColumn {
  id: string;
  label: string;
}

export interface BoardItem {
  id: string;
  columnId: string;
}

/** Items by column, in column order; an item whose column isn't on the board goes to the first one. */
export function groupByColumn<T extends BoardItem>(columns: BoardColumn[], items: T[]): Map<string, T[]> {
  const grouped = new Map<string, T[]>(columns.map((c) => [c.id, []]));
  const first = columns[0]?.id;
  for (const item of items) {
    const target = grouped.get(item.columnId) ?? (first ? grouped.get(first) : undefined);
    target?.push(item);
  }
  return grouped;
}

/** Move an item to another column (optimistically); returns a new array, the same one if nothing changes. */
export function moveItem<T extends BoardItem>(items: T[], id: string, columnId: string): T[] {
  const found = items.find((item) => item.id === id);
  if (!found || found.columnId === columnId) return items;
  return items.map((item) => (item.id === id ? { ...item, columnId } : item));
}
