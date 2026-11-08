/**
 * Check on something the server is still working on until it is done.
 *
 * The first value is checked before any waiting, so work finished in the request costs nothing. Gives up with
 * ``PollTimeoutError`` rather than waiting for ever; the work may still finish, so say so rather than "failed".
 */

export interface PollOptions<T> {
  isPending: (value: T) => boolean;
  intervalMs: number;
  timeoutMs: number;
  sleep?: (ms: number) => Promise<void>;
  now?: () => number;
}

export class PollTimeoutError extends Error {
  constructor(waitedMs: number) {
    super(`Still pending after ${waitedMs} ms.`);
    this.name = "PollTimeoutError";
  }
}

const realSleep = (ms: number) => new Promise<void>((resolve) => setTimeout(resolve, ms));

export async function pollUntilSettled<T>(
  first: T,
  check: (latest: T) => Promise<T>,
  { isPending, intervalMs, timeoutMs, sleep = realSleep, now = Date.now }: PollOptions<T>,
): Promise<T> {
  const started = now();
  let value = first;
  while (isPending(value)) {
    if (now() - started >= timeoutMs) throw new PollTimeoutError(now() - started);
    await sleep(intervalMs);
    value = await check(value);
  }
  return value;
}

/** How often to look again while something is pending: soon at first, then less often (for refetchInterval). */
export function backoffInterval(elapsedMs: number): number {
  if (elapsedMs < 10_000) return 1_000;
  if (elapsedMs < 60_000) return 2_000;
  return 5_000;
}
