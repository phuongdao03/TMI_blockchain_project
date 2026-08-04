import { createServer } from "node:http";

const user = {
  id: "c57912cc-714c-4ab5-9fd9-1c5b38cd902b",
  email: "owner@tmigroup.vn",
  roles: [
    "APPLICANT",
    "REVIEWER",
    "COUNCIL_MEMBER",
    "COUNCIL_SECRETARY",
    "CONTENT_ADMIN",
  ],
  accountType: "INDIVIDUAL_APPLICANT",
};
const organizationId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
const avatarMediaId = "6a0bb388-3c26-4417-aed8-3ca05c212d1f";
const dossierId = "9155dbf5-bb3e-449d-8bf0-9572cc642cac";
const evidenceId = "5f81fa20-ec0a-4393-a90c-bf9c6285766d";
const categoryId = "4d28db19-1507-5a45-a50d-cd0aa83029ec";
const reviewAssignmentId = "4155dbf5-bb3e-449d-8bf0-9572cc642cac";
const reviewVersionId = "8155dbf5-bb3e-449d-8bf0-9572cc642cac";
const reviewMediaId = "7155dbf5-bb3e-449d-8bf0-9572cc642cac";
const councilSessionId = "9255dbf5-bb3e-449d-8bf0-9572cc642cac";
const councilCaseId = "9355dbf5-bb3e-449d-8bf0-9572cc642cac";
const paymentOrderId = "a255dbf5-bb3e-449d-8bf0-9572cc642cac";
const profile = {
  userId: user.id,
  email: user.email,
  fullName: "Nguyễn Minh Anh",
  phone: "+84901234567",
  avatarMediaId: null,
  locale: "vi-VN",
  timezone: "Asia/Ho_Chi_Minh",
};
const organization = {
  id: organizationId,
  code: "TMI-LAB",
  legalName: "Công ty TNHH TMI Lab",
  displayName: "TMI Lab",
  taxCode: "0312345678",
  status: "ACTIVE",
  ownerUserId: user.id,
  currentRole: "OWNER",
  canManageMembers: true,
};
const members = [
  {
    userId: user.id,
    email: user.email,
    roleCode: "OWNER",
    status: "ACTIVE",
    joinedAt: "2026-07-30T08:00:00Z",
  },
  {
    userId: "5f81fa20-ec0a-4393-a90c-bf9c6285766d",
    email: "member@tmigroup.vn",
    roleCode: "MEMBER",
    status: "INVITED",
    joinedAt: null,
  },
];
let dossier = null;
let evidences = [];
let versions = [];
let timeline = [];
let reviewAssignmentStatus = "ASSIGNED";
let review = null;
let councilSessionStatus = "DRAFT";
let councilAttendance = null;
let councilConflict = null;
let councilVote = null;
let paymentOrder = null;
let paymentStatusReads = 0;
let cmsPosts = [];
const publicWorkId = "d255dbf5-bb3e-449d-8bf0-9572cc642cac";
let publicWork = {
  id: publicWorkId,
  dossierId,
  certificateId: "7eaec2d2-c99a-42c9-8f1e-71462ba01ea0",
  slug: "di-san-so-tmi",
  title: "Di sản số TMI",
  shortDescription: "Tác phẩm số đã hoàn tất quy trình xác lập minh bạch.",
  fullDescription: "Một bản giới thiệu công khai chỉ chứa dữ liệu được duyệt.",
  authorDisplayName: "TMI Studio",
  categoryId,
  categoryName: "Thương hiệu",
  tagIds: [],
  thumbnailMediaId: null,
  publicationStatus: "DRAFT",
  visibility: "PUBLIC",
  publishedAt: null,
  scheduledPublishAt: null,
  featuredAt: null,
  featuredUntil: null,
  version: 1,
  checklist: [{ code: "TITLE_REQUIRED", passed: true }],
};

function envelope(data) {
  return JSON.stringify({
    success: true,
    data,
    meta: { request_id: "e2e-request" },
  });
}

function paginatedEnvelope(data) {
  return JSON.stringify({
    success: true,
    data,
    meta: {
      requestId: "e2e-request",
      page: 1,
      pageSize: 20,
      total: data.length,
    },
  });
}

async function readJson(request) {
  let body = "";
  for await (const chunk of request) {
    body += chunk;
  }
  return body ? JSON.parse(body) : {};
}

function error(status, code, message) {
  return {
    status,
    body: JSON.stringify({
      success: false,
      error: {
        code,
        message,
        details: {},
        request_id: "e2e-request",
      },
    }),
  };
}

function send(response, status, body, headers = {}) {
  response.writeHead(status, {
    "Content-Type": "application/json",
    ...headers,
  });
  response.end(body);
}

