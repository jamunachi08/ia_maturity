import { useAssessmentTypes } from "../assessmentTypes";
import Select from "../Select";
import OrganizationProfile, { ProfileExtras } from "../OrganizationProfile";
import AuditScope, { ScopeSummary } from "../AuditScope";
import { useAssessmentFocus } from "../useAssessmentFocus";
import MaturityPanel from "../MaturityPanel";
import ReportDelivery from "./ReportDelivery";
import { ActivityPage } from "./Operations";
import { useCallback, useEffect, useRef, useState } from "react";
import { Link, Navigate, useNavigate, useParams } from "react-router-dom";
import {
  ArrowLeft,
  ArrowRight,
  Check,
  Paperclip,
  Save,
  ShieldCheck,
  Clock3,
  LoaderCircle,
  Maximize2,
  Minimize2,
} from "lucide-react";
import { useData, useMutation, upload } from "../api";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
import { Button, ErrorNotice, Field, Form, Loading, Modal, PageTitle, Status } from "../components";
import type { Assessment, Question } from "../types";
import { liveOverall, parseSelected } from "../liveScore";
import "../assessment.css";

function selectedLetters(raw?: string) {
  const parsed = parseSelected(raw);
  return parsed.kind === "letters" ? parsed.letters : parsed.kind === "N/A" ? ["N/A"] : [];
}

function encodeSelection(letters: string[]) {
  if (letters.includes("N/A")) return "N/A";
  return [...new Set(letters.filter((l) => l !== "N/A"))]
    .sort((a, b) => "ABCD".indexOf(a) - "ABCD".indexOf(b))
    .join(",");
}

