import { z } from "zod";

const optionalPhone = z
  .string()
  .trim()
  .refine(
    (value) => value === "" || /^\+[1-9]\d{7,14}$/.test(value),
    "Số điện thoại phải theo định dạng quốc tế, ví dụ +84901234567.",
  );

export const profileSchema = z.object({
  fullName: z.string().trim().max(255, "Họ tên không được quá 255 ký tự."),
  phone: optionalPhone,
  locale: z.string().trim().min(2).max(16),
  timezone: z.string().trim().min(1).max(64),
});

export const organizationSchema = z.object({
  code: z
    .string()
    .trim()
    .regex(
      /^[A-Za-z0-9][A-Za-z0-9_-]{2,31}$/,
      "Mã gồm 3–32 chữ, số, gạch ngang hoặc gạch dưới.",
    ),
  legalName: z.string().trim().min(1, "Vui lòng nhập tên pháp lý.").max(255),
  displayName: z.string().trim().min(1, "Vui lòng nhập tên hiển thị.").max(255),
  taxCode: z
    .string()
    .trim()
    .refine(
      (value) => value === "" || /^[A-Za-z0-9-]{3,32}$/.test(value),
      "Mã số thuế không hợp lệ.",
    ),
});

export const memberSchema = z.object({
  email: z.string().trim().email("Email không đúng định dạng."),
  roleCode: z.enum(["ORG_MANAGER", "MEMBER"]),
});

export type ProfileValues = z.infer<typeof profileSchema>;
export type OrganizationValues = z.infer<typeof organizationSchema>;
export type MemberValues = z.infer<typeof memberSchema>;
