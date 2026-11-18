import AssessmentDisclosure from "../AssessmentDisclosure";
import { useState } from "react";
import { Eye, FileDown, Mail, LockKeyhole } from "lucide-react";
import { Link } from "react-router-dom";
import { useMutation } from "../api";
import { useLanguage } from "../i18n";
import { useSession } from "../session";
import { Button, Field, Form, Modal } from "../components";
import type { Assessment } from "../types";
export default function ReportDelivery({ doc }: { doc: Assessment }) {
  const { t } = useLanguage(),
    { session } = useSession(),
    email = useMutation("email_report");
  const [open, setOpen] = useState(false),
    [sent, setSent] = useState(false);
  const canDownload = !!doc.can_download_report && !!doc.pdf_url;
  const canEmail = !!doc.can_email_report;
  const downloadOff = doc.allow_report_download === 0;
  const emailOff = doc.allow_report_email === 0;
  const unavailable = (disabled: boolean) =>
    disabled
      ? "Disabled by the platform administrator."
      : !doc.released && doc.report_access_timing === "Before Audit" && doc.docstatus === 0
        ? "Submit the assessment before requesting a preliminary PDF."
        : !doc.released && doc.report_access_timing === "Before Audit"
          ? "This action is not available for your account. Contact your organization administrator or department manager."
          : !doc.released
            ? "The assigned reviewer must approve and release the official report first."
            : "This action is not available for your account. Contact your organization administrator or department manager.";
  const note =
    canDownload || canEmail
      ? undefined
      : downloadOff && emailOff
        ? "Report delivery disabled"
        : doc.released || (doc.report_access_timing === "Before Audit" && doc.docstatus === 1)
          ? "Report access unavailable"
          : doc.report_access_timing === "Before Audit"
            ? "Available after assessment submission"
            : "Available after report release";
  let hint =
    "PDF download and report email become available after an authorized reviewer releases the report.";
  if (downloadOff && emailOff) hint = "Report download and email are disabled by the platform administrator.";
  else if (doc.report_access_timing === "Before Audit" && !doc.released)
    hint = doc.report_preliminary
      ? "A preliminary PDF is available before report release. The approved PDF replaces it after release."
      : doc.docstatus === 0
        ? "Report download and email become available after the customer submits the assessment."
        : "This action is not available for your account. Contact your organization administrator or department manager.";
  else if (doc.released)
    hint = "Download the released PDF or email the PDF to the customer’s registered email.";
  return (
    <AssessmentDisclosure title="Report" note={note} className="report-disclosure" open={doc.expand_report}>
      <section className="report-delivery">
        <div>
          <p className="muted">{t(hint)}</p>
        </div>
        <div className="row-actions">
          {doc.can_view_report && (
            <div>
              <Link className="button secondary" to={session.home + "/assessments/" + doc.name + "/report"}>
                <Eye size={17} />
                {t("View report")}
              </Link>
            </div>
          )}
          <div>
            {canDownload ? (
              <a className="button primary" href={doc.pdf_url}>
                <FileDown size={17} />
                {t(doc.report_preliminary ? "Download preliminary PDF" : "Download PDF")}
              </a>
            ) : (
              <Button disabled variant="secondary">
                <LockKeyhole size={17} />
                {t("Download PDF")}
              </Button>
            )}
            {!canDownload && <p className="muted">{t(unavailable(downloadOff))}</p>}
          </div>
          <div>
            <Button variant="secondary" disabled={!canEmail} onClick={() => setOpen(true)}>
              <Mail size={17} />
              {t("Email report")}
            </Button>
            {!canEmail && <p className="muted">{t(unavailable(emailOff))}</p>}
          </div>
        </div>
        {sent && (
          <p role="status" className="notice">
            {t("Report email queued. Delivery depends on the site's outgoing email service.")}
          </p>
        )}
        {open && (
          <Modal title="Email report" onClose={() => setOpen(false)}>
            <Form
              onSubmit={async () => {
                await email.execute({ name: doc.name });
                setSent(true);
                setOpen(false);
              }}
            >
              <Field label="Recipient">
                <input
                  readOnly
                  value={
                    doc.report_recipient ||
                    (session.kind === "Customer" ? session.user : doc.respondent) ||
                    ""
                  }
                  type="email"
                />
              </Field>
              <p>{t("The assessment PDF will be attached and sent to the customer’s registered email.")}</p>
              <div className="row-actions">
                <Button type="submit">{t("Send PDF")}</Button>
                <Button type="button" variant="secondary" onClick={() => setOpen(false)}>
                  {t("Cancel")}
                </Button>
              </div>
            </Form>
          </Modal>
        )}
        {canDownload && (
          <iframe
            title={t("Report preview")}
            src={doc.pdf_url + "&inline=1"}
            style={{ width: "100%", height: "650px", border: 0, gridColumn: "1 / -1" }}
          />
        )}
      </section>
    </AssessmentDisclosure>
  );
}
