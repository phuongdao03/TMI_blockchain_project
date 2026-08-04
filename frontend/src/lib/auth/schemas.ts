import { z } from "zod";

const email = z
  .string()
  .trim()
  .min(1, "Vui lòng nhập email.")
  .email("Email không đúng định dạng.");

const password = z
  .string()
  .min(12, "Mật khẩu phải có ít nhất 12 ký tự.")
  .max(128, "Mật khẩu không được vượt quá 128 ký tự.");

export const loginSchema = z.object({
  email,
  password: z.string().min(1, "Vui lòng nhập mật khẩu.").max(128),
});

export const registerSchema = z
  .object({
    email,
    password,
    confirmPassword: z.string(),
    accountType: z.enum([
      "PUBLIC_USER",
      "INDIVIDUAL_APPLICANT",
      "ORGANIZATION_APPLICANT",
    ]),
  })
  .refine((values) => values.password === values.confirmPassword, {
    message: "Mật khẩu xác nhận không khớp.",
    path: ["confirmPassword"],
  });

export const forgotPasswordSchema = z.object({ email });

export const tokenSchema = z.object({
  token: z
    .string()
    .trim()
    .min(32, "Liên kết xác minh không hợp lệ.")
    .max(256, "Liên kết xác minh không hợp lệ."),
});

export const resetPasswordSchema = z
  .object({
    token: tokenSchema.shape.token,
    newPassword: password,
    confirmPassword: z.string(),
  })
  .refine((values) => values.newPassword === values.confirmPassword, {
    message: "Mật khẩu xác nhận không khớp.",
    path: ["confirmPassword"],
  });

export type LoginValues = z.infer<typeof loginSchema>;
export type RegisterValues = z.infer<typeof registerSchema>;
export type ForgotPasswordValues = z.infer<typeof forgotPasswordSchema>;
export type TokenValues = z.infer<typeof tokenSchema>;
export type ResetPasswordValues = z.infer<typeof resetPasswordSchema>;
