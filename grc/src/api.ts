import { useFrappeGetCall, useFrappePostCall } from "frappe-react-sdk";
const ROOT = "ia_maturity.grc.api.";
export function useData<T>(method: string, args?: Record<string, unknown>, refresh = 0) {
  const result = useFrappeGetCall<{ message: T }>(
    method.includes(".") ? method : ROOT + method,
    args,
    undefined,
    { revalidateOnFocus: true, refreshInterval: refresh, shouldRetryOnError: false },
  );
  return { ...result, data: result.data?.message };
}
export function useMutation(method: string) {
  const result = useFrappePostCall<{ message: any }>(method.includes(".") ? method : ROOT + method);
  return {
    ...result,
    execute: async (args: Record<string, unknown>) => {
      const response = (await result.call(args)).message;
      if (response?.pending_approval)
        window.dispatchEvent(new CustomEvent("grc-approval-queued", { detail: response.name }));
      return response;
    },
  };
}
export { errorText, rawPost, upload } from "./http";
