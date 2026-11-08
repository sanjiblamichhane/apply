/**
 * Local fake boards for the browser journeys: each board on its own port, serving its form and taking the
 * submission (kept for the test to inspect, at GET /__received: the fields and the files as received), then its
 * thank-you page.
 * Only on 127.0.0.1; nothing reaches a real board.
 */
import { createServer, type IncomingMessage, type Server } from "node:http";

import {
  board03Page,
  board01Confirmation,
  board01Form,
  board02Confirmation,
  board02Form,
  otherConfirmation,
  otherForm,
  POSTINGS,
  BOARD04,
  board04Application,
  board04Job,
} from "./boards";

export interface Received {
  board: string;
  fields: Record<string, string>;
  files: { field: string; filename: string; size: number; head: string }[];
}

export interface FakeBoards {
  urls: Record<"board01" | "board02" | "board03", string>;
  hosts: Record<string, "board01" | "board02" | "board03">;
  /** A careers site on no board apply knows (the generic filler): not one of ``hosts``, so never Auto's. */
  other: { url: string; host: string };
  /** board04's job page, standing in for a career site on *.myworkdayjobs.com (extension only: never Auto's). */
  board04: { url: string; host: string };
  received: Received[];
  close(): Promise<void>;
}

async function body(req: IncomingMessage): Promise<Buffer> {
  const chunks: Buffer[] = [];
  for await (const chunk of req) chunks.push(chunk as Buffer);
  return Buffer.concat(chunks);
}

async function parse(req: IncomingMessage, board: string): Promise<Received> {
  const raw = await body(req);
  const request = new Request("http://local/", {
    method: "POST", headers: { "content-type": req.headers["content-type"] ?? "" }, body: new Uint8Array(raw),
  });
  const form = await request.formData();
  const received: Received = { board, fields: {}, files: [] };
  for (const [key, value] of form.entries()) {
    if (typeof value === "string") received.fields[key] = value;
    else if (value.size > 0) {
      const bytes = Buffer.from(await value.arrayBuffer());
      received.files.push({ field: key, filename: value.name, size: value.size, head: bytes.subarray(0, 5).toString() });
    }
  }
  return received;
}

function serve(board: "board01" | "board02" | "board03" | "other" | "board04", received: Received[]): Server {
  return createServer(async (req, res) => {
    const url = new URL(req.url ?? "/", "http://local");
    const html = (status: number, text: string) => {
      res.writeHead(status, { "content-type": "text/html; charset=utf-8" });
      res.end(text);
    };
    try {
      if (url.pathname === "/__received") {
        res.writeHead(200, { "content-type": "application/json" });
        return res.end(JSON.stringify(received.filter((r) => r.board === board)));
      }
      if (board === "board01") {
        if (req.method === "GET" && url.pathname === POSTINGS.board01.path) return html(200, board01Form());
        if (url.pathname === `${POSTINGS.board01.path}/confirmation`) {
          if (req.method === "POST") received.push(await parse(req, board));
          return html(200, board01Confirmation());
        }
      }
      if (board === "board02") {
        const posting = POSTINGS.board02.path.replace(/\/apply$/, "");
        if (req.method === "GET" && url.pathname === POSTINGS.board02.path) return html(200, board02Form());
        if (req.method === "POST" && url.pathname === POSTINGS.board02.path) {
          received.push(await parse(req, board));
          res.writeHead(303, { location: `${posting}/thanks` });
          return res.end();
        }
        if (url.pathname === `${posting}/thanks`) return html(200, board02Confirmation());
      }
      if (board === "board03") {
        if (req.method === "GET" && url.pathname === POSTINGS.board03.path) return html(200, board03Page("/api/submit"));
        if (req.method === "POST" && url.pathname === "/api/submit") {
          received.push(await parse(req, board));
          res.writeHead(200, { "content-type": "application/json" });
          return res.end("{}");
        }
      }
      if (board === "other") {
        if (req.method === "GET" && url.pathname === POSTINGS.other.path) return html(200, otherForm());
        if (req.method === "POST" && url.pathname === POSTINGS.other.path) {
          received.push(await parse(req, board));
          res.writeHead(303, { location: "/careers/42/thanks" });
          return res.end();
        }
        if (url.pathname === "/careers/42/thanks") return html(200, otherConfirmation());
      }
      if (board === "board04") {
        if (req.method === "GET" && url.pathname === BOARD04.job) return html(200, board04Job());
        if (url.pathname === `${BOARD04.job}/apply/applyManually`) {
          if (req.method === "POST") {
            received.push(await parse(req, board));
            res.writeHead(200, { "content-type": "application/json" });
            return res.end("{}");
          }
          return html(200, board04Application());
        }
      }
      html(404, "<h1>Not found</h1>");
    } catch (error) {
      html(500, `<pre>${String(error)}</pre>`);
    }
  });
}

function listen(server: Server): Promise<number> {
  return new Promise((resolve) => server.listen(0, "127.0.0.1", () => {
    const address = server.address();
    resolve(typeof address === "object" && address ? address.port : 0);
  }));
}

export async function startFakeBoards(): Promise<FakeBoards> {
  const received: Received[] = [];
  const boards = ["board01", "board02", "board03"] as const;
  const servers = boards.map((b) => serve(b, received));
  const ports = await Promise.all(servers.map(listen));
  const urls = Object.fromEntries(boards.map((b, i) => [b, `http://127.0.0.1:${ports[i]}${POSTINGS[b].path}`])) as FakeBoards["urls"];
  const hosts = Object.fromEntries(boards.map((b, i) => [`127.0.0.1:${ports[i]}`, b]));
  const otherServer = serve("other", received);
  const otherPort = await listen(otherServer);
  const other = { url: `http://127.0.0.1:${otherPort}${POSTINGS.other.path}`, host: `127.0.0.1:${otherPort}` };
  const board04Server = serve("board04", received);
  const board04Port = await listen(board04Server);
  const board04 = { url: `http://127.0.0.1:${board04Port}${BOARD04.job}`, host: `127.0.0.1:${board04Port}` };
  return {
    urls, hosts, other, board04, received,
    close: () => Promise.all([...servers, otherServer, board04Server].map((s) => new Promise<void>((r) => s.close(() => r())))).then(() => undefined),
  };
}
