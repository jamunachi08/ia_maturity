import { useCallback, useEffect, useRef, useState } from "react";
import { useLocation } from "react-router-dom";
import { Map, X } from "lucide-react";
import { useLanguage } from "./i18n";
import { useSession } from "./session";
import { getPageTour, pageTourKey, type TourStep } from "./pageTourContent";
import "./page-tour.css";

const labels = {
  en: {
    take: "Take page tour",
    skip: "Skip tour",
    skipAll: "Skip automatic tours",
    previous: "Previous",
    next: "Next",
    finish: "Finish",
    step: "Step",
    of: "of",
    close: "Close tour",
    page: "Page tour",
  },
  ar: {
    take: "جولة الصفحة",
    skip: "تخطي الجولة",
    skipAll: "تخطي الجولات التلقائية",
    previous: "السابق",
    next: "التالي",
    finish: "إنهاء",
    step: "الخطوة",
    of: "من",
    close: "إغلاق الجولة",
    page: "جولة الصفحة",
  },
};
const visible = (selector?: string): HTMLElement | null => {
  if (!selector) return null;
  return (
    Array.from(document.querySelectorAll<HTMLElement>(selector)).find((el) => {
      const r = el.getBoundingClientRect();
      const style = getComputedStyle(el);
      return (
        r.width > 0 &&
        r.height > 0 &&
        r.right > 0 &&
        r.left < window.innerWidth &&
        style.visibility !== "hidden" &&
        style.display !== "none"
      );
    }) || null
  );
};
const storageKey = (user: string, key: string) => `grc-page-tour:v1:${encodeURIComponent(user)}:${key}`;
const optOutKey = (user: string) => `grc-page-tour:v1:${encodeURIComponent(user)}:skip-auto`;
// Storage can be unavailable in private or restricted browser contexts.
const read = (key: string) => {
  try {
    return localStorage.getItem(key);
  } catch {
    return null;
  }
};
const write = (key: string) => {
  try {
    localStorage.setItem(key, "1");
  } catch {
    /* The tour still works for this visit. */
  }
};

