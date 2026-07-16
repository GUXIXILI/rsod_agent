/** Chat attachments are uploaded separately from chat messages. */
import request from "@/utils/request";

/**
 * Upload one chat attachment and receive an opaque attachment ID.
 * The backend owns the MinIO object path and never exposes it to the browser.
 */
export function uploadChatAttachment(formData) {
  return request.post("/chat/attachments", formData, {
    timeout: 180000,
  });
}
