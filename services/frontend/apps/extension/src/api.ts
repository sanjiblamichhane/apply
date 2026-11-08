/** apply's API with a personal token (the extension has no cookie): only what the side panel uses. */
import {
  ApiError, call, createTokenApi, type Application, type Caller, type CopySheet, type FillSheet, type Lookup,
  type Opportunity, type Pack, type Submission,
} from "@apply/api";

export class ExtensionApi {
  private readonly api;

  private readonly fetchImpl: typeof fetch;

  constructor(private readonly baseUrl: string, private readonly token: string, fetchImpl?: typeof fetch) {
    // Never fetch as a method of this object: the browser's fetch needs to be called on its own.
    this.fetchImpl = fetchImpl ?? ((input, init) => fetch(input, init));
    this.api = createTokenApi(baseUrl, token, this.fetchImpl);
  }

  whoami(): Promise<Caller> {
    return call(this.api.GET("/api/v1/tokens/current"));
  }

  /** The application for this form, or null if the posting isn't tracked (or tracked without an application). */
  async lookup(urls: string[]): Promise<Lookup | null> {
    try {
      return await call(this.api.GET("/api/v1/applications/by-url", { params: { query: { url: urls } } }));
    } catch (error) {
      if (error instanceof ApiError && error.code === "OPPORTUNITY_NOT_FOUND") return null;
      throw error;
    }
  }

  /** "Track this job": the posting from the page as the browser shows it, then an application for it. */
  async track(url: string, html: string, existing?: Opportunity): Promise<Application> {
    const opportunity = existing ?? await call(this.api.POST("/api/v1/opportunities", { body: { url, html } }));
    try {
      return await call(this.api.POST("/api/v1/applications", { body: { opportunity_id: opportunity.id } }));
    } catch (error) {
      const id = error instanceof ApiError && error.code === "APPLICATION_EXISTS"
        ? (error.problem as { application_id?: string } | null)?.application_id : undefined;
      if (id) return this.application(id);
      throw error;
    }
  }

  application(id: string): Promise<Application> {
    return call(this.api.GET("/api/v1/applications/{application_id}", { params: { path: { application_id: id } } }));
  }

  pack(key: string): Promise<Pack> {
    return call(this.api.GET("/api/v1/packs/{key}", { params: { path: { key } } }));
  }

  /** A profile's values for the copy panel (the default profile unless one is chosen). Needs profiles:read. */
  copySheet(profileId?: string): Promise<CopySheet> {
    return call(this.api.GET("/api/v1/copy-sheet", { params: { query: profileId ? { profile_id: profileId } : {} } }));
  }

  fillSheet(applicationId: string): Promise<FillSheet> {
    return call(this.api.GET("/api/v1/applications/{application_id}/fill", { params: { path: { application_id: applicationId } } }));
  }

  /** A document's PDF, waiting while it's being made (409 RENDER_PENDING). */
  async pdf(path: string, { tries = 40, wait = 500 } = {}): Promise<ArrayBuffer> {
    for (let i = 0; i < tries; i++) {
      let response: Response;
      try {
        response = await this.fetchImpl(new URL(path, this.baseUrl), {
          headers: { Authorization: `Bearer ${this.token}` }, credentials: "omit",
        });
      } catch (cause) {
        throw new ApiError("NETWORK", 0, null, String(cause));
      }
      if (response.ok) return response.arrayBuffer();
      const problem = await response.json().catch(() => null);
      if (response.status !== 409 || problem?.code !== "RENDER_PENDING") {
        throw new ApiError(problem?.code ?? "INTERNAL", response.status, problem);
      }
      await new Promise((r) => setTimeout(r, wait));
    }
    throw new ApiError("RENDER_PENDING", 409, null);
  }

  submit(applicationId: string, body: { confirmation_url: string; filled: { fields: number; files: string[]; left_blank: string[] } }): Promise<Submission> {
    return call(this.api.POST("/api/v1/applications/{application_id}/submissions", {
      params: { path: { application_id: applicationId } }, body: { ...body, note: "" },
    }));
  }

  undo(submissionId: string): Promise<Submission> {
    return call(this.api.POST("/api/v1/submissions/{submission_id}/undo", { params: { path: { submission_id: submissionId } } }));
  }
}
