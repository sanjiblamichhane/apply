/**
 * The apply API, typed from its OpenAPI schema.
 *
 *   const api = createApi();                                  // same origin: the web app proxies /api
 *   const apps = await call(api.GET("/api/v1/applications", { params: { query: { pack: "job" } } }));
 *
 * ``call`` returns the body, or throws an ``ApiError`` carrying the API's stable ``code`` (or ``NETWORK``
 * when the server didn't answer), which the UI translates with @apply/i18n's ``errorText``.
 */

import createClient, { type Client } from "openapi-fetch";

import type { components, paths } from "./schema";

export type { components, paths } from "./schema";
type Schemas = components["schemas"];

export type ErrorCode = Schemas["ErrorCode"] | "NETWORK";
export type Problem = Schemas["Problem"];
export type Me = Schemas["Me"];
export type Pack = Schemas["PackOut"];
export type Stage = Schemas["StageOut"];
export type Profile = Schemas["ProfileOut"];
export type NewProfile = Schemas["NewProfile"];
export type ProfileChanges = Schemas["ProfileChanges"];
export type ProfileReading = Schemas["ProfileReading"];
export type ProfileSource = Schemas["ProfileSource"];
export type Opportunity = Schemas["OpportunityOut"];
export type OpportunityChanges = Schemas["OpportunityChanges"];
export type Application = Schemas["ApplicationOut"];
export type HistoryEntry = Schemas["HistoryEntry"];
export type Document = Schemas["DocumentOut"];
export type Template = Schemas["TemplateOut"];
export type TemplateCheck = Schemas["TemplateCheck"];
export type TemplateProblem = Schemas["TemplateProblem"];
export type TemplateKind = Template["kind"];
export type ModelStatus = Schemas["ModelStatus"];
export type Models = Schemas["Models"];
export type ModelServer = Schemas["EndpointOut"];
export type FoundModel = Schemas["FoundModelOut"];
export type ModelInUse = Schemas["ModelInUse"];
export type ChooseModel = Schemas["ChooseModel"];
export type ModelChosen = Schemas["ModelChosen"];
export type Label = Schemas["Label"];
export type SourceKind = Schemas["SourceKind"];
export type Source = Schemas["SourceOut"];
export type NewSource = Schemas["NewSource"];
export type Search = Schemas["SearchOut"];
export type NewSearch = Schemas["NewSearch"];
export type Criteria = Schemas["Criteria"];
export type Match = Schemas["MatchOut"];
export type MatchCounts = Schemas["MatchCounts"];
export type Briefing = Schemas["BriefingOut"];
export type ClaimWarning = Schemas["ClaimWarning"];
export type Answer = Schemas["AnswerOut"];
export type Kit = Schemas["Kit"];
export type CopySheet = Schemas["CopySheetOut"];
export type CopyTab = Schemas["CopyTabOut"];
export type CopyItem = Schemas["CopyItemOut"];
export type CopyProfile = Schemas["CopyProfile"];
export type Submission = Schemas["SubmissionOut"];
export type Token = Schemas["TokenOut"];
export type NewToken = Schemas["NewToken"];
export type CreatedToken = Schemas["CreatedToken"];
export type Scope = Token["scopes"][number];
export type Caller = Schemas["Caller"];
export type Lookup = Schemas["Lookup"];
export type FillSheet = Schemas["FillSheet"];
export type FillDocument = Schemas["FillDocument"];
export type AutoSettings = Schemas["AutoSettings"];
export type AutoSettingsChanges = Schemas["AutoSettingsChanges"];
export type AutoRun = Schemas["AutoRunOut"];
export type AutoCounts = Schemas["AutoCounts"];

export type Api = Client<paths>;

export function createApi(baseUrl = "", fetchImpl?: typeof fetch): Api {
  return createClient<paths>({
    baseUrl,
    credentials: "same-origin",
    headers: { Accept: "application/json, application/problem+json" },
    ...(fetchImpl ? { fetch: fetchImpl } : {}),
  });
}

/**
 * The API from somewhere a cookie can't go (the browser extension): every request carries a personal API
 * token, and no cookie is ever sent.
 */
export function createTokenApi(baseUrl: string, token: string, fetchImpl?: typeof fetch): Api {
  return createClient<paths>({
    baseUrl,
    credentials: "omit",
    headers: { Accept: "application/json, application/problem+json", Authorization: `Bearer ${token}` },
    ...(fetchImpl ? { fetch: fetchImpl } : {}),
  });
}

export class ApiError extends Error {
  readonly code: ErrorCode;
  readonly status: number;
  readonly problem: Problem | null;

  constructor(code: ErrorCode, status: number, problem: Problem | null, message?: string) {
    super(message ?? problem?.detail ?? code);
    this.name = "ApiError";
    this.code = code;
    this.status = status;
    this.problem = problem;
  }

  /** Field errors by dotted location ("attributes.skills"), for putting messages next to fields. */
  get fieldErrors(): Record<string, string> {
    const found: Record<string, string> = {};
    for (const e of this.problem?.errors ?? []) {
      const loc = e.loc.filter((part) => part !== "body").join(".");
      if (loc) found[loc] = e.msg;
    }
    return found;
  }
}

export function isApiError(value: unknown, code?: ErrorCode): value is ApiError {
  return value instanceof ApiError && (code === undefined || value.code === code);
}

function asProblem(body: unknown): Problem | null {
  if (body && typeof body === "object" && "code" in body && "status" in body) return body as Problem;
  return null;
}

/** The body of a successful call; an ApiError otherwise. */
export async function call<T>(request: Promise<{ data?: T; error?: unknown; response: Response }>): Promise<T> {
  let result: { data?: T; error?: unknown; response: Response };
  try {
    result = await request;
  } catch (cause) {
    throw new ApiError("NETWORK", 0, null, cause instanceof Error ? cause.message : String(cause));
  }
  const { data, error, response } = result;
  if (response.ok) return data as T;
  const problem = asProblem(error);
  if (problem) throw new ApiError(problem.code, response.status, problem);
  // Not from the API (a proxy's 502 while the backend is down, say).
  throw new ApiError(response.status >= 500 ? "NETWORK" : "INTERNAL", response.status, null);
}
