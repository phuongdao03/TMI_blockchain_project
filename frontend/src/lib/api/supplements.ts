import { request } from "@/lib/api/client";

export interface SupplementRequest {
  id: string;
  dossierId: string;
  requestedVersionId: string;
  criterionKey: string;
  criterionLabel: string;
  claimId: string | null;
  requestedInformation: string;
  reason: string;
  priority: "NORMAL" | "HIGH";
  dueAt: string | null;
  createdAt: string;
  status: "OPEN" | "ANSWERED" | "RESOLVED";
  revision: number;
  responses: Array<{
    id: string;
    sequenceNo: number;
    kind: "RESPONSE" | "RESOLVE" | "REOPEN";
    text: string;
    createdAt: string;
  }>;
}

export interface CreateSupplement {
  expectedVersionId: string;
  criterionKey: string;
  requestedInformation: string;
  reason: string;
  priority: "NORMAL" | "HIGH";
  dueAt?: string | null;
}

const path = (id: string) =>
  `/dossiers/${encodeURIComponent(id)}/supplement-requests`;

export const supplementApi = {
  list: (id: string) => request<SupplementRequest[]>(path(id)),
  create: (id: string, input: CreateSupplement) =>
    request<SupplementRequest>(path(id), {
      method: "POST",
      body: JSON.stringify(input),
    }),
  respond: (id: string, item: SupplementRequest, text: string) =>
    request<SupplementRequest>(`${path(id)}/${item.id}/response`, {
      method: "PUT",
      body: JSON.stringify({ expectedRevision: item.revision, text }),
    }),
  decide: (
    id: string,
    item: SupplementRequest,
    resolution: string,
    reopen: boolean,
  ) =>
    request<SupplementRequest>(`${path(id)}/${item.id}/resolve`, {
      method: "POST",
      body: JSON.stringify({
        expectedRevision: item.revision,
        resolution,
        reopen,
      }),
    }),
};
