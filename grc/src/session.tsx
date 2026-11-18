import { applyTheme } from "./theme";
import { createContext, useCallback, useContext, useEffect, useRef, useState } from "react";
import type { ReactNode } from "react";
import type { Session } from "./types";
import { Loading, ErrorNotice } from "./components";
const guest: Session = { enabled: true, kind: "Guest", home: "/login" };
type SessionMutation = <T>(operation: (refreshSession: () => Promise<Session>) => Promise<T>) => Promise<T>;
type SessionContextValue = {
  session: Session;
  loading: boolean;
  error: unknown;
  refresh: () => Promise<Session>;
  withSessionMutation: SessionMutation;
  activeOrganization: string;
  setOrganization: (entity: string) => void;
};
const SessionContext = createContext<SessionContextValue>({
  session: guest,
  loading: true,
  error: undefined,
  refresh: async () => guest,
  withSessionMutation: async (operation) => operation(async () => guest),
  activeOrganization: "",
  setOrganization: () => {},
});
export function SessionProvider({ children }: { children: ReactNode }) {
  const [data, setData] = useState<Session>(),
    [error, setError] = useState<unknown>();
  const [selected, setSelected] = useState<string | null>(null);
  const [authenticationPending, setAuthenticationPending] = useState(false);
  const previous = useRef<string | undefined>(undefined),
    pending = useRef<Promise<Session> | null>(null),
    mounted = useRef(true);
  const currentSession = useRef<Session | undefined>(undefined);
  const mutations = useRef(0),
    mutationQueue = useRef<Promise<unknown>>(Promise.resolve());
  // A single request serves timer, focus and explicit refresh callers. Session
  // data remains page-local; no private bootstrap response is persisted.
  const load = useCallback(() => {
    if (pending.current) return pending.current;
    const request = fetch("/api/method/ia_maturity.grc.api.bootstrap", {
      credentials: "same-origin",
      cache: "no-store",
    })
      .then(async (response) => {
        const body = await response.json();
        if (!response.ok) throw body;
        if (!body.message || !["Guest", "ERP", "Customer", "Auditor"].includes(body.message.kind))
          throw new Error("Unable to load your account. Please sign in again or contact your administrator.");
        const session = body.message as Session;
        applyTheme(session.theme);
        currentSession.current = session;
        if (mounted.current) {
          setData(session);
          setError(undefined);
        }
        return session;
      })
      .catch((failure) => {
        if (mounted.current) setError(failure);
        throw failure;
      })
      .finally(() => {
        pending.current = null;
      });
    pending.current = request;
    return request;
  }, []);
  // Frappe refreshes sid on GET responses too. Pause automatic GETs immediately,
  // drain older responses before changing authentication, and serialize changes.
  // Only this operation's refresh may run before the mutation queue is drained.
  const withSessionMutation = useCallback<SessionMutation>(
    (operation) => {
      mutations.current++;
      setAuthenticationPending(true);
      const run = async () => {
        if (pending.current) await pending.current.catch(() => {});
        const result = await operation(load);
        // A successful auth transition owns its redirect. An older drained response
        // must not redirect to the previous account/home after login or sign-out.
        previous.current = currentSession.current?.access_version;
        return result;
      };
      const work = mutationQueue.current.then(run, run);
      mutationQueue.current = work.then(
        () => undefined,
        () => undefined,
      );
      return work.finally(() => {
        mutations.current--;
        if (!mutations.current && mounted.current) setAuthenticationPending(false);
      });
    },
    [load],
  );
  // Normal mutation refresh callers wait for auth changes, rather than starting
  // a GET whose old sid could overwrite a newly authenticated/logout cookie.
  const refresh = useCallback(async () => {
    while (mutations.current) await mutationQueue.current;
    if (pending.current) await pending.current.catch(() => {});
    return load();
  }, [load]);
  useEffect(() => {
    mounted.current = true;
    const revalidate = () => {
      if (!mutations.current && document.visibilityState !== "hidden") void load().catch(() => {});
    };
    revalidate();
    const timer = window.setInterval(revalidate, 30000);
    window.addEventListener("focus", revalidate);
    window.addEventListener("online", revalidate);
    document.addEventListener("visibilitychange", revalidate);
    return () => {
      mounted.current = false;
      window.clearInterval(timer);
      window.removeEventListener("focus", revalidate);
      window.removeEventListener("online", revalidate);
      document.removeEventListener("visibilitychange", revalidate);
    };
  }, [load]);
  useEffect(() => {
    if (!authenticationPending && data?.access_version) {
      if (previous.current && previous.current !== data.access_version) window.location.assign(data.home);
      previous.current = data.access_version;
    }
  }, [data, authenticationPending]);
  const session = data || guest;
  const saved = selected ?? localStorage.getItem("grc-organization:" + session.user) ?? "";
  const activeOrganization = session.organizations?.some((o) => o.name === saved) ? saved : "";
  const setOrganization = (entity: string) => {
    localStorage.setItem("grc-organization:" + session.user, entity);
    setSelected(entity);
  };
  return (
    <SessionContext.Provider
      value={{
        session,
        loading: !data && !error,
        error,
        refresh,
        withSessionMutation,
        activeOrganization,
        setOrganization,
      }}
    >
      {children}
    </SessionContext.Provider>
  );
}
// Public content and login render independently; private routes and draft
// previews wait for the real server session instead of treating unknown as Guest.
export function SessionGate({ children }: { children: ReactNode }) {
  const { loading, error } = useSession();
  if (error)
    return (
      <div className="standalone">
        <ErrorNotice error={error} />
        <a href="/login">Sign in / تسجيل الدخول</a>
      </div>
    );
  if (loading) return <Loading />;
  return children;
}
export const useSession = () => useContext(SessionContext);
