import type { SiteContent } from "../siteContent";
import { getLayout } from "../siteLayout";
export function ExtraCards({
  content,
  container,
  lang,
  journey = false,
  start = 0,
}: {
  content: SiteContent;
  container: string;
  lang: "en" | "ar";
  journey?: boolean;
  start?: number;
}) {
  return (
    <>
      {(getLayout(content).cards[container] || []).map((card, index) =>
        journey ? (
          <li key={card.id} data-site-card={card.id}>
            <span className="step-count">{String(1 + index + start).padStart(2, "0")}</span>
            <h3>{content[card.title]?.[lang]}</h3>
            <p>{content[card.body]?.[lang]}</p>
          </li>
        ) : (
          <article key={card.id} data-site-card={card.id}>
            <h2>{content[card.title]?.[lang]}</h2>
            <p>{content[card.body]?.[lang]}</p>
          </article>
        ),
      )}
    </>
  );
}
export function ExtraSections({
  content,
  page,
  lang,
}: {
  content: SiteContent;
  page: string;
  lang: "en" | "ar";
}) {
  const layout = getLayout(content);
  return (
    <>
      {(layout.sections[page] || [])
        .filter((s) => !layout.hidden.includes(s.id))
        .map((section) => (
          <section className="public-content" key={section.id} data-site-section={section.id}>
            <h2>{content[section.title]?.[lang]}</h2>
            <p className="public-intro">{content[section.body]?.[lang]}</p>
            <div className="public-cards">
              {section.cards.map((card) => (
                <article key={card.id} data-site-card={card.id}>
                  <h2>{content[card.title]?.[lang]}</h2>
                  <p>{content[card.body]?.[lang]}</p>
                </article>
              ))}
              <ExtraCards content={content} container={section.id} lang={lang} />
            </div>
          </section>
        ))}
    </>
  );
}
