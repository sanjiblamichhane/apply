"use client";

import { cn, ScrollArea, ScrollBar } from "@apply/ui";
import { type DragEvent, type ReactNode, useId, useMemo, useState } from "react";

import { type BoardColumn, type BoardItem, groupByColumn, moveItem } from "./board";

/** A card dragged between columns moves there; it is never copied. */
const DRAG_EFFECT = "move";

export interface KanbanBoardProps<T extends BoardItem> {
  columns: BoardColumn[];
  items: T[];
  /** The card: it carries its own link and its own "Move to…" menu (the keyboard route for moving). */
  renderCard: (item: T) => ReactNode;
  /** A card dropped on another column. Throw (or reject) to put it back. */
  onMove?: (id: string, columnId: string) => Promise<void> | void;
  /** Accessible name of the whole board. */
  label: string;
  /** Shown in an empty column. */
  emptyLabel: string;
  /** "3" or "३": counts in the reader's digits. */
  formatCount?: (count: number) => string;
  className?: string;
}

/**
 * Columns of cards, one column per stage.
 *
 * Each column is a section with a heading and a list, so a screen reader hears "Interview, list, 3 items".
 * Pointer users can drag a card to another column; everyone can use the card's own "Move to…" menu, which is
 * the same action (WCAG 2.1.1, 2.5.7). On narrow screens the columns stack instead of scrolling sideways.
 */
export function KanbanBoard<T extends BoardItem>({
  columns, items, renderCard, onMove, label, emptyLabel, formatCount = String, className,
}: KanbanBoardProps<T>) {
  const [local, setLocal] = useState(items);
  const [shown, setShown] = useState(items);
  const [dragging, setDragging] = useState<string | null>(null);
  const [over, setOver] = useState<string | null>(null);
  const baseId = useId();

  // New items from the caller replace any optimistic move (React's "adjust state when a prop changes").
  if (items !== shown) {
    setShown(items);
    setLocal(items);
  }
  const grouped = useMemo(() => groupByColumn(columns, local), [columns, local]);

  async function drop(event: DragEvent, columnId: string) {
    event.preventDefault();
    setOver(null);
    const id = dragging ?? event.dataTransfer.getData("text/plain");
    setDragging(null);
    if (!id || !onMove) return;
    const before = local;
    const after = moveItem(local, id, columnId);
    if (after === before) return;
    setLocal(after);
    try {
      await onMove(id, columnId);
    } catch {
      setLocal(before);
    }
  }

  return (
    <div role="region" aria-label={label} className={cn("min-h-0", className)}>
      {/* Sideways on wide screens, in a scroll area with its own bar; stacked on narrow ones. */}
      <ScrollArea>
        <div className="flex flex-col gap-4 md:w-max md:min-w-full md:flex-row md:pb-4">
        {columns.map((column) => {
          const cards = grouped.get(column.id) ?? [];
          const headingId = `${baseId}-${column.id}`;
          return (
            <section
              key={column.id}
              aria-labelledby={headingId}
              className={cn(
                "flex w-full shrink-0 flex-col rounded-xl bg-muted/50 p-2 md:w-80",
                over === column.id && "outline-2 outline-dashed outline-ring",
              )}
              onDragOver={onMove ? (event) => {
                event.preventDefault();
                event.dataTransfer.dropEffect = DRAG_EFFECT;
                if (over !== column.id) setOver(column.id);
              } : undefined}
              onDragLeave={() => setOver((current) => (current === column.id ? null : current))}
              onDrop={onMove ? (event) => drop(event, column.id) : undefined}
            >
              <h2 id={headingId} className="flex items-center justify-between px-2 py-2 text-sm font-semibold">
                <span>{column.label}</span>
                <span className="text-xs font-medium tabular-nums text-muted-foreground">
                  {formatCount(cards.length)}
                </span>
              </h2>
              {cards.length === 0 ? (
                <p className="rounded-lg border border-dashed border-input px-3 py-6 text-center text-sm text-muted-foreground">
                  {emptyLabel}
                </p>
              ) : (
                <ul className="grid gap-2">
                  {cards.map((item) => (
                    <li
                      key={item.id}
                      draggable={Boolean(onMove)}
                      onDragStart={(event) => {
                        setDragging(item.id);
                        event.dataTransfer.effectAllowed = DRAG_EFFECT;
                        event.dataTransfer.setData("text/plain", item.id);
                      }}
                      onDragEnd={() => {
                        setDragging(null);
                        setOver(null);
                      }}
                      className={cn(dragging === item.id && "opacity-60")}
                    >
                      {renderCard(item)}
                    </li>
                  ))}
                </ul>
              )}
            </section>
          );
        })}
        </div>
        <ScrollBar orientation="horizontal" />
      </ScrollArea>
    </div>
  );
}
