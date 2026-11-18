import { useEffect, useState } from "react";
import type { SiteContent } from "./siteContent";

// Only the anonymous, approved-content endpoint uses this small public loader.
// Draft previews remain in the authenticated SDK/provider and never share it.
export function usePublishedContent(enabled = true) {
  const [data, setData] = useState<SiteContent>(),
    [error, setError] = useState<unknown>();
  useEffect(() => {
    if (!enabled) return;
    let active = true,
      pending = false;
    const controller = new AbortController();
    async function refresh() {
      if (pending || document.visibilityState === "hidden") return;
      pending = true;
      try {
        const response = await fetch("/api/method/ia_maturity.grc.public.site_content", {
          credentials: "same-origin",
          signal: controller.signal,
        });
        const body = await response.json();
        if (!response.ok) throw body;
        if (!body.message || typeof body.message !== "object") throw new Error("Invalid published content");
        if (active) {
          setData(body.message);
          setError(undefined);
        }
      } catch (failure) {
        if (active) setError(failure);
      } finally {
        pending = false;
      }
    }
    const revalidate = () => {
      void refresh();
    };
    revalidate();
    const timer = window.setInterval(revalidate, 30000);
    window.addEventListener("focus", revalidate);
    document.addEventListener("visibilitychange", revalidate);
    return () => {
      active = false;
      controller.abort();
      window.clearInterval(timer);
      window.removeEventListener("focus", revalidate);
      document.removeEventListener("visibilitychange", revalidate);
    };
  }, [enabled]);
  return { data, error };
}
