import { useState } from "react";
import Select from "../Select";
import { useData, useMutation } from "../api";
import { useLanguage } from "../i18n";
import { Button, ErrorNotice, Field, Loading, PageTitle } from "../components";
export default function MaturityVisibility() {
  const { data, error, mutate } = useData<{ mode: string; options: string[] }>("maturity_display_settings");
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return (
    <>
      <PageTitle
        title="Assessment display"
        description="Control the Overall Maturity panel for customers and staff."
      />
      <Editor key={data.mode} data={data} done={mutate} />
    </>
  );
}
function Editor({ data, done }: { data: { mode: string; options: string[] }; done: () => Promise<any> }) {
  const { t } = useLanguage();
  const [mode, setMode] = useState(data.mode),
    [error, setError] = useState<any>();
  const save = useMutation("save_maturity_display");
  return (
    <section className="panel padded">
      <form
        className="form settings-form"
        onSubmit={async (e) => {
          e.preventDefault();
          setError(null);
          try {
            await save.execute({ mode, expected_mode: data.mode });
            await done();
          } catch (err) {
            setError(err);
          }
        }}
      >
        <Field label="Overall Maturity panel">
          <Select value={mode} onChange={(e) => setMode(e.target.value)}>
            {data.options.map((v) => (
              <option key={v} value={v}>
                {t(v === "Hidden" ? "Don't show at all" : v)}
              </option>
            ))}
          </Select>
        </Field>
        <p className="muted">
          {t(
            "Hidden removes the entire panel. Completion means every question has an answer, including Not applicable. Completed sections only shows no aggregate score. Existing result access rules still apply.",
          )}
        </p>
        <ErrorNotice error={error} />
        <Button type="submit" loading={save.loading}>
          {t("Save display setting")}
        </Button>
      </form>
    </section>
  );
}