export default function PageTour() {
  const { session } = useSession(),
    { lang } = useLanguage(),
    location = useLocation();
  const key = pageTourKey(location.pathname),
    user = session.user || "",
    l = labels[lang];
  const enabled = session.workspace_preferences?.show_page_tour !== false;
  const [steps, setSteps] = useState<TourStep[]>([]),
    [index, setIndex] = useState<number | null>(null),
    [rect, setRect] = useState<DOMRect | null>(null);
  const [ready, setReady] = useState(false),
    [panelTop, setPanelTop] = useState(false);
  const dialog = useRef<HTMLElement>(null),
    first = useRef<HTMLButtonElement>(null),
    launch = useRef<HTMLButtonElement>(null),
    activeKey = useRef<string | undefined>(undefined);
  const start = useCallback((tourKey: string) => {
    const available = getPageTour(tourKey).filter((s) => !s.optional || visible(s.selector));
    if (!available.length) return;
    activeKey.current = tourKey;
    setSteps(available);
    setIndex(0);
  }, []);
  // Resets the tour whenever the page, user or enabled flag changes, then schedules a new check.
  useEffect(() => {
    // oxlint-disable-next-line react/set-state-in-effect
    setIndex(null);
    setSteps([]);
    setReady(false);
    activeKey.current = undefined;
    if (!enabled || !key || !user) return;
    let started = false;
    let timer: number | undefined;
    const check = () => {
      if (started) return;
      const main = document.querySelector(".main-content");
      if (!main || main.querySelector(":scope > .loading")) return;
      if (!main.querySelector(".page-title, .onboarding, .guide-hero, .iam-questionnaire")) return;
      started = true;
      setReady(true);
      observer.disconnect();
      if (!read(storageKey(user, key)) && !read(optOutKey(user)))
        timer = window.setTimeout(() => start(key), 450);
    };
    const observer = new MutationObserver(check);
    const main = document.querySelector(".main-content");
    if (main) observer.observe(main, { subtree: true, childList: true });
    check();
    return () => {
      observer.disconnect();
      if (timer !== undefined) window.clearTimeout(timer);
    };
  }, [enabled, key, user, location.pathname, start]);
  const finish = useCallback(
    (all = false) => {
      if (activeKey.current && user) write(storageKey(user, activeKey.current));
      if (all && user) write(optOutKey(user));
      activeKey.current = undefined;
      setIndex(null);
      setRect(null);
      launch.current?.focus();
    },
    [user],
  );
  useEffect(() => {
    if (index === null) return;
    first.current?.focus();
    const target = visible(steps[index]?.selector);
    if (target && !target.closest(".sidebar"))
      target.scrollIntoView({ block: "center", inline: "nearest", behavior: "instant" });
    const measure = () => {
      const element = visible(steps[index]?.selector);
      const r = element?.getBoundingClientRect() || null;
      setRect(r);
      setPanelTop(!!r && r.top > window.innerHeight * 0.52);
    };
    measure();
    window.addEventListener("resize", measure);
    window.addEventListener("scroll", measure, true);
    const onKey = (e: KeyboardEvent) => {
      if (e.key === "Escape") {
        e.preventDefault();
        finish();
      }
    };
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("resize", measure);
      window.removeEventListener("scroll", measure, true);
      window.removeEventListener("keydown", onKey);
    };
  }, [index, steps, finish]);
  if (!enabled || !key) return null;
  const current = index === null ? undefined : steps[index];
  const inset = rect
    ? {
        top: Math.max(0, rect.top - 5),
        left: Math.max(0, rect.left - 5),
        width: Math.min(window.innerWidth, rect.right + 5) - Math.max(0, rect.left - 5),
        height: Math.min(window.innerHeight, rect.bottom + 5) - Math.max(0, rect.top - 5),
      }
    : undefined;
  return (
    <>
      <button
        ref={launch}
        type="button"
        className="page-tour-launch"
        onClick={() => start(key)}
        disabled={!ready}
        title={l.take}
      >
        <Map size={16} />
        <span>{l.take}</span>
      </button>
      {current && (
        <div className="page-tour-layer">
          <div
            className={
              "page-tour-backdrop " + (inset && inset.width > 0 && inset.height > 0 ? "has-highlight" : " ")
            }
            aria-hidden="true"
          />
          {inset && inset.width > 0 && inset.height > 0 && (
            <div className="page-tour-highlight" style={inset} aria-hidden="true" />
          )}
          <section
            ref={dialog}
            className={"page-tour-dialog " + (panelTop ? "at-top" : "at-bottom")}
            role="dialog"
            aria-modal="true"
            aria-labelledby="page-tour-title"
            aria-describedby="page-tour-description"
            onKeyDown={(e) => {
              if (e.key !== "Tab") return;
              const nodes = Array.from(
                dialog.current?.querySelectorAll<HTMLElement>("button:not(:disabled)") || [],
              );
              if (e.shiftKey && document.activeElement === nodes[0]) {
                e.preventDefault();
                nodes[nodes.length - 1]?.focus();
              } else if (!e.shiftKey && document.activeElement === nodes[nodes.length - 1]) {
                e.preventDefault();
                nodes[0]?.focus();
              }
            }}
          >
            <div className="page-tour-top">
              <span>
                {l.page} · {l.step} {(index ?? 0) + 1} {l.of} {steps.length}
              </span>
              <button
                ref={first}
                type="button"
                className="page-tour-close"
                onClick={() => finish()}
                aria-label={l.close}
              >
                <X size={19} />
              </button>
            </div>
            <div className="page-tour-progress" aria-hidden="true">
              <span style={{ width: (((index ?? 0) + 1) / steps.length) * 100 + "%" }} />
            </div>
            <h2 id="page-tour-title">{current[lang][0]}</h2>
            <p id="page-tour-description">{current[lang][1]}</p>
            <div className="page-tour-actions">
              <button type="button" className="page-tour-skip" onClick={() => finish()}>
                {l.skip}
              </button>
              <button type="button" className="page-tour-skip" onClick={() => finish(true)}>
                {l.skipAll}
              </button>
              <span className="page-tour-spacer" />
              <button
                type="button"
                className="button secondary"
                disabled={index === 0}
                onClick={() => setIndex((index ?? 0) - 1)}
              >
                {l.previous}
              </button>
              <button
                type="button"
                className="button primary"
                onClick={() => (index === steps.length - 1 ? finish() : setIndex((index ?? 0) + 1))}
              >
                {index === steps.length - 1 ? l.finish : l.next}
              </button>
            </div>
          </section>
        </div>
      )}
    </>
  );
}