export function AssignTeam({
  assessment,
  onClose,
  onDone,
}: {
  assessment: Assessment;
  onClose: () => void;
  onDone: () => void;
}) {
  const { t } = useLanguage(),
    { data, error } = useData<any>("organization_detail", { name: assessment.entity }),
    save = useMutation("assign_assessment");
  return (
    <Modal title="Assign team" onClose={onClose}>
      <Form
        onSubmit={async (d) => {
          await save.execute({ ...d, name: assessment.grc_assignment });
          onDone();
          onClose();
        }}
      >
        <p>
          {t(
            "Choose from staff already assigned to this customer. If no eligible person is listed, ask a department manager to update the customer assignments first. You can cancel without changing the team.",
          )}
        </p>
        <ErrorNotice error={error} />
        {!data && !error && <Loading />}
        {["Consultant", "Reviewer"].map((role) => {
          const current = role === "Consultant" ? assessment.consultant : assessment.reviewer;
          const staff = data?.auditors?.filter((a: any) => a.active && a.responsibility === role) || [];
          return (
            <Field key={role} label={role}>
              <Select name={role.toLowerCase()} disabled={!data || !!error} defaultValue={current || ""}>
                <option value="">{t("No selection")}</option>
                {current && !staff.some((a: any) => a.auditor === current) && (
                  <option value={current}>{current}</option>
                )}
                {staff.map((a: any) => (
                  <option key={a.name} value={a.auditor}>
                    {a.auditor}
                  </option>
                ))}
              </Select>
            </Field>
          );
        })}
        <div className="form-grid">
          <Field label="Due date">
            <input type="date" name="due_date" defaultValue={assessment.due_date || ""} />
          </Field>
          <Field label="Review due date">
            <input type="date" name="review_due_date" />
          </Field>
        </div>
        {assessment.docstatus === 0 && (
          <Field label="Customer owner">
            <Select name="respondent" defaultValue={assessment.customer_pending ? "" : assessment.respondent}>
              <option value="">{t("No selection")}</option>
              {data?.members
                ?.filter((m: any) => m.active && m.membership_role !== "Viewer")
                .map((m: any) => (
                  <option key={m.name} value={m.user}>
                    {m.user}
                  </option>
                ))}
            </Select>
          </Field>
        )}
        <Field label="Transfer reason">
          <textarea
            name="reason"
            maxLength={2000}
            placeholder={t("Required when changing an existing consultant, reviewer or customer owner.")}
          />
        </Field>
        <div className="row-actions">
          <Button type="submit" disabled={!data || !!error}>
            {t("Save changes")}
          </Button>
          <Button type="button" variant="secondary" onClick={onClose}>
            {t("Cancel")}
          </Button>
        </div>
      </Form>
    </Modal>
  );
}
export default function AssessmentPage({ scopeOnly = false }: { scopeOnly?: boolean }) {
  const { session } = useSession(),
    { t } = useLanguage();
  const { name } = useParams(),
    { data, error, mutate } = useData<Assessment>("assessment", { name });
  if (error)
    return (
      <>
        <Link className="back-link" to={session.home + "/assessments"}>
          {t("Back to assessments")}
        </Link>
        <ErrorNotice error={error} />
      </>
    );
  if (!data) return <Loading />;
  if (data.docstatus === 0 && data.profile_required)
    return (
      <>
        <Link className="back-link" to={session.home + "/assessments"}>
          <ArrowLeft size={15} />
          {t("Back to assessments")}
        </Link>
        <OrganizationProfile entity={data.entity} requiredForAssessment onDone={() => void mutate()} />
        <ProfileExtras entity={data.entity} />
      </>
    );
  const needsScope = data.scope && (!data.scope.confirmed || data.scope.acknowledgement_required);
  if (needsScope && !scopeOnly)
    return <Navigate to={session.home + "/assessments/" + data.name + "/scope"} replace />;
  if (!needsScope && scopeOnly) return <Navigate to={session.home + "/assessments/" + data.name} replace />;
  if (needsScope)
    return (
      <AuditScope
        key={data.modified}
        doc={data}
        correction={!!data.scope?.confirmed && !!session.is_admin}
        onDone={() => void mutate()}
      />
    );
  return <AssessmentEditor key={data.name} initial={data} mutate={mutate} />;
}
function AssessmentEditor({ initial, mutate }: { initial: Assessment; mutate: () => Promise<any> }) {
  const assessmentTypes = useAssessmentTypes();
  const navigate = useNavigate(),
    { session } = useSession(),
    { t, lang } = useLanguage();
  const [doc, setDoc] = useState<Assessment>(initial),
    [questions, setQuestions] = useState<Question[]>(initial.questions || []),
    [section, setSection] = useState(0);
  const [revision, setRevision] = useState(0),
    [savedRevision, setSavedRevision] = useState(0),
    [saving, setSaving] = useState(false),
    [saveError, setSaveError] = useState<any>();
  const [reviewAction, setReviewAction] = useState(""),
    [assign, setAssign] = useState(false),
    [submitting, setSubmitting] = useState(false);
  const version = useRef(initial.modified),
    inflight = useRef<Promise<void> | null>(null),
    current = useRef<Question[]>(initial.questions || []),
    rev = useRef(0);
  const focusRoot = useRef<HTMLDivElement>(null);
  const [focusSections, setFocusSections] = useState(true),
    [focusProgress, setFocusProgress] = useState(true);
  const focus = useAssessmentFocus(
    focusRoot,
    session.kind === "Customer" && !!doc.editable,
    session.user || "",
    doc.name,
  );
  const [correctScope, setCorrectScope] = useState(false);
  const removeEvidence = useMutation("delete_evidence");
  const save = useMutation("save_assessment"),
    submit = useMutation("submit_assessment"),
    review = useMutation("transition");
  useEffect(() => {
    const guard = (e: BeforeUnloadEvent) => {
      if (revision !== savedRevision) {
        e.preventDefault();
        e.returnValue = "";
      }
    };
    window.addEventListener("beforeunload", guard);
    return () => window.removeEventListener("beforeunload", guard);
  }, [revision, savedRevision]);
  const saveNow = useCallback(async () => {
    if (inflight.current) await inflight.current;
    if (!doc?.editable || rev.current === savedRevision) return;
    const r = rev.current,
      answers = Object.fromEntries(
        current.current.map((q) => [
          q.question_code,
          {
            selected_option: q.selected_option || "",
            ...(q.allow_comment === 1 ? { comment: q.comment || "" } : {}),
            ...(q.allow_attachment === 1 ? { evidence: q.evidence || "" } : {}),
          },
        ]),
      );
    setSaving(true);
    setSaveError(null);
    const promise = (async () => {
      try {
        const result: Assessment = await save.execute({
          name: doc.name,
          answers,
          modified: version.current,
          language: lang,
        });
        version.current = result.modified;
        setDoc(result);
        setSavedRevision(r);
        await mutate();
        // Automatic issue-register answers are server-authoritative.
        if (rev.current === r) {
          setQuestions(result.questions || []);
          current.current = result.questions || [];
        }
      } catch (err) {
        setSaveError(err);
        throw err;
      } finally {
        setSaving(false);
        inflight.current = null;
      }
    })();
    inflight.current = promise;
    return promise;
  }, [doc.editable, doc.name, savedRevision, save, lang, mutate]);
  useEffect(() => {
    if (revision === savedRevision || saving || saveError || !doc?.editable) return;
    const timer = setTimeout(() => {
      void saveNow().catch(() => {});
    }, 900);
    return () => clearTimeout(timer);
  }, [revision, savedRevision, saving, doc?.editable, saveError, saveNow]);
  useEffect(() => {
    const guard = (event: MouseEvent) => {
      if (
        rev.current === savedRevision ||
        event.button !== 0 ||
        event.metaKey ||
        event.ctrlKey ||
        event.shiftKey ||
        event.altKey
      )
        return;
      const link = (event.target as Element).closest("a[href]") as HTMLAnchorElement | null;
      if (!link || link.target || link.origin !== location.origin || !link.pathname.startsWith("/grc/"))
        return;
      event.preventDefault();
      event.stopPropagation();
      void saveNow()
        .then(() => navigate(link.pathname + link.search + link.hash))
        .catch(() => {});
    };
    document.addEventListener("click", guard, true);
    return () => document.removeEventListener("click", guard, true);
  }, [savedRevision, saveNow, navigate]);
  function change(code: string, patch: Partial<Question>) {
    const next = current.current.map((q) => (q.question_code === code ? { ...q, ...patch } : q));
    current.current = next;
    setQuestions(next);
    rev.current += 1;
    setRevision(rev.current);
    setSaveError(null);
  }
  async function attach(q: Question, file?: File) {
    if (!file || !doc) return;
    setSaveError(null);
    try {
      const result = await upload(doc.name, file);
      change(q.question_code, { evidence: result.file_url });
    } catch (err) {
      setSaveError(err);
    }
  }
  const meta = new Map((doc.sections || []).map((s) => [s.code, s]));
  const sections = Array.from(
    new Map(
      questions.map((q) => {
        const m = meta.get(q.section_code);
        return [
          q.section_code,
          {
            code: q.section_code,
            title:
              lang === "ar"
                ? m?.title_ar || q.section_title_ar || m?.title || q.section_title
                : m?.title || q.section_title,
            reference: lang === "ar" ? m?.reference_ar || m?.reference || "" : m?.reference || "",
          },
        ];
      }),
    ).values(),
  );
  const selected = sections[Math.min(section, sections.length - 1)];
  const answered = questions.filter((q) => q.selected_option).length,
    progress = Math.round((answered / Math.max(1, questions.length)) * 100);
  const levels: Record<string, string> = { A: "Ad hoc", B: "Foundational", C: "Established", D: "Leading" },
    points: Record<string, number> = {
      A: Number(doc.scoring?.points?.A ?? 25),
      B: Number(doc.scoring?.points?.B ?? 50),
      C: Number(doc.scoring?.points?.C ?? 75),
      D: Number(doc.scoring?.points?.D ?? 100),
    },
    lettersAr: Record<string, string> = { A: "أ", B: "ب", C: "ج", D: "د" };
  const complete = questions.length > 0 && answered === questions.length;
  const customer = session.kind === "Customer";
  const scoreTiming = doc.customer_score_timing || "After all answers";
  const showScores =
    !customer ||
    scoreTiming === "During assessment" ||
    (scoreTiming === "After submission" ? doc.docstatus === 1 : complete);
  const overview = doc.customer_sections_visibility || "Always expanded";
  const showOverview = !customer || overview !== "Hidden";
  const overviewOpen =
    !customer || overview === "Always expanded" || (overview === "Collapsed until complete" && complete);
  const live =
    doc.overall_maturity_visibility === "After assessment completion" &&
    complete &&
    showScores &&
    doc.editable &&
    doc.scoring
      ? liveOverall(questions, doc.scoring)
      : null;
  const liveBand = live?.band,
    liveBandLabel = liveBand
      ? lang === "ar"
        ? liveBand.level_name_ar || t(liveBand.level_name)
        : t(liveBand.level_name)
      : "";
  const livePct = live ? (Number.isInteger(live.pct) ? String(live.pct) : live.pct.toFixed(1)) : "";
  const showLetter = (letter: string) => (lang === "ar" ? lettersAr[letter] || letter : letter);
  const missing = questions.filter((q) => !q.selected_option).map((q) => q.question_code);
  const pendingQuestion = useRef<string | null>(null);
  function focusQuestion(code: string) {
    const card = document.getElementById("question-" + code);
    if (!card) return;
    card.scrollIntoView({ block: "center", behavior: "smooth" });
    (
      card.querySelector<HTMLElement>(
        "input:not(:disabled), select:not(:disabled), textarea:not(:disabled)",
      ) || card
    ).focus({ preventScroll: true });
  }
  const stepped = useRef(false);
  useEffect(() => {
    if (pendingQuestion.current) {
      const code = pendingQuestion.current;
      pendingQuestion.current = null;
      stepped.current = true;
      requestAnimationFrame(() => focusQuestion(code));
      return;
    }
    if (!stepped.current) {
      stepped.current = true;
      return;
    }
    if (focusRoot.current?.classList.contains("assessment-focus-active")) {
      const container = focusRoot.current.querySelector<HTMLElement>(".assessment-questionnaire-content"),
        sectionNode = focusRoot.current.querySelector<HTMLElement>(".iam-section"),
        question = focusRoot.current.querySelector<HTMLElement>(".question-heading h3");
      if (container) {
        container.scrollTop = 0;
        const bounds = container.getBoundingClientRect();
        const top =
          question && sectionNode && question.getBoundingClientRect().top >= bounds.bottom
            ? sectionNode.getBoundingClientRect().top - bounds.top
            : 0;
        container.scrollTo({ top, behavior: "smooth" });
      }
    } else
      focusRoot.current
        ?.querySelector(".iam-section")
        ?.scrollIntoView({ block: "start", behavior: "smooth" });
  }, [section, focusRoot]);
  const text = (q: Question, key: string) =>
    String((lang === "ar" ? q[(key + "_ar") as keyof Question] : null) || q[key as keyof Question] || "");
  const reviewLabels: Record<string, string> = {
    start_review: "Begin review",
    clarify: "Request clarification",
    approve: "Approve assessment",
    release: "Release report",
  };
  const nextStep =
    doc.current === false
      ? "This is an earlier assessment revision. It is read-only. Return to Assessments to open the current revision."
      : doc.released
        ? "The official report has been released. Use the Report panel for the download and email actions available to your account."
        : doc.editable
          ? customer
            ? doc.clarification
              ? "Update the answers requested in the clarification, then submit again for review."
              : complete
                ? "All shown questions are answered. Review your choices, then choose Submit for review."
                : "Answer every shown question. Use N/A where offered. Changes save automatically; Save and exit lets you continue later."
            : "You are preparing a draft for the customer. Confirm the customer owner and team, then let the customer complete and submit the assessment."
          : doc.docstatus === 0
            ? "This draft is read-only for your account. The assigned customer completes and submits it before review."
            : !customer && doc.state === "Clarification Required"
              ? "Waiting for the customer to respond to the clarification and resubmit. Review can continue after the updated assessment is submitted."
              : doc.review_actions.includes("release")
                ? "The assessment is approved. Release report publishes the official PDF to authorized customer users."
                : doc.review_actions.includes("approve")
                  ? "Review the submitted answers. Request clarification if information is missing, or approve the assessment when the review is complete."
                  : doc.review_actions.includes("start_review")
                    ? "The customer has submitted this assessment. Choose Begin review to start the assigned review."
                    : customer
                      ? doc.state === "Approved"
                        ? "Your assessment is approved. The reviewer will release the official report. Use the Report panel for any preliminary PDF currently available."
                        : "Your answers are submitted and locked during review. No action is needed unless the reviewer requests clarification. Use the Report panel for available results and PDFs."
                      : doc.can_assign
                        ? "Use Assign team to confirm the customer owner and assigned reviewer. Review actions appear for the authorized reviewer after the customer submits."
                        : "This assessment is read-only for your account. Review actions are available only to the assigned authorized reviewer. Ask your department manager if the review assignment needs updating.";
  function goToQuestion(code: string) {
    const question = questions.find((q) => q.question_code === code);
    if (!question) return;
    const index = sections.findIndex((s) => s.code === question.section_code);
    if (index < 0) return;
    if (index === section) requestAnimationFrame(() => focusQuestion(code));
    else {
      pendingQuestion.current = code;
      setSection(index);
    }
  }
  function goToUnanswered() {
    const question = questions.find((q) => !q.selected_option);
    if (question) goToQuestion(question.question_code);
  }
  async function saveAndExit() {
    try {
      await saveNow();
      navigate(session.home + "/assessments");
    } catch {
      /* Stay here so unsaved work can be retried. */
    }
  }
  async function doSubmit() {
    setSubmitting(true);
    try {
      await saveNow();
      const result = await submit.execute({ name: doc!.name });
      setDoc(result);
      setQuestions(result.questions);
      await mutate();
    } catch (err) {
      setSaveError(err);
    } finally {
      setSubmitting(false);
    }
  }
  return (
    <div className={"assessment-editor" + (focus.active ? " is-focus" : "")}>
      <Link className="back-link" to={session.home + "/assessments"}>
        <ArrowLeft size={15} />
        {t("Assessments")}
      </Link>
      <PageTitle
        eyebrow={doc.name}
        title={
          doc.assessment_type === "GRC"
            ? "GRC Maturity Assessment"
            : doc.assessment_type === "Internal Audit" || !doc.assessment_type
              ? "Internal Audit Maturity Assessment"
              : lang === "ar"
                ? "تقييم نضج " + assessmentTypes.label(doc.assessment_type)
                : assessmentTypes.label(doc.assessment_type) + " Maturity Assessment"
        }
        description={doc.entity}
      >
        <Status value={doc.state} />
        {doc.can_assign && (
          <Button variant="secondary" onClick={() => setAssign(true)}>
            {t("Assign team")}
          </Button>
        )}
      </PageTitle>
      <section className="panel padded assessment-next-step" aria-label={t("Your next step")}>
        <strong>{t("Your next step")}</strong>
        <p>{t(nextStep)}</p>
        {doc.editable && missing.length > 0 && (
          <p>
            {t("Questions still to answer")}: {missing.length}{" "}
            <Button type="button" variant="ghost" onClick={goToUnanswered}>
              {t("Go to first unanswered question")}
            </Button>
          </p>
        )}
      </section>
      {doc.clarification && (
        <div className="notice warning">
          <Clock3 size={19} />
          <div>
            <strong>{t("Clarification Required")}</strong>
            <p>{doc.clarification}</p>
          </div>
        </div>
      )}
      {doc.scope && (
        <>
          <ScopeSummary scope={doc.scope} />
          {(doc.scope.can_correct || (doc.scope.can_change && customer && doc.scope_editable)) && (
            <Button
              variant="secondary"
              onClick={async () => {
                try {
                  await saveNow();
                  setCorrectScope(true);
                } catch {
                  /* Existing error notice explains the failed save. */
                }
              }}
            >
              {t(doc.scope.can_change && customer ? "Change sections" : "Correct assessment scope")}
            </Button>
          )}
        </>
      )}
      <MaturityPanel doc={doc} questions={questions} />
      {!doc.results_visible && doc.docstatus === 1 && (
        <div className="notice">
          <ShieldCheck size={19} />
          {t("Results are available after report release.")}
        </div>
      )}
      {doc.customer_pending && (
        <p className="notice">
          {t("Invite a customer administrator and assign a customer owner before submission.")}
        </p>
      )}
      <ReportDelivery doc={doc} />
      {doc.review_actions.length > 0 && (
        <section className="review-actions panel">
          <div>
            <span className="eyebrow">{t("Review assessment")}</span>
            <p>
              {t(
                "Submitted answers stay locked. Request clarification to let the customer make a correction.",
              )}
            </p>
          </div>
          <div>
            {doc.review_actions.map((a) => (
              <Button
                key={a}
                variant={a === "clarify" ? "secondary" : "primary"}
                onClick={() => setReviewAction(a)}
              >
                {t(reviewLabels[a])}
              </Button>
            ))}
          </div>
        </section>
      )}
      <div
        ref={focusRoot}
        className={"iam-questionnaire" + (focus.active ? " assessment-focus-active" : "")}
        onClickCapture={focus.onClickCapture}
        onKeyDownCapture={focus.onKeyDownCapture}
      >
        {focus.eligible && (
          <div className="assessment-focus-toolbar">
            <div>
              <strong>{t(focus.active ? "Full-screen assessment" : "Assessment view")}</strong>
              <span>
                {doc.entity} · {t("Section")} {section + 1} {t("of")} {sections.length}
              </span>
            </div>
            <div className="assessment-focus-actions">
              {focus.active && (
                <>
                  {showOverview && (
                    <Button
                      type="button"
                      variant="secondary"
                      aria-expanded={focusSections}
                      aria-controls="assessment-section-overview"
                      onClick={() => setFocusSections((value) => !value)}
                    >
                      {t(focusSections ? "Hide section overview" : "Show section overview")}
                    </Button>
                  )}
                  <Button
                    type="button"
                    variant="secondary"
                    aria-expanded={focusProgress}
                    aria-controls="assessment-progress-details"
                    onClick={() => setFocusProgress((value) => !value)}
                  >
                    {t(focusProgress ? "Hide progress" : "Show progress")}
                  </Button>
                </>
              )}
              <Button
                data-focus-toggle
                type="button"
                variant="secondary"
                onClick={focus.active ? focus.normal : focus.enter}
              >
                {focus.active ? <Minimize2 size={17} /> : <Maximize2 size={17} />}{" "}
                {t(focus.active ? "Normal view" : "Full screen")}
              </Button>
            </div>
          </div>
        )}
        <div
          className="assessment-questionnaire-content"
          role={focus.active ? "region" : undefined}
          aria-label={focus.active ? t("Questions") : undefined}
          tabIndex={focus.active ? 0 : undefined}
        >
          {focus.active && <p className="notice">{t(nextStep)}</p>}
          {focus.active && doc.clarification && <p className="notice warning">{doc.clarification}</p>}
          {showOverview && (!focus.active || focusSections) && (
            <details
              id="assessment-section-overview"
              className={
                "iam-section-overview" + (overview === "Always expanded" ? " tabs-only" : " panel padded")
              }
              open={overviewOpen || undefined}
            >
              <summary>{t("Section overview")}</summary>
              <div className="iam-stepper" role="list" aria-label={t("Sections")}>
                {sections.map((s, i) => {
                  const qs = questions.filter((q) => q.section_code === s.code),
                    unanswered = qs.filter((q) => !q.selected_option),
                    complete = qs.length > 0 && !unanswered.length;
                  return (
                    <div
                      key={s.code}
                      role="listitem"
                      className={"iam-step-group" + (unanswered.length ? " has-missing" : "")}
                    >
                      <button
                        type="button"
                        className={"iam-step" + (complete ? " done" : "")}
                        aria-current={i === section ? "step" : undefined}
                        onClick={() => setSection(i)}
                      >
                        <span className="n">
                          {t("Section")} {i + 1}
                        </span>
                        <span className="t">{s.title}</span>
                        {unanswered.length > 0 && (
                          <span className="iam-missing-count">
                            {unanswered.length} {lang === "ar" ? "غير مُجاب" : "unanswered"}
                          </span>
                        )}
                      </button>
                      {unanswered.length > 0 && (
                        <div
                          className="iam-missing-links"
                          aria-label={lang === "ar" ? "الأسئلة غير المجابة" : "Unanswered questions"}
                        >
                          {unanswered.map((q) => (
                            <button
                              type="button"
                              key={q.question_code}
                              onClick={() => goToQuestion(q.question_code)}
                              aria-label={`${lang === "ar" ? "انتقل إلى السؤال غير المجاب" : "Go to unanswered question"} ${q.question_code}`}
                            >
                              {q.question_code}
                            </button>
                          ))}
                        </div>
                      )}
                    </div>
                  );
                })}
              </div>
            </details>
          )}
          {!showOverview && missing.length > 0 && (
            <section
              className="iam-missing-summary"
              aria-label={lang === "ar" ? "الأسئلة غير المجابة" : "Unanswered questions"}
            >
              <strong>
                {t("Questions still to answer")}: {missing.length}
              </strong>
              {sections.map((s) => {
                const unanswered = questions.filter((q) => q.section_code === s.code && !q.selected_option);
                return (
                  unanswered.length > 0 && (
                    <div key={s.code}>
                      <span>
                        {s.title} · {unanswered.length} {t("Unanswered")}
                      </span>
                      <div className="iam-missing-links">
                        {unanswered.map((q) => (
                          <button
                            type="button"
                            key={q.question_code}
                            onClick={() => goToQuestion(q.question_code)}
                            aria-label={`${lang === "ar" ? "انتقل إلى السؤال غير المجاب" : "Go to unanswered question"} ${q.question_code}`}
                          >
                            {q.question_code}
                          </button>
                        ))}
                      </div>
                    </div>
                  )
                );
              })}
            </section>
          )}
          <div
            id="assessment-progress-details"
            className="iam-assessment-progress"
            hidden={focus.active && !focusProgress}
          >
            <div className="iam-progress-row">
              <div className="assessment-progress">
                <strong>{answered}</strong> {t("of")} {questions.length} {t("answered")}
                <span className="iam-count-ratio">
                  {" "}
                  {answered}/{questions.length}
                </span>
                <span className="muted">
                  {" "}
                  · {questions.length - answered} {t("pending")}
                </span>
              </div>
              {live && (
                <p className="iam-live-score" aria-live="polite">
                  <span className="iam-live-label">{t("Current score")}</span>
                  <strong className="iam-live-pct">
                    {livePct}
                    <span>%</span>
                  </strong>
                  {liveBandLabel && (
                    <span className="iam-live-band" style={{ color: liveBand?.color || undefined }}>
                      {liveBandLabel}
                    </span>
                  )}
                </p>
              )}
            </div>
            <div
              className="progress-track"
              role="progressbar"
              aria-label={t("Assessment progress")}
              aria-valuemin={0}
              aria-valuemax={questions.length}
              aria-valuenow={answered}
            >
              <span style={{ width: progress + "%" }} />
            </div>
          </div>
          <section className="panel iam-section">
            <div className="iam-section-head">
              <div>
                <p className="iam-kicker">
                  {t("Section")} {section + 1} {t("of")} {sections.length}
                </p>
                <h2>{selected?.title}</h2>
                {selected?.reference && (
                  <p className="iam-ref">
                    {t("Reference")}: {selected.reference}
                  </p>
                )}
              </div>
              <span className={"save-state " + (saveError && revision !== savedRevision ? "error" : "")}>
                {saving ? <LoaderCircle size={15} className="spin" /> : <Check size={15} />}{" "}
                {t(
                  saveError && revision !== savedRevision
                    ? "Save failed"
                    : saving
                      ? "Saving…"
                      : revision === savedRevision
                        ? "Saved"
                        : "Saving…",
                )}
              </span>
            </div>
            <ErrorNotice error={saveError} />
            {saveError && doc.editable && revision !== savedRevision && (
              <p className="notice warning">
                {t("Your latest changes have not been saved. Retry saving before leaving this page.")}{" "}
                <Button
                  type="button"
                  variant="secondary"
                  loading={saving}
                  onClick={() => void saveNow().catch(() => {})}
                >
                  {t("Retry save")}
                </Button>
              </p>
            )}
            {questions
              .filter((q) => q.section_code === selected?.code)
              .map((q) => {
                const allowComment = q.allow_comment === 1;
                const allowAttachment = q.allow_attachment === 1;
                const multi = (q.selection_mode || "Single") === "Multi";
                const chosen = selectedLetters(q.selected_option);
                const toggle = (letter: string) => {
                  if (!multi) {
                    change(q.question_code, { selected_option: letter });
                    return;
                  }
                  if (letter === "N/A") {
                    change(q.question_code, { selected_option: chosen.includes("N/A") ? "" : "N/A" });
                    return;
                  }
                  const next = chosen.includes(letter)
                    ? chosen.filter((x) => x !== letter && x !== "N/A")
                    : [...chosen.filter((x) => x !== "N/A"), letter];
                  change(q.question_code, { selected_option: encodeSelection(next) });
                };
                return (
                  <fieldset
                    className={"question-card" + (!q.selected_option ? " is-unanswered" : "")}
                    id={"question-" + q.question_code}
                    tabIndex={-1}
                    key={q.question_code}
                    disabled={!doc.editable}
                  >
                    <div className="question-heading">
                      <span className="question-code">{q.question_code}</span>
                      <h3>{text(q, "question_text")}</h3>
                      {!q.selected_option && <span className="question-unanswered">{t("Unanswered")}</span>}
                    </div>
                    {q.topic_title && (
                      <p className="question-guidance muted">
                        {lang === "ar" ? q.topic_title_ar || q.topic_title : q.topic_title}
                      </p>
                    )}
                    {text(q, "guidance") && <p className="question-guidance">{text(q, "guidance")}</p>}
                    {multi && <p className="question-guidance muted">{t("Select all that apply")}</p>}
                    {q.locked && <div className="notice">{lang === "ar" ? q.auto_note_ar : q.auto_note}</div>}
                    <div className="iam-opts">
                      {["A", "B", "C", "D", ...(q.allow_na ? ["N/A"] : [])].map((letter) => {
                        const isChosen = chosen.includes(letter);
                        return (
                          <label key={letter} className={"answer-option" + (isChosen ? " chosen" : "")}>
                            <input
                              type={multi ? "checkbox" : "radio"}
                              name={q.question_code + (multi ? `-${letter}` : "")}
                              value={letter}
                              checked={isChosen}
                              disabled={!doc.editable || q.locked}
                              onChange={() => toggle(letter)}
                            />
                            <span className="iam-opt-top">
                              <span>
                                {letter === "N/A"
                                  ? t("Not applicable")
                                  : assessmentTypes.behaviour(doc.assessment_type) === "GRC"
                                    ? showLetter(letter)
                                    : `${showLetter(letter)} · ${t(levels[letter])}`}
                              </span>
                              {letter !== "N/A" && <span className="pts">{points[letter]}</span>}
                            </span>
                            <span className="iam-opt-text">
                              {letter === "N/A"
                                ? t("Excluded from the score.")
                                : text(q, "option_" + letter.toLowerCase())}
                            </span>
                          </label>
                        );
                      })}
                    </div>
                    {allowComment && (
                      <details className="iam-comment" open>
                        <summary>{t("Comment (optional)")}</summary>
                        <textarea
                          rows={2}
                          maxLength={5000}
                          value={q.comment || ""}
                          disabled={!doc.editable}
                          onChange={(e) => change(q.question_code, { comment: e.target.value })}
                        />
                      </details>
                    )}
                    {allowAttachment && (
                      <div className="evidence-row">
                        <span>
                          <Paperclip size={15} />
                          {t("Evidence")}
                        </span>
                        {q.evidence?.startsWith("/private/files/") && (
                          <a href={q.evidence} target="_blank" rel="noreferrer">
                            {t("View evidence")}
                          </a>
                        )}
                        {doc.editable && q.evidence && q.evidence_deletable !== false && (
                          <Button
                            variant="ghost"
                            onClick={async () => {
                              try {
                                await saveNow();
                                await removeEvidence.execute({ name: doc.name, file_url: q.evidence });
                                const updated = await mutate();
                                if (updated?.message) {
                                  const next = updated.message as Assessment;
                                  setDoc(next);
                                  version.current = next.modified;
                                  setQuestions(next.questions || []);
                                  current.current = next.questions || [];
                                }
                              } catch (err) {
                                setSaveError(err);
                              }
                            }}
                          >
                            {t("Delete evidence")}
                          </Button>
                        )}
                        {doc.editable && (
                          <label className="button secondary upload-button">
                            <Paperclip size={15} />
                            {t("Attach evidence")}
                            <input
                              type="file"
                              accept=".pdf,.png,.jpg,.jpeg,.webp,.txt,.csv,.docx,.xlsx,.pptx"
                              onChange={(e) => void attach(q, e.target.files?.[0])}
                            />
                          </label>
                        )}
                      </div>
                    )}
                  </fieldset>
                );
              })}
            {section === sections.length - 1 && missing.length > 0 && (
              <div className="iam-missing" role="status">
                <p>
                  {t("Unanswered")}: {missing.join(", ")}
                </p>
                {doc.editable && (
                  <>
                    <p>
                      {t(
                        "Answer every shown question before submitting. N/A counts as an answer where it is available.",
                      )}
                    </p>
                    <Button type="button" variant="secondary" onClick={goToUnanswered}>
                      {t("Go to first unanswered question")}
                    </Button>
                  </>
                )}
              </div>
            )}
          </section>
        </div>
        <div className="editor-footer">
          <Button variant="secondary" disabled={section === 0} onClick={() => setSection((s) => s - 1)}>
            <ArrowLeft size={16} />
            {t("Previous section")}
          </Button>
          <div>
            {doc.editable && (
              <Button variant="secondary" loading={saving} onClick={() => void saveNow().catch(() => {})}>
                <Save size={16} />
                {t("Save")}
              </Button>
            )}
            {doc.editable && (
              <Button type="button" variant="secondary" loading={saving} onClick={() => void saveAndExit()}>
                {t("Save and exit")}
              </Button>
            )}
            {section < sections.length - 1 ? (
              <Button onClick={() => setSection((s) => s + 1)}>
                {t("Next section")}
                <ArrowRight size={16} />
              </Button>
            ) : (
              doc.editable && (
                <Button
                  loading={submitting}
                  disabled={!complete || saving || !!doc.customer_pending}
                  onClick={() => void doSubmit()}
                >
                  {t("Submit for review")}
                  <ArrowRight size={16} />
                </Button>
              )
            )}
          </div>
        </div>
      </div>
      {correctScope && (
        <Modal
          title={doc.scope?.can_change && customer ? "Change sections" : "Correct assessment scope"}
          onClose={() => setCorrectScope(false)}
        >
          <AuditScope
            doc={doc}
            correction={!(doc.scope?.can_change && customer)}
            onDone={async (result) => {
              setCorrectScope(false);
              setDoc(result);
              setQuestions(result.questions || []);
              current.current = result.questions || [];
              version.current = result.modified;
              await mutate();
            }}
          />
        </Modal>
      )}
      {reviewAction && (
        <Modal title={reviewLabels[reviewAction]} onClose={() => setReviewAction("")}>
          <Form
            onSubmit={async (values) => {
              const result: Assessment = await review.execute({
                name: doc.name,
                action: reviewAction,
                ...values,
              });
              setReviewAction("");
              setDoc(result);
              setQuestions(result.questions || []);
              if (result.name !== doc.name) navigate(session.home + "/assessments/" + result.name);
              else await mutate();
            }}
          >
            {reviewAction === "release" ? (
              <p>{t("Report release publishes the approved PDF to authorized customer users.")}</p>
            ) : (
              <Field label="Review comment">
                <textarea
                  name="comment"
                  rows={4}
                  required={reviewAction === "clarify"}
                  placeholder={t("Explain the required clarification or review decision.")}
                />
              </Field>
            )}
            <div className="row-actions">
              <Button type="submit">{t("Confirm")}</Button>
              <Button type="button" variant="secondary" onClick={() => setReviewAction("")}>
                {t("Cancel")}
              </Button>
            </div>
          </Form>
        </Modal>
      )}
      <details className="panel padded">
        <summary>{t(customer ? "Assessment dates" : "Assessment activity")}</summary>
        <ActivityPage assignment={doc.grc_assignment} />
      </details>
      {assign && (
        <AssignTeam
          assessment={doc}
          onClose={() => setAssign(false)}
          onDone={() => {
            void mutate().then((r) => {
              if (r?.message) setDoc(r.message);
            });
          }}
        />
      )}
    </div>
  );
}
