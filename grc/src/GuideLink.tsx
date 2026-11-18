import { Link } from "react-router-dom";
import { BookOpen } from "lucide-react";
import { useLanguage } from "./i18n";
import { useSession } from "./session";
import "./guide.css";

// Keep the header control independent of the full guide content and dialog.
export default function GuideLink() {
  const { lang } = useLanguage(),
    { session } = useSession();
  if (session.workspace_preferences?.show_help === false) return null;
  const base = session.kind === "Auditor" ? "/grc/auditor" : "/grc/customer";
  return (
    <Link className="guide-header-link" to={base + "/guide"}>
      <BookOpen size={16} />
      {lang === "ar" ? "المساعدة والأدلة" : "Help & guides"}
    </Link>
  );
}
