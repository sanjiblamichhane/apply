// The Spanish guide files, as text. Loaded with import() from ../guides.ts so they ship as a chunk of their own.
import { texts } from "../texts";

export default texts(import.meta.glob<{ default: string }>("../guides/*/es.md", { query: "?raw", eager: true }));
