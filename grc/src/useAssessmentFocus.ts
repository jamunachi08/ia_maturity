import { useEffect, useRef, useState } from "react";
import type { MouseEvent, KeyboardEvent, RefObject } from "react";
/** Focus layout is automatic; native fullscreen is requested only from a user gesture. */
export function useAssessmentFocus(
  root: RefObject<HTMLDivElement | null>,
  eligible: boolean,
  user: string,
  name: string,
) {
  const attempted = useRef(false),
    owned = useRef(false),
    activeRef = useRef(false);
  const key = "grc-assessment-view:" + encodeURIComponent(user) + ":" + encodeURIComponent(name);
  const [wanted, setWanted] = useState(() => {
    try {
      return sessionStorage.getItem(key) !== "normal";
    } catch {
      return true;
    }
  });
  const active = eligible && wanted;
  function remember(value: "normal" | "focus") {
    try {
      sessionStorage.setItem(key, value);
    } catch {
      /* Storage restrictions must not prevent answering. */
    }
  }
  function normal() {
    activeRef.current = false;
    remember("normal");
    setWanted(false);
    if (root.current && document.fullscreenElement === root.current)
      void document.exitFullscreen().catch(() => {});
  }
  function native() {
    const element = root.current;
    if (!element || attempted.current || document.fullscreenElement) return;
    attempted.current = true;
    if (!document.fullscreenEnabled || typeof element.requestFullscreen !== "function") return;
    try {
      void element
        .requestFullscreen()
        .then(() => {
          if (!activeRef.current && document.fullscreenElement === element)
            void document.exitFullscreen().catch(() => {});
        })
        .catch(() => {
          /* Continue in full-window focus layout when native fullscreen is denied. */
        });
    } catch {
      /* Older implementations may throw synchronously. */
    }
  }
  function enter() {
    if (!eligible) return;
    activeRef.current = true;
    attempted.current = false;
    remember("focus");
    setWanted(true);
    native();
  }
  function onClickCapture(event: MouseEvent<HTMLElement>) {
    if (active && event.isTrusted && !(event.target as Element).closest("[data-focus-toggle]")) native();
  }
  function onKeyDownCapture(event: KeyboardEvent<HTMLElement>) {
    if (
      active &&
      event.isTrusted &&
      !["Escape", "Tab", "Shift", "Control", "Alt", "Meta"].includes(event.key) &&
      !event.defaultPrevented
    )
      native();
  }
  useEffect(() => {
    activeRef.current = active;
    if (!active) return;
    const element = root.current;
    owned.current = !!element && document.fullscreenElement === element;
    document.body.classList.add("assessment-focus-mode");
    const background = Array.from(
      document.querySelectorAll<HTMLElement>(
        ".app-shell .sidebar,.app-shell .topbar,.workspace-footer,.main-content > :not(.assessment-editor)",
      ),
    );
    const previous = background.map((node) => node.inert);
    background.forEach((node) => (node.inert = true));
    const change = () => {
      if (document.fullscreenElement === element) owned.current = true;
      else if (owned.current) {
        owned.current = false;
        remember("normal");
        setWanted(false);
        activeRef.current = false;
      }
    };
    const escape = (event: globalThis.KeyboardEvent) => {
      if (
        event.key === "Escape" &&
        !event.defaultPrevented &&
        !(event.target instanceof Element && event.target.closest("[role=dialog],[role=listbox]"))
      )
        normal();
    };
    document.addEventListener("fullscreenchange", change);
    window.addEventListener("keydown", escape);
    return () => {
      activeRef.current = false;
      document.removeEventListener("fullscreenchange", change);
      window.removeEventListener("keydown", escape);
      owned.current = false;
      document.body.classList.remove("assessment-focus-mode");
      background.forEach((node, i) => (node.inert = previous[i]));
      if (element && document.fullscreenElement === element) void document.exitFullscreen().catch(() => {});
    };
    // The storage key and element are stable for this keyed assessment editor.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [active, key]);
  return { active, eligible, normal, enter, onClickCapture, onKeyDownCapture };
}
