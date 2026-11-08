import { redirect } from "next/navigation";

/** "Waiting to send" became Ready for you (apply never sends): an old link lands there. */
export default function WaitingPage() {
  redirect("/ready");
}
