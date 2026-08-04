export type PublicWorkAction = "share" | "qr_requested" | "report_requested";

export interface PublicWorkActionEvent {
  action: PublicWorkAction;
  workId: string;
  slug: string;
}

export const PUBLIC_WORK_ACTION_EVENT = "tmi:public-work-action";

export function emitPublicWorkAction(detail: PublicWorkActionEvent): void {
  if (typeof window === "undefined") return;
  window.dispatchEvent(
    new CustomEvent<PublicWorkActionEvent>(PUBLIC_WORK_ACTION_EVENT, { detail }),
  );
}
