import { useData } from "../api";
import { useLanguage } from "../i18n";
import { ErrorNotice, Loading, Table } from "../components";
export default function EmailDelivery() {
  const { data, error } = useData<any>("email_diagnostics"),
    { t } = useLanguage();
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  const checks = [
    ["Outgoing email account", data.outgoing_accounts > 0],
    ["Default outgoing account", data.default_outgoing_configured],
    ["Email sending enabled", !data.emails_muted && !data.queue_suspended && !data.account_awaiting_password],
    ["Scheduler active", !data.scheduler_inactive],
    ["Workers available", data.workers_present],
  ];
  return (
    <section className="panel padded">
      <h2>{t("Email delivery diagnostics")}</h2>
      <p className="muted">
        {t("Read-only checks. Sent means handed to the mail server, not proof of inbox delivery.")}
      </p>
      <dl>
        {checks.map(([label, ok]) => (
          <div className="score-row" key={String(label)}>
            <dt>{t(String(label))}</dt>
            <dd>{t(ok === null ? "Unknown" : ok ? "Ready" : "Needs attention")}</dd>
          </div>
        ))}
      </dl>
      <p>
        {Object.entries(data.queue_counts)
          .map(([s, n]) => t(s) + ": " + n)
          .join(" · ") || t("No queued emails")}
      </p>
      {data.verification_queue?.length > 0 && (
        <Table headers={["Verification queue status", "Count", "Oldest queued", "Newest queued"]}>
          {data.verification_queue.map((r: any) => (
            <tr key={r.status}>
              <td>{t(r.status)}</td>
              <td>{r.total}</td>
              <td>{r.oldest?.slice(0, 16)}</td>
              <td>{r.newest?.slice(0, 16)}</td>
            </tr>
          ))}
        </Table>
      )}
      <p className="muted">
        {t(
          "Provider processing, spam placement and SPF/DKIM/DMARC require provider delivery records and recipient headers. Queue status alone cannot verify them.",
        )}
      </p>
      {data.recent_failures.length > 0 && (
        <Table headers={["Queue record", "Date", "Diagnostic"]}>
          {data.recent_failures.map((r: any) => (
            <tr key={r.name}>
              <td>{r.name}</td>
              <td>{r.modified?.slice(0, 16)}</td>
              <td>{t(r.category)}</td>
            </tr>
          ))}
        </Table>
      )}
      <p className="muted">
        {t(
          "Platform operators can inspect Email Queue in Desk for the full error. These checks do not send or retry emails.",
        )}
      </p>
    </section>
  );
}
