import { useState } from "react";
import { useData, useMutation } from "../api";
import { useSession } from "../session";
import { useLanguage } from "../i18n";
import { Button, ErrorNotice, Loading, PageTitle } from "../components";
import { defaultColorRanges, sectionScoreColor, type ColorRange } from "../sectionScoreColor";
export default function ColorRangesPage() {
  const { session } = useSession();
  const { data, error, mutate } = useData<{ ranges: ColorRange[]; revision: string }>("color_ranges");
  if (!session.is_admin && !session.staff_roles?.includes("GRC Manager"))
    return (
      <ErrorNotice
        error={{ message: "Only GRC administrators and GRC managers can manage report colors." }}
      />
    );
  if (error) return <ErrorNotice error={error} />;
  if (!data) return <Loading />;
  return <Editor initial={data} refresh={mutate} />;
}
function Editor({
  initial,
  refresh,
}: {
  initial: { ranges: ColorRange[]; revision: string };
  refresh: () => Promise<any>;
}) {
  const { t } = useLanguage();
  const [revision, setRevision] = useState(initial.revision),
    [ranges, setRanges] = useState<ColorRange[]>(initial.ranges),
    [error, setError] = useState<any>(),
    [saved, setSaved] = useState(false);
  const save = useMutation("save_color_ranges");
  const sorted = [...ranges].sort((a, b) => a.min_score - b.min_score);
  function change(index: number, patch: Partial<ColorRange>) {
    setRanges((rows) => rows.map((row, i) => (i === index ? { ...row, ...patch } : row)));
    setSaved(false);
  }
  function add() {
    const starts = sorted.map((r) => r.min_score);
    let start = 0,
      width = -1;
    for (let i = 0; i < starts.length; i++) {
      const gap = (starts[i + 1] ?? 100) - starts[i];
      if (gap > width) {
        width = gap;
        start = starts[i] + gap / 2;
      }
    }
    setRanges((rows) =>
      [...rows, { min_score: Number(start.toFixed(4)), color: "#0E6B66" }].sort(
        (a, b) => a.min_score - b.min_score,
      ),
    );
    setSaved(false);
  }
  return (
    <>
      <PageTitle
        title="Report color ranges"
        description="Configure section-score colors for the questionnaire, report preview and PDF."
      />
      <section className="panel padded">
        <p>
          {t(
            "Each range includes its starting percentage and ends just before the next range. The last range includes 100%. Start the first range at 0%.",
          )}
        </p>
        <ErrorNotice error={error} />
        <form
          onSubmit={async (e) => {
            e.preventDefault();
            setError(null);
            try {
              const result = await save.execute({ ranges, expected_revision: revision });
              setRevision(result.revision);
              setRanges(result.ranges);
              await refresh();
              setSaved(true);
            } catch (err) {
              setError(err);
            }
          }}
        >
          <div style={{ overflowX: "auto" }}>
            <table>
              <thead>
                <tr>
                  <th>{t("Starting percentage")}</th>
                  <th>{t("Color")}</th>
                  <th>{t("Remove")}</th>
                </tr>
              </thead>
              <tbody>
                {ranges.map((row, i) => (
                  <tr key={i}>
                    <td>
                      <input
                        aria-label={t("Range start") + " " + (i + 1)}
                        type="number"
                        min="0"
                        max="100"
                        step="any"
                        required
                        value={row.min_score}
                        onChange={(e) => change(i, { min_score: Number(e.target.value) })}
                      />
                    </td>
                    <td>
                      <div style={{ display: "flex", gap: 8, alignItems: "center" }}>
                        <input
                          type="color"
                          aria-label={t("Pick color") + " " + (i + 1)}
                          value={/^#[0-9a-f]{6}$/i.test(row.color) ? row.color : "#000000"}
                          onChange={(e) => change(i, { color: e.target.value })}
                          style={{ width: 48, minWidth: 48 }}
                        />
                        <input
                          aria-label={t("Hex color") + " " + (i + 1)}
                          value={row.color}
                          required
                          pattern="#[0-9a-fA-F]{6}"
                          onChange={(e) => change(i, { color: e.target.value })}
                          style={{ minWidth: 100 }}
                        />
                      </div>
                    </td>
                    <td>
                      <Button
                        variant="ghost"
                        aria-label={t("Remove range") + " " + (i + 1)}
                        type="button"
                        disabled={ranges.length === 1}
                        onClick={() => {
                          setRanges((rows) => rows.filter((_, index) => index !== i));
                          setSaved(false);
                        }}
                      >
                        {t("Remove")}
                      </Button>
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
          <div className="row-actions" style={{ marginTop: 20 }}>
            <Button type="button" variant="secondary" onClick={add}>
              {t("Add range")}
            </Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                setRanges(defaultColorRanges.map((r) => ({ ...r })));
                setSaved(false);
              }}
            >
              {t("Restore default ranges")}
            </Button>
            <Button type="submit" loading={save.loading}>
              {t("Save color ranges")}
            </Button>
          </div>
          <div
            style={{ display: "flex", flexWrap: "wrap", gap: 8, marginTop: 20 }}
            aria-label={t("Range preview")}
          >
            {sorted.map((row, i) => (
              <span
                key={i}
                style={{
                  border: "1px solid " + row.color,
                  borderRadius: 999,
                  padding: "5px 12px",
                  color: row.color,
                }}
              >
                {row.min_score === 100
                  ? "100%"
                  : row.min_score + "% – " + (sorted[i + 1] ? "<" + sorted[i + 1].min_score : "100") + "%"}
              </span>
            ))}
          </div>
          <div
            aria-label={t("Score color preview")}
            style={{ display: "flex", gap: 12, flexWrap: "wrap", marginTop: 16 }}
          >
            {[0, 25, 50, 75, 100].map((score) => (
              <span key={score} style={{ color: sectionScoreColor(score, ranges) }}>
                {score}%
              </span>
            ))}
          </div>
          {saved && <p role="status">{t("Color ranges saved.")}</p>}
        </form>
      </section>
    </>
  );
}