const server = createServer(async (request, response) => {
  const path = new URL(request.url ?? "/", "http://127.0.0.1").pathname;
  const authenticated = request.headers.cookie?.includes(
    "tmi_access=e2e-access",
  );
  const csrfProtected =
    authenticated && request.headers["x-csrf-token"] === "e2e-csrf";
  const publicAsset = {
    slug: "bo-nhan-dien-tmi",
    title: "Bộ nhận diện TMI",
    summary: "Hệ thống nhận diện thương hiệu đã được xác lập.",
    categoryCode: "BRAND",
    categoryName: "Thương hiệu",
    certificateNumber: "TMI-2026-7EAEC2D2C99A",
    certificateStatus: "ACTIVE",
    issuedAt: "2026-07-31T00:00:00Z",
    transactionHash: `0x${"34".repeat(32)}`,
  };
  const catalogWork = {
    id: "32324c61-89fd-44c2-b803-67d8cf5f203e",
    slug: "bo-nhan-dien-tmi",
    title: "Bộ nhận diện TMI",
    shortDescription:
      "Hệ thống nhận diện thương hiệu đã được công bố minh bạch.",
    authorDisplayName: "TMI Studio",
    categoryName: "Thương hiệu",
    categorySlug: "brand",
    tags: [{ name: "Tiêu biểu", slug: "featured" }],
    publishedAt: "2026-07-31T00:00:00Z",
    isFeatured: true,
    thumbnailUrl: null,
    thumbnailAltText: null,
  };
  const catalogDetail = {
    ...catalogWork,
    fullDescription:
      "Một câu chuyện công khai dài hơn về giá trị đã được xác lập.",
    organizationDisplayName: "TMI Group",
    visibility: "PUBLIC",
    certificate: {
      certificateNumber: "TMI-2026-7EAEC2D2C99A",
      status: "ACTIVE",
      issuedAt: "2026-07-31T00:00:00Z",
      expiresAt: null,
    },
    proof: {
      network: "local",
      transactionHash: publicAsset.transactionHash,
      status: "CONFIRMED",
      confirmations: 3,
      confirmedAt: "2026-07-31T10:00:00Z",
    },
    media: [],
    relatedWorks: [],
    canonicalSlug: catalogWork.slug,
    redirected: false,
  };
  if (request.method === "GET" && path === "/api/v1/public/seo/sitemap") {
    send(
      response,
      200,
      envelope({
        generation: "e2e-public-sitemap",
        total: 1,
        pageSize: 10000,
        pageCount: 1,
        generatedAt: "2026-07-31T10:00:00Z",
      }),
    );
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/seo/sitemap/1") {
    send(
      response,
      200,
      envelope([
        {
          slug: catalogWork.slug,
          lastModified: "2026-07-31T10:00:00Z",
        },
      ]),
    );
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/works") {
    send(response, 200, paginatedEnvelope([catalogWork]));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/public/search/autocomplete"
  ) {
    send(
      response,
      200,
      envelope([
        {
          kind: "work",
          label: catalogWork.title,
          slug: catalogWork.slug,
        },
        { kind: "category", label: "Thương hiệu", slug: "brand" },
      ]),
    );
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/search/facets") {
    send(
      response,
      200,
      envelope({
        categories: [{ slug: "brand", label: "Thương hiệu", count: 1 }],
        tags: [{ slug: "featured", label: "Tiêu biểu", count: 1 }],
        approximate: false,
      }),
    );
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/search") {
    send(response, 200, JSON.stringify({
      success: true,
      data: [
        {
          id: catalogWork.id,
          slug: catalogWork.slug,
          title: catalogWork.title,
          shortDescription: catalogWork.shortDescription,
          authorDisplayName: catalogWork.authorDisplayName,
          categoryName: catalogWork.categoryName,
          categorySlug: catalogWork.categorySlug,
          certificateNumber: "TMI-2026-7EAEC2D2C99A",
          certificateStatus: "ACTIVE",
          publishedAt: catalogWork.publishedAt,
        },
      ],
      meta: {
        requestId: "e2e-search-request",
        nextCursor: "e2e-next-cursor",
        durationMs: 14,
        version: "search-v1",
      },
    }));
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/works/featured") {
    send(response, 200, envelope([catalogWork]));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/public/works/bo-nhan-dien-tmi/qr"
  ) {
    const png = Buffer.from(
      "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mNk+A8AAQUBAScY42YAAAAASUVORK5CYII=",
      "base64",
    );
    response.writeHead(200, {
      "Cache-Control": "no-store",
      "Content-Location": "http://127.0.0.1:3100/tai-san/bo-nhan-dien-tmi",
      "Content-Type": "image/png",
    });
    response.end(png);
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/public/works/${catalogWork.id}/reports`
  ) {
    send(
      response,
      201,
      envelope({
        id: "105ac997-68a2-40d1-8194-a2181d0a9c32",
        status: "OPEN",
      }),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/public/works/bo-nhan-dien-cu"
  ) {
    response.writeHead(308, {
      Location: "/api/v1/public/works/bo-nhan-dien-tmi",
    });
    response.end();
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/public/works/bo-nhan-dien-tmi"
  ) {
    send(response, 200, envelope(catalogDetail), {
      "Cache-Control": "no-store",
    });
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/public/works/chia-se-rieng"
  ) {
    send(
      response,
      200,
      envelope({
        ...catalogDetail,
        id: "42324c61-89fd-44c2-b803-67d8cf5f203e",
        slug: "chia-se-rieng",
        title: "Tác phẩm chia sẻ riêng",
        visibility: "UNLISTED",
        canonicalSlug: "chia-se-rieng",
      }),
      {
        "Cache-Control": "no-store",
        "X-Robots-Tag": "noindex, nofollow",
      },
    );
    return;
  }
  if (
    request.method === "GET" &&
    [
      "/api/v1/public/works/tai-san-rieng-tu",
      "/api/v1/public/works/tai-san-da-dinh-chi",
      "/api/v1/public/works/11111111-1111-4111-8111-111111111111",
    ].includes(path)
  ) {
    const missing = error(404, "HTTP_ERROR", "Public work was not found.");
    send(response, missing.status, missing.body, {
      "Cache-Control": "no-store",
    });
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/tags") {
    send(
      response,
      200,
      envelope([
        {
          id: "44ecb5a4-41b5-4c99-892b-8c0757af1c68",
          name: "Tiêu biểu",
          slug: "featured",
          isActive: true,
        },
      ]),
    );
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/assets") {
    send(response, 200, paginatedEnvelope([publicAsset]));
    return;
  }
  if (request.method === "GET" && path === "/api/v1/public/categories") {
    send(
      response,
      200,
      envelope([
        {
          id: categoryId,
          code: "BRAND",
          name: "Thương hiệu",
          slug: "brand",
          description: "Tài sản thương hiệu.",
          assetCount: 1,
        },
      ]),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/public/assets/bo-nhan-dien-tmi"
  ) {
    send(
      response,
      200,
      envelope({
        asset: publicAsset,
        metadata: {
          schemaVersion: 1,
          asset: { title: publicAsset.title },
        },
        network: "local",
        contractAddress: `0x${"12".repeat(20)}`,
        confirmations: 3,
      }),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/verify/certificate/TMI-2026-7EAEC2D2C99A"
  ) {
    send(
      response,
      200,
      envelope({
        status: "VALID",
        checkedAt: "2026-07-31T10:00:00Z",
        certificateNumber: publicAsset.certificateNumber,
        assetTitle: publicAsset.title,
        categoryName: publicAsset.categoryName,
        issuedAt: publicAsset.issuedAt,
        expiresAt: null,
        version: 1,
        network: "local",
        contractAddress: `0x${"12".repeat(20)}`,
        transactionHash: publicAsset.transactionHash,
        confirmations: 3,
        confirmedAt: "2026-07-31T10:00:00Z",
        explorerUrl: null,
      }),
    );
    return;
  }
  const demoCertificate = {
    id: "7eaec2d2-c99a-42c9-8f1e-71462ba01ea0",
    certificateNumber: publicAsset.certificateNumber,
    dossierId,
    dossierCode: "TMI-2026-DEMO0001",
    assetTitle: publicAsset.title,
    categoryName: publicAsset.categoryName,
    currentVersionNo: 1,
    status: "ACTIVE",
    issuedAt: publicAsset.issuedAt,
    expiresAt: "2027-07-31T00:00:00Z",
    pdfReady: true,
    network: "local",
    contractAddress: `0x${"12".repeat(20)}`,
    transactionHash: publicAsset.transactionHash,
    blockchainStatus: "CONFIRMED",
    confirmations: 3,
  };
  if (
    request.method === "GET" &&
    path === "/api/v1/certificates" &&
    authenticated
  ) {
    send(response, 200, paginatedEnvelope([demoCertificate]));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/certificates/${demoCertificate.id}` &&
    authenticated
  ) {
    send(
      response,
      200,
      envelope({
        certificate: demoCertificate,
        metadata: {
          schemaVersion: 1,
          asset: {
            title: publicAsset.title,
            category: publicAsset.categoryName,
          },
        },
        metadataHash: "ab".repeat(32),
        qrPayload: "http://127.0.0.1:3100/kiem-tra/demo-token",
      }),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/certificates/${demoCertificate.id}/download` &&
    authenticated
  ) {
    send(
      response,
      200,
      envelope({
        url: "http://127.0.0.1:3100/kiem-tra/demo-token",
        expiresAt: Math.floor(Date.now() / 1000) + 300,
      }),
    );
    return;
  }
  if (request.method === "GET" && path === "/api/v1/verify/demo-token") {
    send(
      response,
      200,
      envelope({
        status: "VALID",
        checkedAt: "2026-07-31T10:00:00Z",
        certificateNumber: publicAsset.certificateNumber,
        assetTitle: publicAsset.title,
        categoryName: publicAsset.categoryName,
        issuedAt: publicAsset.issuedAt,
        expiresAt: "2027-07-31T00:00:00Z",
        version: 1,
        network: "local",
        contractAddress: `0x${"12".repeat(20)}`,
        transactionHash: publicAsset.transactionHash,
        confirmations: 3,
        confirmedAt: "2026-07-31T10:00:00Z",
        explorerUrl: null,
      }),
    );
    return;
  }
  if (request.method === "POST" && path === "/api/e2e/reset-payment") {
    dossier = {
      id: dossierId,
      code: "TMI-2026-PAYMENT001",
      ownerUserId: user.id,
      organizationId: null,
      categoryId,
      title: "Hồ sơ thương hiệu đã được duyệt",
      slug: null,
      summary: "Hồ sơ sẵn sàng thanh toán phí xác lập.",
      status: "APPROVED",
      visibility: "PRIVATE",
      currentVersionNo: 1,
      submittedAt: "2026-07-31T08:00:00Z",
      createdAt: "2026-07-31T08:00:00Z",
      updatedAt: "2026-08-01T08:00:00Z",
      canEdit: false,
    };
    evidences = [];
    versions = [];
    timeline = [];
    paymentOrder = null;
    paymentStatusReads = 0;
    send(response, 200, envelope({ status: "reset" }));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/dossiers/${dossierId}/payment-orders` &&
    csrfProtected &&
    dossier?.status === "APPROVED"
  ) {
    dossier = { ...dossier, status: "PAYMENT_PENDING" };
    paymentOrder = {
      id: paymentOrderId,
      orderCode: "PAY-2026-E2E00001",
      dossierId,
      provider: "mock",
      providerOrderId: "mock-provider-order",
      amountMinor: 1000000,
      currency: "VND",
      status: "PENDING",
      expiresAt: "2026-08-01T08:15:00Z",
      paidAt: null,
      checkoutUrl: "http://127.0.0.1:4010/mock-checkout",
      qrPayload: "TMI|PAY-2026-E2E00001",
      createdAt: "2026-08-01T08:00:00Z",
      updatedAt: "2026-08-01T08:00:00Z",
    };
    send(response, 201, envelope(paymentOrder));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/payment-orders/${paymentOrderId}` &&
    authenticated &&
    paymentOrder
  ) {
    paymentStatusReads += 1;
    if (paymentStatusReads >= 2) {
      paymentOrder = {
        ...paymentOrder,
        status: "PAID",
        paidAt: "2026-08-01T08:03:00Z",
        checkoutUrl: null,
        qrPayload: null,
        updatedAt: "2026-08-01T08:03:00Z",
      };
      dossier = { ...dossier, status: "PAID" };
    }
    send(response, 200, envelope(paymentOrder));
    return;
  }
  if (request.method === "GET" && path === "/mock-checkout") {
    response.writeHead(200, { "Content-Type": "text/plain; charset=utf-8" });
    response.end("Mock payment checkout");
    return;
  }
  const reviewAssignment = {
    id: reviewAssignmentId,
    dossierId,
    dossierVersionId: reviewVersionId,
    reviewerUserId: user.id,
    assignedBy: user.id,
    dueAt: "2026-08-08T08:00:00Z",
    status: reviewAssignmentStatus,
    conflictDeclaredAt:
      reviewAssignmentStatus === "ASSIGNED" ? null : "2026-08-02T08:00:00Z",
    conflictReason: null,
  };
  const reviewSnapshot = {
    schemaVersion: 1,
    dossier: {
      id: dossierId,
      code: "HS-2026-REVIEW01",
      title: "Hồ sơ thương hiệu TMI",
      summary: "Hồ sơ kiểm thử thẩm định 5T.",
    },
    evidences: [
      {
        id: evidenceId,
        mediaAssetId: reviewMediaId,
        evidenceType: "OWNERSHIP_DOCUMENT",
        title: "Giấy xác nhận quyền sở hữu",
        description: "Tài liệu gốc đã được kiểm tra checksum.",
        issuedAt: "2026-07-20T08:00:00Z",
        displayOrder: 0,
        isPublic: false,
        media: {
          mimeType: "application/pdf",
          bytes: 2048,
          sha256: "a".repeat(64),
        },
      },
    ],
  };
  const councilSession = {
    id: councilSessionId,
    code: "HD-2026-E2E",
    title: "Phiên xét duyệt thương hiệu số",
    scheduledAt: "2026-08-03T08:00:00Z",
    status: councilSessionStatus,
    quorumRequired: 1,
    openedAt: ["OPEN", "CLOSED"].includes(councilSessionStatus)
      ? "2026-08-03T08:05:00Z"
      : null,
    closedAt: councilSessionStatus === "CLOSED" ? "2026-08-03T08:15:00Z" : null,
    minutesHash: councilSessionStatus === "CLOSED" ? "c".repeat(64) : null,
    memberCount: 1,
    attendanceCount: councilAttendance ? 1 : 0,
  };
  const councilCase = {
    id: councilCaseId,
    sessionId: councilSessionId,
    dossierId,
    dossierVersionId: reviewVersionId,
    dossierCode: "HS-2026-COUNCIL",
    dossierTitle: "Hồ sơ thương hiệu số TMI",
    versionNo: 1,
    decision: councilSessionStatus === "CLOSED" ? "APPROVE" : null,
  };
  const councilResult =
    councilSessionStatus === "CLOSED"
      ? {
          caseId: councilCaseId,
          dossierId,
          dossierVersionId: reviewVersionId,
          decision: "APPROVE",
          quorumMet: true,
          validVoteCount: 1,
          voteCounts: {
            APPROVE: 1,
            REJECT: 0,
            ABSTAIN: 0,
            REQUEST_MORE_INFO: 0,
          },
        }
      : null;
  if (request.method === "POST" && path === "/api/e2e/reset-council") {
    councilSessionStatus = "DRAFT";
    councilAttendance = null;
    councilConflict = null;
    councilVote = null;
    send(response, 200, envelope({ status: "reset" }));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/council/sessions" &&
    authenticated
  ) {
    send(
      response,
      200,
      paginatedEnvelope([
        {
          session: councilSession,
          myAttendanceConfirmedAt: councilAttendance,
        },
      ]),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/council/sessions/${councilSessionId}` &&
    authenticated
  ) {
    send(
      response,
      200,
      envelope({
        session: councilSession,
        myAttendanceConfirmedAt: councilAttendance,
        cases: [
          {
            case: councilCase,
            myConflict: councilConflict,
            myVote: councilVote,
            result: councilResult,
          },
        ],
      }),
    );
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/council/sessions/${councilSessionId}/attendance` &&
    csrfProtected &&
    councilSessionStatus === "DRAFT"
  ) {
    councilAttendance = "2026-08-03T08:01:00Z";
    send(
      response,
      200,
      envelope({
        id: "9455dbf5-bb3e-449d-8bf0-9572cc642cac",
        sessionId: councilSessionId,
        memberUserId: user.id,
        attendanceConfirmedAt: councilAttendance,
      }),
    );
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/admin/council/sessions/${councilSessionId}/open` &&
    csrfProtected &&
    councilAttendance
  ) {
    councilSessionStatus = "OPEN";
    send(response, 200, envelope({ ...councilSession, status: "OPEN" }));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/council/cases/${councilCaseId}/conflict` &&
    csrfProtected &&
    councilSessionStatus === "OPEN"
  ) {
    const input = await readJson(request);
    councilConflict = {
      id: "9555dbf5-bb3e-449d-8bf0-9572cc642cac",
      caseId: councilCaseId,
      memberUserId: user.id,
      hasConflict: input.hasConflict,
      reason: input.reason,
      declaredAt: "2026-08-03T08:06:00Z",
    };
    send(response, 200, envelope(councilConflict));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/council/cases/${councilCaseId}/vote` &&
    csrfProtected &&
    councilSessionStatus === "OPEN" &&
    councilConflict?.hasConflict === false
  ) {
    const input = await readJson(request);
    councilVote = {
      id: "9655dbf5-bb3e-449d-8bf0-9572cc642cac",
      caseId: councilCaseId,
      memberUserId: user.id,
      choice: input.choice,
      reason: input.reason,
      votedAt: "2026-08-03T08:10:00Z",
    };
    send(response, 200, envelope(councilVote));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/admin/council/sessions/${councilSessionId}/close` &&
    csrfProtected &&
    councilVote
  ) {
    councilSessionStatus = "CLOSED";
    send(
      response,
      200,
      envelope({
        ...councilSession,
        status: "CLOSED",
        closedAt: "2026-08-03T08:15:00Z",
        minutesHash: "c".repeat(64),
      }),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/council/sessions/${councilSessionId}/minutes` &&
    authenticated &&
    councilSessionStatus === "CLOSED"
  ) {
    send(
      response,
      200,
      envelope({
        sessionId: councilSessionId,
        sessionCode: "HD-2026-E2E",
        closedAt: "2026-08-03T08:15:00Z",
        quorumRequired: 1,
        minutesHash: "c".repeat(64),
        cases: [councilResult],
      }),
    );
    return;
  }
  if (request.method === "POST" && path === "/api/e2e/reset-review") {
    reviewAssignmentStatus = "ASSIGNED";
    review = null;
    send(response, 200, envelope({ status: "reset" }));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/reviewer/assignments" &&
    authenticated
  ) {
    send(
      response,
      200,
      paginatedEnvelope([
        {
          assignment: reviewAssignment,
          dossierCode: "HS-2026-REVIEW01",
          dossierTitle: "Hồ sơ thương hiệu TMI",
          versionNo: 1,
        },
      ]),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/reviewer/assignments/${reviewAssignmentId}` &&
    authenticated
  ) {
    const visible = ["IN_PROGRESS", "SUBMITTED"].includes(
      reviewAssignmentStatus,
    );
    send(
      response,
      200,
      envelope({
        assignment: reviewAssignment,
        dossierCode: "HS-2026-REVIEW01",
        dossierTitle: "Hồ sơ thương hiệu TMI",
        versionNo: 1,
        canonicalHash: visible ? "b".repeat(64) : null,
        snapshotJson: visible ? reviewSnapshot : null,
        review,
      }),
    );
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/reviewer/assignments/${reviewAssignmentId}/conflict` &&
    csrfProtected
  ) {
    const input = await readJson(request);
    reviewAssignmentStatus = input.hasConflict ? "CONFLICTED" : "IN_PROGRESS";
    send(
      response,
      200,
      envelope({
        ...reviewAssignment,
        status: reviewAssignmentStatus,
        conflictDeclaredAt: "2026-08-02T08:00:00Z",
        conflictReason: input.reason ?? null,
      }),
    );
    return;
  }
  if (
    request.method === "PUT" &&
    path === `/api/v1/reviewer/assignments/${reviewAssignmentId}/draft` &&
    csrfProtected &&
    reviewAssignmentStatus === "IN_PROGRESS"
  ) {
    const input = await readJson(request);
    const scores = [
      input.truthScore,
      input.transparencyScore,
      input.ownershipScore,
      input.professionalismScore,
      input.respectScore,
    ];
    review = {
      id: "3155dbf5-bb3e-449d-8bf0-9572cc642cac",
      assignmentId: reviewAssignmentId,
      ...input,
      totalScore: scores.every((score) => Number.isInteger(score))
        ? scores.reduce((total, score) => total + score, 0)
        : null,
      submittedAt: null,
    };
    send(response, 200, envelope(review));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/reviewer/assignments/${reviewAssignmentId}/submit` &&
    csrfProtected &&
    review &&
    review.totalScore === 80 &&
    review.recommendation === "APPROVE" &&
    Object.values(review.criterionComments ?? {}).filter(
      (comment) => comment.trim().length > 0,
    ).length === 5
  ) {
    reviewAssignmentStatus = "SUBMITTED";
    review = { ...review, submittedAt: "2026-08-02T09:00:00Z" };
    send(response, 200, envelope(review));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/media/${reviewMediaId}/signed-url` &&
    authenticated &&
    ["IN_PROGRESS", "SUBMITTED"].includes(reviewAssignmentStatus)
  ) {
    send(
      response,
      200,
      envelope({
        url: "http://127.0.0.1:4010/mock-evidence.pdf",
        expiresAt: 1785657900,
      }),
    );
    return;
  }
  if (request.method === "GET" && path === "/mock-evidence.pdf") {
    response.writeHead(200, { "Content-Type": "application/pdf" });
    response.end("%PDF-1.4\n%%EOF");
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/dossiers" &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, paginatedEnvelope(dossier ? [dossier] : []));
    return;
  }
  if (
    request.method === "POST" &&
    path === "/api/v1/dossiers" &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf"
  ) {
    const input = await readJson(request);
    dossier = {
      id: dossierId,
      code: "TMI-2026-E2E000000001",
      ownerUserId: user.id,
      organizationId: input.organizationId ?? null,
      categoryId,
      title: input.title,
      slug: null,
      summary: input.summary ?? null,
      status: "DRAFT",
      visibility: input.visibility ?? "PRIVATE",
      currentVersionNo: 0,
      submittedAt: null,
      createdAt: "2026-07-31T08:00:00Z",
      updatedAt: "2026-07-31T08:00:00Z",
      canEdit: true,
    };
    evidences = [];
    versions = [];
    timeline = [];
    send(response, 201, envelope(dossier));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/dossiers/${dossierId}` &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    dossier
  ) {
    send(response, 200, envelope({ ...dossier, evidences }));
    return;
  }
  if (
    request.method === "PATCH" &&
    path === `/api/v1/dossiers/${dossierId}` &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf" &&
    dossier
  ) {
    const input = await readJson(request);
    dossier = {
      ...dossier,
      ...input,
      updatedAt: "2026-07-31T08:01:00Z",
    };
    send(response, 200, envelope(dossier));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/dossiers/${dossierId}/evidences` &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf"
  ) {
    const input = await readJson(request);
    const evidence = {
      id: evidenceId,
      dossierId,
      dossierVersionId: null,
      mediaAssetId: input.mediaAssetId,
      evidenceType: input.evidenceType,
      title: input.title,
      description: input.description ?? null,
      issuedAt: input.issuedAt ?? null,
      displayOrder: input.displayOrder ?? 0,
      isPublic: input.isPublic ?? false,
      mimeType: "image/png",
      bytes: 68,
      sha256: "a".repeat(64),
    };
    evidences = [evidence];
    send(response, 201, envelope(evidence));
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/dossiers/${dossierId}/submit` &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf" &&
    request.headers["idempotency-key"] &&
    dossier
  ) {
    const version = {
      id: "0bb644bb-b373-42e4-ae68-d2b2af28678e",
      dossierId,
      versionNo: 1,
      snapshotJson: { schemaVersion: 1 },
      canonicalHash: "b".repeat(64),
      submittedBy: user.id,
      submittedAt: "2026-07-31T08:02:00Z",
    };
    dossier = {
      ...dossier,
      status: "SUBMITTED",
      currentVersionNo: 1,
      submittedAt: version.submittedAt,
      canEdit: false,
    };
    evidences = evidences.map((item) => ({
      ...item,
      dossierVersionId: version.id,
    }));
    versions = [version];
    timeline = [
      {
        id: "8db15a26-acbf-41f6-adc7-2d9fdd305551",
        dossierId,
        fromStatus: "DRAFT",
        toStatus: "SUBMITTED",
        actorUserId: user.id,
        reasonCode: "APPLICANT_SUBMIT",
        note: null,
        createdAt: version.submittedAt,
      },
    ];
    send(response, 200, envelope({ dossier, version }));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/dossiers/${dossierId}/versions` &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, envelope(versions));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/dossiers/${dossierId}/timeline` &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, envelope(timeline));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/auth/me" &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, envelope(user));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/admin/cms/posts" &&
    authenticated
  ) {
    send(response, 200, paginatedEnvelope(cmsPosts));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/admin/public-works" &&
    authenticated
  ) {
    send(response, 200, paginatedEnvelope([publicWork]));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/admin/public-works/categories" &&
    authenticated
  ) {
    send(
      response,
      200,
      envelope([
        {
          id: categoryId,
          parentId: null,
          code: "BRAND",
          name: "Thương hiệu",
          slug: "thuong-hieu",
          description: null,
          isActive: true,
          displayOrder: 0,
        },
      ]),
    );
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/admin/public-works/tags" &&
    authenticated
  ) {
    send(response, 200, envelope([]));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/admin/public-works/${publicWorkId}` &&
    authenticated
  ) {
    send(response, 200, envelope(publicWork));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/admin/public-works/${publicWorkId}/media` &&
    authenticated
  ) {
    send(response, 200, envelope([]));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/admin/public-works/${publicWorkId}/preview` &&
    authenticated
  ) {
    send(
      response,
      200,
      envelope({
        slug: publicWork.slug,
        title: publicWork.title,
        shortDescription: publicWork.shortDescription,
        fullDescription: publicWork.fullDescription,
        authorDisplayName: publicWork.authorDisplayName,
        categoryName: publicWork.categoryName,
        media: [],
        canPublish: true,
      }),
    );
    return;
  }
  if (
    request.method === "PATCH" &&
    path === `/api/v1/admin/public-works/${publicWorkId}` &&
    csrfProtected
  ) {
    const payload = await readJson(request);
    publicWork = { ...publicWork, ...payload, version: publicWork.version + 1 };
    send(response, 200, envelope(publicWork));
    return;
  }
  if (
    request.method === "PUT" &&
    path === `/api/v1/admin/public-works/${publicWorkId}/tags` &&
    csrfProtected
  ) {
    const payload = await readJson(request);
    publicWork = { ...publicWork, tagIds: payload.tagIds };
    response.writeHead(204, { "X-Request-Id": "e2e-request" });
    response.end();
    return;
  }
  if (
    request.method === "POST" &&
    path === `/api/v1/admin/public-works/${publicWorkId}/publish` &&
    csrfProtected
  ) {
    publicWork = {
      ...publicWork,
      publicationStatus: "PUBLISHED",
      publishedAt: "2026-07-31T10:05:00Z",
      version: publicWork.version + 1,
    };
    send(response, 200, envelope(publicWork));
    return;
  }
  if (
    request.method === "POST" &&
    path === "/api/v1/admin/cms/posts" &&
    csrfProtected
  ) {
    const payload = await readJson(request);
    const post = {
      id: "c255dbf5-bb3e-449d-8bf0-9572cc642cac",
      ...payload,
      categoryId: payload.categoryId ?? null,
      status: "DRAFT",
      version: 1,
      publishedAt: null,
      createdAt: "2026-07-31T10:00:00Z",
      updatedAt: "2026-07-31T10:00:00Z",
    };
    cmsPosts = [post];
    send(response, 201, envelope(post));
    return;
  }
  if (
    request.method === "POST" &&
    path ===
      "/api/v1/admin/cms/posts/c255dbf5-bb3e-449d-8bf0-9572cc642cac/publish" &&
    csrfProtected
  ) {
    cmsPosts = cmsPosts.map((post) => ({
      ...post,
      status: "PUBLISHED",
      version: 2,
      publishedAt: "2026-07-31T10:05:00Z",
    }));
    send(response, 200, envelope(cmsPosts[0]));
    return;
  }
  for (const resource of ["pages", "banners", "categories"]) {
    if (
      request.method === "GET" &&
      path === `/api/v1/admin/cms/${resource}` &&
      authenticated
    ) {
      send(response, 200, envelope([]));
      return;
    }
  }
  if (
    request.method === "POST" &&
    path === "/api/v1/media/upload-signature" &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf"
  ) {
    send(
      response,
      200,
      envelope({
        mediaId: avatarMediaId,
        publicId: `users/${user.id}/avatar`,
        uploadUrl: "/api/cloudinary/upload",
        cloudName: "tmi-e2e",
        apiKey: "e2e-api-key",
        signature: "a".repeat(40),
        parameters: {
          folder: `users/${user.id}`,
          public_id: "avatar",
          timestamp: "1785402000",
        },
        expiresAt: 1785402300,
      }),
    );
    return;
  }
  if (request.method === "POST" && path === "/api/cloudinary/upload") {
    send(
      response,
      200,
      JSON.stringify({
        public_id: `users/${user.id}/avatar`,
        signature: "b".repeat(40),
        version: 1,
      }),
    );
    return;
  }
  if (
    request.method === "POST" &&
    path === "/api/v1/media/complete" &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf"
  ) {
    send(
      response,
      200,
      envelope({
        id: avatarMediaId,
        status: "ACTIVE",
        mimeType: "image/png",
        bytes: 68,
        width: 1,
        height: 1,
        durationMs: null,
      }),
    );
    return;
  }
  if (
    request.method === "PATCH" &&
    path === "/api/v1/users/me" &&
    request.headers.cookie?.includes("tmi_access=e2e-access") &&
    request.headers["x-csrf-token"] === "e2e-csrf"
  ) {
    send(response, 200, envelope({ ...profile, avatarMediaId }));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/users/me" &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, envelope(profile));
    return;
  }
  if (
    request.method === "GET" &&
    path === "/api/v1/organizations" &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, envelope([organization]));
    return;
  }
  if (
    request.method === "GET" &&
    path === `/api/v1/organizations/${organizationId}/members` &&
    request.headers.cookie?.includes("tmi_access=e2e-access")
  ) {
    send(response, 200, envelope(members));
    return;
  }
  if (request.method === "POST" && path === "/api/v1/auth/login") {
    const credentials = await readJson(request);
    if (
      credentials.email !== "owner@tmigroup.vn" ||
      credentials.password !== "correct horse battery staple"
    ) {
      const failure = error(401, "INVALID_CREDENTIALS", "Sai thông tin.");
      send(response, failure.status, failure.body);
      return;
    }
    publicWork = {
      ...publicWork,
      publicationStatus: "DRAFT",
      publishedAt: null,
      version: 1,
    };
    send(response, 200, envelope({ user }), {
      "Set-Cookie": [
        "tmi_access=e2e-access; Path=/; HttpOnly; SameSite=Lax",
        "tmi_refresh=e2e-refresh; Path=/; HttpOnly; SameSite=Lax",
        "tmi_csrf=e2e-csrf; Path=/; SameSite=Lax",
      ],
    });
    return;
  }
  if (
    request.method === "POST" &&
    path === "/api/v1/auth/refresh" &&
    request.headers.cookie?.includes("tmi_refresh=e2e-refresh") &&
    request.headers.cookie?.includes("tmi_csrf=e2e-csrf") &&
    request.headers["x-csrf-token"] === "e2e-csrf"
  ) {
    send(response, 200, envelope({ status: "refreshed" }), {
      "Set-Cookie": [
        "tmi_access=e2e-access; Path=/; HttpOnly; SameSite=Lax",
        "tmi_refresh=e2e-refresh; Path=/; HttpOnly; SameSite=Lax",
        "tmi_csrf=e2e-csrf; Path=/; SameSite=Lax",
      ],
    });
    return;
  }

  const failure = error(401, "UNAUTHENTICATED", "Authentication is required.");
  send(response, failure.status, failure.body);
});

server.listen(4010, "127.0.0.1");

function close() {
  server.close(() => process.exit(0));
}

process.on("SIGINT", close);
process.on("SIGTERM", close);
