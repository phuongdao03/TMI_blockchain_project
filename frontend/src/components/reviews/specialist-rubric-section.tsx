"use client";

import type {
  ReviewEvidenceSnapshot,
  ReviewGateAnswer,
  ReviewRubric,
  SpecialistCriterionAnswer,
} from "@/lib/api/types";

const levels = [
  [0, "Không có căn cứ"], [1, "Rất yếu"], [2, "Yếu"],
  [3, "Đạt"], [4, "Tốt"], [5, "Xuất sắc"],
] as const;

export function specialistScore(
  rubric: ReviewRubric,
  answers: Record<string, SpecialistCriterionAnswer>,
) {
  if (rubric.criteria.some(({ key }) => answers[key] === undefined)) return null;
  return Math.round(
    rubric.criteria.reduce(
      (total, criterion) => total + (answers[criterion.key]!.score * criterion.weight) / 5,
      0,
    ),
  );
}

function EvidenceChoices({ evidences, value, onChange }: {
  evidences: ReviewEvidenceSnapshot[];
  value: string[];
  onChange: (value: string[]) => void;
}) {
  return <div className="mt-3 grid gap-2 sm:grid-cols-2">
    {evidences.map((evidence) => <label className="flex min-h-11 items-center gap-2 rounded-lg border border-[var(--theme-border)] bg-[var(--theme-surface)] p-2.5 text-sm" key={evidence.mediaAssetId}>
      <input checked={value.includes(evidence.mediaAssetId)} className="size-4 accent-primary-700" onChange={() => onChange(value.includes(evidence.mediaAssetId) ? value.filter((id) => id !== evidence.mediaAssetId) : [...value, evidence.mediaAssetId])} type="checkbox" />
      <span className="truncate">{evidence.title}</span>
    </label>)}
  </div>;
}

export function SpecialistRubricSection({ rubric, evidences, gateAnswers, specialistAnswers, onGateChange, onSpecialistChange, readOnly }: {
  rubric: ReviewRubric;
  evidences: ReviewEvidenceSnapshot[];
  gateAnswers: Record<string, ReviewGateAnswer>;
  specialistAnswers: Record<string, SpecialistCriterionAnswer>;
  onGateChange: (value: Record<string, ReviewGateAnswer>) => void;
  onSpecialistChange: (value: Record<string, SpecialistCriterionAnswer>) => void;
  readOnly: boolean;
}) {
  const total = specialistScore(rubric, specialistAnswers);
  return <section className="space-y-5" id="specialist-rubric">
    <header className="border-l-4 border-gold-500 pl-4">
      <p className="text-xs font-bold uppercase tracking-[0.16em] text-primary-700">Rubric chuyên biệt · phiên bản {rubric.version}</p>
      <div className="mt-1 flex flex-wrap items-end justify-between gap-3"><h3 className="text-xl font-bold">{rubric.title}</h3><strong className="text-xl tabular-nums">{total ?? "—"}/100</strong></div>
      <p className="mt-2 text-sm text-neutral-600">Cổng bắt buộc không được bù bằng tổng điểm. Mỗi tiêu chí phải có căn cứ và tài liệu dẫn chiếu.</p>
    </header>

    {rubric.gates.length > 0 ? <div className="space-y-3"><h4 className="font-bold">A. Điều kiện bắt buộc</h4>{rubric.gates.map((gate) => {
      const answer = gateAnswers[gate.key] ?? { outcome: "PASS", rationale: "", evidenceMediaIds: [] };
      return <fieldset className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4" disabled={readOnly} key={gate.key}>
        <legend className="px-1 font-bold">{gate.label}{gate.required !== false ? " · Bắt buộc" : ""}</legend>
        {gate.description ? <p className="text-sm text-neutral-600">{gate.description}</p> : null}
        <div className="mt-3 grid gap-3 sm:grid-cols-[12rem_1fr]"><select aria-label={`Kết quả ${gate.label}`} className="min-h-11 rounded-lg border bg-[var(--theme-surface)] px-3" onChange={(event) => onGateChange({ ...gateAnswers, [gate.key]: { ...answer, outcome: event.target.value as ReviewGateAnswer["outcome"] } })} value={answer.outcome}><option value="PASS">Đạt</option><option value="FAIL">Không đạt</option><option value="NOT_APPLICABLE">Không áp dụng</option></select><textarea aria-label={`Căn cứ ${gate.label}`} className="min-h-20 rounded-lg border bg-[var(--theme-surface)] p-3 text-sm" onChange={(event) => onGateChange({ ...gateAnswers, [gate.key]: { ...answer, rationale: event.target.value } })} placeholder="Nêu cách kiểm tra và kết quả…" value={answer.rationale} /></div>
        <EvidenceChoices evidences={evidences} onChange={(ids) => onGateChange({ ...gateAnswers, [gate.key]: { ...answer, evidenceMediaIds: ids } })} value={answer.evidenceMediaIds} />
      </fieldset>;
    })}</div> : null}

    <div className="space-y-3"><h4 className="font-bold">B. Tiêu chí theo loại hồ sơ</h4>{rubric.criteria.map((criterion, index) => {
      const answer = specialistAnswers[criterion.key] ?? { score: 0, rationale: "", evidenceMediaIds: [] };
      return <fieldset className="rounded-xl border border-[var(--theme-border)] bg-[var(--theme-elevated)] p-4" disabled={readOnly} key={criterion.key}>
        <legend className="px-1 font-bold"><span className="mr-2 text-primary-700">{String(index + 1).padStart(2, "0")}</span>{criterion.label} · {criterion.weight}%</legend>
        <p className="text-sm text-neutral-600">{criterion.description}</p>
        <div className="mt-3 grid gap-3 sm:grid-cols-[12rem_1fr]"><select aria-label={`Điểm ${criterion.label}`} className="min-h-11 rounded-lg border bg-[var(--theme-surface)] px-3" onChange={(event) => onSpecialistChange({ ...specialistAnswers, [criterion.key]: { ...answer, score: Number(event.target.value) } })} value={answer.score}>{levels.map(([score, label]) => <option key={score} value={score}>{score}/5 · {label}</option>)}</select><textarea aria-label={`Căn cứ ${criterion.label}`} className="min-h-24 rounded-lg border bg-[var(--theme-surface)] p-3 text-sm" onChange={(event) => onSpecialistChange({ ...specialistAnswers, [criterion.key]: { ...answer, rationale: event.target.value } })} placeholder="Nêu nhận định, phương pháp đối chứng và giới hạn…" value={answer.rationale} /></div>
        <EvidenceChoices evidences={evidences} onChange={(ids) => onSpecialistChange({ ...specialistAnswers, [criterion.key]: { ...answer, evidenceMediaIds: ids } })} value={answer.evidenceMediaIds} />
      </fieldset>;
    })}</div>
    <p className="rounded-xl border border-[var(--theme-border)] p-3 text-sm font-semibold">Ngưỡng chuyên biệt: duyệt từ {rubric.thresholds.approveMin}/100 · từ chối dưới {rubric.thresholds.rejectBelow}/100.</p>
  </section>;
}
