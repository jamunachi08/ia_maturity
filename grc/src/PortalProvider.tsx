import type { ReactNode } from "react";
import { FrappeProvider } from "frappe-react-sdk";

// The SDK and its transport dependencies are needed by portal/private APIs,
// not by public copy or the password/email-code sign-in form.
export default function PortalProvider({ children }: { children: ReactNode }) {
  return (
    <FrappeProvider enableSocket={false} swrConfig={{ shouldRetryOnError: false }}>
      {children}
    </FrappeProvider>
  );
}
