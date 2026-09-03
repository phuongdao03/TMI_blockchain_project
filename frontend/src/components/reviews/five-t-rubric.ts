import type { ReviewFinding, ReviewRecommendation } from "@/lib/api/types";

export const scoreBands = [
  {
    min: 0,
    max: 4,
    label: "Không đạt",
    description: "Thiếu căn cứ, mâu thuẫn hoặc không thể kiểm chứng.",
  },
  {
    min: 5,
    max: 8,
    label: "Yếu",
    description: "Có khoảng trống trọng yếu, rủi ro quyết định cao.",
  },
  {
    min: 9,
    max: 11,
    label: "Đạt có điều kiện",
    description: "Có căn cứ một phần nhưng cần làm rõ hoặc bổ sung.",
  },
  {
    min: 12,
    max: 15,
    label: "Đạt chuẩn",
    description: "Bằng chứng đủ, nhất quán với chuẩn thẩm định.",
  },
  {
    min: 16,
    max: 18,
    label: "Tốt",
    description: "Bằng chứng đầy đủ và có đối chứng độc lập.",
  },
  {
    min: 19,
    max: 20,
    label: "Xuất sắc",
    description: "Khả năng kiểm chứng, truy xuất và thực hành nổi bật.",
  },
] as const;

export const reviewCriteria = [
  {
    key: "truth",
    label: "Tính đúng đắn",
    scoreKey: "truthScore",
    purpose: "Xác minh tính xác thực, chính xác và nhất quán của nội dung.",
    indicators: [
      "Nguồn gốc và tác giả",
      "Mốc thời gian, sự kiện",
      "Đối chứng độc lập",
    ],
  },
  {
    key: "transparency",
    label: "Tính minh bạch",
    scoreKey: "transparencyScore",
    purpose:
      "Đánh giá khả năng truy xuất nguồn, lịch sử và phương pháp công bố.",
    indicators: [
      "Chuỗi nguồn gốc",
      "Lịch sử chỉnh sửa",
      "Công khai giới hạn thông tin",
    ],
  },
  {
    key: "ownership",
    label: "Quyền sở hữu & trách nhiệm",
    scoreKey: "ownershipScore",
    purpose: "Kiểm tra quyền nộp, quyền sử dụng và trách nhiệm của chủ thể.",
    indicators: [
      "Quyền sở hữu/sử dụng",
      "Ủy quyền hợp lệ",
      "Cam kết và trách nhiệm",
    ],
  },
  {
    key: "professionalism",
    label: "Tính chuyên nghiệp",
    scoreKey: "professionalismScore",
    purpose: "Đánh giá chất lượng, độ hoàn thiện và năng lực thực hiện.",
    indicators: [
      "Chất lượng chuyên môn",
      "Tính hoàn chỉnh",
      "Khả năng duy trì và phát triển",
    ],
  },
  {
    key: "respect",
    label: "Tính tôn trọng",
    scoreKey: "respectScore",
    purpose:
      "Đánh giá tuân thủ pháp luật, đạo đức và tác động tới các bên liên quan.",
    indicators: [
      "Tuân thủ pháp luật",
      "Đạo đức và văn hóa",
      "Quyền lợi cộng đồng",
    ],
  },
] as const;

export function scoreBand(score: number | null | undefined) {
  if (score === null || score === undefined) return null;
  return (
    scoreBands.find((band) => score >= band.min && score <= band.max) ?? null
  );
}

export function decisionGate(
  scores: Array<number | null | undefined>,
  recommendation: ReviewRecommendation | null,
  findings: ReviewFinding[],
): { valid: boolean; message: string } {
  const completeScores = scores.filter(
    (score): score is number => score != null,
  );
  if (completeScores.length !== 5 || recommendation === null) {
    return {
      valid: false,
      message: "Hoàn tất đủ 5 tiêu chí và chọn kiến nghị.",
    };
  }
  const total = completeScores.reduce((sum, score) => sum + score, 0);
  if (recommendation === "APPROVE") {
    if (total < 75)
      return {
        valid: false,
        message: "Đề nghị phê duyệt cần tổng điểm từ 75/100.",
      };
    if (completeScores.some((score) => score < 12)) {
      return {
        valid: false,
        message: "Đề nghị phê duyệt yêu cầu mọi tiêu chí đạt ít nhất 12/20.",
      };
    }
    if (
      findings.some(
        ({ severity }) => severity === "HIGH" || severity === "CRITICAL",
      )
    ) {
      return {
        valid: false,
        message:
          "Phải xử lý phát hiện mức Cao/Nghiêm trọng trước khi đề nghị phê duyệt.",
      };
    }
  }
  if (
    recommendation === "SUPPLEMENT" &&
    !findings.some(({ action }) => action === "SUPPLEMENT")
  ) {
    return {
      valid: false,
      message:
        "Yêu cầu bổ sung cần ít nhất một phát hiện nêu rõ tài liệu phải bổ sung.",
    };
  }
  if (
    recommendation === "REJECT" &&
    total >= 50 &&
    !findings.some(({ severity }) => severity === "CRITICAL")
  ) {
    return {
      valid: false,
      message:
        "Đề nghị từ chối cần tổng điểm dưới 50 hoặc phát hiện Nghiêm trọng.",
    };
  }
  return { valid: true, message: "Kiến nghị phù hợp với cổng quyết định." };
}
