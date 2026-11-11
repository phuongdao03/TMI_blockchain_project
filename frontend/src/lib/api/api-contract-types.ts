export interface ResponseMeta {
  request_id: string;
}

export interface ListResponseMeta {
  request_id?: string;
  requestId?: string;
  page: number;
  pageSize: number;
  total: number;
}

export type ActivityKind = "FAVORITE" | "SHARE";

export interface ActivityItem {
  activityId: string;
  kind: ActivityKind;
  publicWorkId: string;
  slug: string;
  title: string;
  shortDescription: string;
  channel: "NATIVE" | "COPY_LINK" | null;
  createdAt: string;
}

export interface ActivityPage {
  items: ActivityItem[];
  nextCursor: string | null;
}

export interface SuccessEnvelope<Data> {
  success: true;
  data: Data;
  meta: ResponseMeta;
}

export interface ErrorEnvelope {
  success: false;
  error: {
    code: string;
    message: string;
    details: Record<string, unknown>;
    request_id: string;
  };
}
