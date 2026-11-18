import Select from "../Select";
import { useSession } from "../session";
import { useMutation } from "../api";
import { useLanguage } from "../i18n";
import { Button, Field, Form, PageTitle } from "../components";
export default function Preferences() {
  const { session, refresh } = useSession(),
    save = useMutation("save_notification_preferences"),
    { t } = useLanguage();
  return (
    <>
      <PageTitle
        title="Notification preferences"
        description="Optional emails require both organization and individual permission."
      />
      <section className="panel padded">
        <Form
          onSubmit={async (data) => {
            await save.execute({ ...data, email_notifications: 1 });
            refresh();
          }}
        >
          {(
            [
              ["optional_reminders", "Optional reminders"],
              ["optional_status_updates", "Optional status updates"],
            ] as const
          ).map(([key, label]) => (
            <Field key={key} label={label}>
              <Select name={key} defaultValue={session.email_notifications === 0 ? 0 : (session[key] ?? 1)}>
                <option value="1">{t("Enabled")}</option>
                <option value="0">{t("Disabled")}</option>
              </Select>
            </Field>
          ))}
          <p className="notice">
            {t(
              "Verification codes, account security emails, invitations and clarification requests are mandatory and cannot be disabled.",
            )}
          </p>
          <Button type="submit">{t("Save changes")}</Button>
        </Form>
      </section>
    </>
  );
}
