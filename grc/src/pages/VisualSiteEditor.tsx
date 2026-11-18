import Select from "../Select";
import { useEffect, useRef, useState } from "react";
import { createPortal } from "react-dom";
import { PublicSite } from "./Public";
import { Modal, Button } from "../components";
import { useLanguage } from "../i18n";
import catalogue from "../site-content-defaults.json";
import type { SiteContent } from "../siteContent";
import { getLayout, withLayout, type SiteCard } from "../siteLayout";
import "./visual-site-editor.css";
const pages = [
  "home",
  "services",
  "catalogue",
  "frameworks",
  "about",
  "resources",
  "faq",
  "contact",
  "privacy",
  "terms",
];
export default function VisualSiteEditor({
  content,
  onChange,
}: {
  content: SiteContent;
  onChange: (value: SiteContent) => void;
}) {
  const { lang } = useLanguage(),
    ar = lang === "ar",
    t = (en: string, arabic: string) => (ar ? arabic : en);
  const frame = useRef<HTMLIFrameElement>(null),
    [root, setRoot] = useState<HTMLElement | null>(null),
    [page, setPage] = useState("home"),
    [full, setFull] = useState(false);
  const [editing, setEditing] = useState<string>(),
    [pair, setPair] = useState({ en: "", ar: "" }),
    [selection, setSelection] = useState<{ section: string; card?: string }>();
  const creationSnapshot = useRef<SiteContent | null>(null);
  const closeEditor = () => {
    if (creationSnapshot.current) {
      onChange(creationSnapshot.current);
      creationSnapshot.current = null;
    }
    setEditing(undefined);
  };
  const current = useRef(content);
  useEffect(() => {
    current.current = content;
  }, [content]);
  const layout = getLayout(content);
  const container = selection?.section || (page === "home" ? "home.journey" : page + ".main");
  const init = () => {
    const doc = frame.current?.contentDocument;
    if (!doc || doc.getElementById("visual-root")) return;
    doc.head.replaceChildren();
    for (const style of document.querySelectorAll('link[rel="stylesheet"],style'))
      doc.head.append(style.cloneNode(true));
    const css = doc.createElement("style");
    css.textContent =
      "body{margin:0!important;background:white}.visual-hover{outline:2px dashed #1485b0!important;outline-offset:3px;cursor:text!important}";
    doc.head.append(css);
    doc.body.innerHTML = '<div id="visual-root"></div>';
    setRoot(doc.getElementById("visual-root"));
  };
  useEffect(() => {
    init();
  }, []);
  useEffect(() => {
    const doc = frame.current?.contentDocument;
    if (root && doc) {
      doc.documentElement.setAttribute("lang", lang);
      doc.documentElement.setAttribute("dir", ar ? "rtl" : "ltr");
    }
  }, [root, lang, ar]);
  useEffect(() => {
    if (!root) return;
    const doc = root.ownerDocument;
    let highlighted: Element | null = null;
    const click = (event: MouseEvent) => {
      const target = event.target as HTMLElement;
      if (!target.closest(".public-site")) return;
      event.preventDefault();
      event.stopPropagation();
      const section = target.closest<HTMLElement>("[data-site-section]"),
        card = target.closest<HTMLElement>("[data-site-card]");
      setSelection(
        section ? { section: section.dataset.siteSection!, card: card?.dataset.siteCard } : undefined,
      );
      const values = new Map<string, string>();
      for (const [key, defaults] of Object.entries(catalogue))
        values.set((current.current[key]?.[lang] ?? defaults[lang]).trim(), key);
      for (const [key, value] of Object.entries(current.current))
        if (key !== "__layout" && !key.startsWith("custom.")) values.set(value[lang].trim(), key);
      const model = getLayout(current.current),
        sectionId = section?.dataset.siteSection,
        cardId = card?.dataset.siteCard;
      const ownSection = Object.values(model.sections)
        .flat()
        .find((s) => s.id === sectionId);
      const ownCard = [
        ...Object.values(model.cards).flat(),
        ...Object.values(model.sections)
          .flat()
          .flatMap((s) => s.cards),
      ].find((c) => c.id === cardId);
      for (const item of [ownSection, ownCard])
        if (item)
          for (const field of [item.title, item.body]) {
            const text = current.current[field]?.[lang];
            if (text) values.set(text.trim(), field);
          }
      values.delete("");
      let key: string | undefined = target.closest<HTMLElement>("[data-site-key]")?.dataset.siteKey;
      const walker = doc.createTreeWalker(target, NodeFilter.SHOW_TEXT);
      let node: Node | null;
      while (!key && (node = walker.nextNode())) {
        const candidate = values.get(node.textContent?.trim() || "");
        if (!candidate) continue;
        const range = doc.createRange();
        range.selectNodeContents(node);
        if (
          Array.from(range.getClientRects()).some(
            (r) =>
              event.clientX >= r.left &&
              event.clientX <= r.right &&
              event.clientY >= r.top &&
              event.clientY <= r.bottom,
          )
        ) {
          key = candidate;
          break;
        }
      }
      key ||= values.get(target.textContent?.trim() || "");
      if (key) {
        creationSnapshot.current = null;
        const defaults = (catalogue as Record<string, { en: string; ar: string }>)[key];
        setPair(current.current[key] || defaults || { en: "", ar: "" });
        setEditing(key);
      }
    };
    const prevent = (event: Event) => {
      if ((event.target as Element).closest(".public-site")) {
        event.preventDefault();
        event.stopPropagation();
      }
    };
    const hover = (event: MouseEvent) => {
      highlighted?.classList.remove("visual-hover");
      highlighted = (event.target as Element).closest("h1,h2,h3,p,a,span,li,strong,small,label");
      highlighted?.classList.add("visual-hover");
    };
    doc.addEventListener("click", click, true);
    doc.addEventListener("pointerdown", prevent, true);
    doc.addEventListener("submit", prevent, true);
    doc.addEventListener("mouseover", hover);
    return () => {
      doc.removeEventListener("click", click, true);
      doc.removeEventListener("pointerdown", prevent, true);
      doc.removeEventListener("submit", prevent, true);
      doc.removeEventListener("mouseover", hover);
      highlighted?.classList.remove("visual-hover");
    };
  }, [root, lang]);
  const create = (value: SiteContent): [SiteContent, SiteCard] => {
    const id = crypto.randomUUID(),
      title = "custom." + id + ".title",
      body = "custom." + id + ".body";
    return [
      {
        ...value,
        [title]: { en: "New title", ar: "عنوان جديد" },
        [body]: { en: "Describe this content.", ar: "اكتب وصف المحتوى." },
      },
      { id, title, body },
    ];
  };
  const addSection = () => {
    creationSnapshot.current = content;
    const [next, item] = create(content),
      updated = getLayout(next);
    updated.sections[page] = [...(updated.sections[page] || []), { ...item, cards: [] }];
    onChange(withLayout(next, updated));
    setSelection({ section: item.id });
    setEditing(item.title);
    setPair(next[item.title]);
  };
  const addCard = () => {
    creationSnapshot.current = content;
    const [next, item] = create(content),
      updated = getLayout(next);
    updated.cards[container] = [...(updated.cards[container] || []), item];
    onChange(withLayout(next, updated));
    setEditing(item.title);
    setPair(next[item.title]);
  };
  const removeCard = () => {
    if (!selection?.card) return;
    const updated = getLayout(content),
      id = selection.card;
    if (/^\d+$/.test(id))
      updated.removedCards[container] = [
        ...new Set([...(updated.removedCards[container] || []), Number(id)]),
      ];
    else {
      for (const key of Object.keys(updated.cards))
        updated.cards[key] = updated.cards[key].filter((c) => c.id !== id);
      for (const sections of Object.values(updated.sections))
        for (const section of sections) section.cards = section.cards.filter((c) => c.id !== id);
    }
    onChange(withLayout(content, updated));
    setSelection({ section: container });
  };
  const canAdd =
    container === "home.journey" ||
    [
      "services.main",
      "catalogue.main",
      "frameworks.main",
      "about.main",
      "resources.main",
      "faq.main",
    ].includes(container) ||
    Object.values(layout.sections)
      .flat()
      .some((s) => s.id === container);
  return (
    <div className={"visual-editor " + (full ? "visual-full" : "")}>
      <div className="visual-toolbar">
        <strong>{t("Click text to edit both languages", "انقر النص لتعديل اللغتين")}</strong>
        <label>
          {t("Page", "الصفحة")}
          <Select
            aria-label={t("Visual page", "صفحة المحرر المرئي")}
            value={page}
            onChange={(e) => {
              setPage(e.target.value);
              setSelection(undefined);
            }}
          >
            {pages.map((p) => (
              <option key={p} value={p}>
                {
                  (
                    {
                      home: t("Home", "الرئيسية"),
                      services: t("Services", "الخدمات"),
                      catalogue: t("Catalogue", "الدليل"),
                      frameworks: t("Frameworks", "الأطر"),
                      about: t("About", "عن المنصة"),
                      resources: t("Resources", "الموارد"),
                      faq: t("FAQ", "الأسئلة الشائعة"),
                      contact: t("Contact", "تواصل معنا"),
                      privacy: t("Privacy", "الخصوصية"),
                      terms: t("Terms", "الشروط"),
                    } as Record<string, string>
                  )[p]
                }
              </option>
            ))}
          </Select>
        </label>
        <Button variant="secondary" onClick={addSection}>
          {t("Add section", "إضافة قسم")}
        </Button>
        <Button variant="secondary" disabled={!canAdd || layout.hidden.includes(container)} onClick={addCard}>
          {t("Add card", "إضافة بطاقة")}
        </Button>
        <Button variant="secondary" disabled={!selection?.card} onClick={removeCard}>
          {t("Remove selected card", "إزالة البطاقة المحددة")}
        </Button>
        <Button
          variant="secondary"
          disabled={!selection}
          onClick={() => {
            if (window.confirm(t("Remove this section from the draft?", "هل تريد إزالة القسم من المسودة؟"))) {
              const next = getLayout(content);
              next.hidden = [...new Set([...next.hidden, container])];
              onChange(withLayout(content, next));
              setSelection(undefined);
            }
          }}
        >
          {t("Remove selected section", "إزالة القسم المحدد")}
        </Button>
        <Button variant="secondary" onClick={() => setFull(!full)}>
          {full ? t("Exit full screen", "إنهاء ملء الشاشة") : t("Full screen", "ملء الشاشة")}
        </Button>
      </div>
      <p className="visual-hint">
        {t(
          "Click text to open English and Arabic together. Click a card or section to select it for removal. New sections are added at the end of the selected page. Save the draft before submitting for approval.",
          "انقر النص لفتح الإنجليزية والعربية معاً. انقر بطاقة أو قسماً لتحديده للإزالة. تُضاف الأقسام الجديدة في نهاية الصفحة المحددة. احفظ المسودة قبل إرسالها للاعتماد.",
        )}
        {selection && <strong> · {selection.section}</strong>}
      </p>
      {layout.hidden.length > 0 && (
        <details className="visual-restore">
          <summary>{t("Restore removed sections", "استعادة الأقسام المحذوفة")}</summary>
          {layout.hidden.map((id) => (
            <button
              key={id}
              onClick={() => {
                const next = getLayout(content);
                next.hidden = next.hidden.filter((s) => s !== id);
                onChange(withLayout(content, next));
              }}
            >
              {id}
            </button>
          ))}
        </details>
      )}
      <iframe
        ref={frame}
        title={t("Visual website editor", "محرر الموقع المرئي")}
        onLoad={init}
        src="about:blank"
      />
      {root &&
        createPortal(
          <PublicSite previewContent={content} pageOverride={page === "home" ? "" : page} />,
          root,
        )}
      {editing && (
        <Modal title={t("Edit text in both languages", "تعديل النص باللغتين")} onClose={closeEditor}>
          <div className="visual-text-fields">
            <label>
              English
              <textarea
                autoFocus
                lang="en"
                dir="ltr"
                rows={6}
                maxLength={12000}
                value={pair.en}
                onChange={(e) => setPair({ ...pair, en: e.target.value })}
              />
            </label>
            <label>
              العربية
              <textarea
                lang="ar"
                dir="rtl"
                rows={6}
                maxLength={12000}
                value={pair.ar}
                onChange={(e) => setPair({ ...pair, ar: e.target.value })}
              />
            </label>
          </div>
          <div className="site-actions">
            <Button
              onClick={() => {
                onChange({ ...content, [editing]: pair });
                creationSnapshot.current = null;
                setEditing(undefined);
              }}
            >
              {t("Apply to draft", "تطبيق على المسودة")}
            </Button>
            <Button variant="secondary" onClick={closeEditor}>
              {t("Cancel", "إلغاء")}
            </Button>
          </div>
        </Modal>
      )}
    </div>
  );
}
