import PortalProvider from "../PortalProvider";
import { useData } from "../api";
import { useLanguage } from "../i18n";
import { Loading } from "../components";
import { PublicSite } from "./Public";
import type { SiteContent } from "../siteContent";

export default function PublicPreview({ name }: { name: string }) {
  return (
    <PortalProvider>
      <PreviewContent name={name} />
    </PortalProvider>
  );
}
function PreviewContent({ name }: { name: string }) {
  const { data, error } = useData<{ content: SiteContent }>("site_content_revision", { name }),
    { lang } = useLanguage();
  if (error)
    return (
      <div className="standalone" role="alert">
        {lang === "ar"
          ? "تعذرت معاينة النسخة أو لا تملك صلاحية الوصول."
          : "Cannot preview this revision or you do not have access."}
      </div>
    );
  if (!data) return <Loading />;
  return <PublicSite previewContent={data.content} previewName={name} />;
}
