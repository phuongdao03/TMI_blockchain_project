import type {
  InputHTMLAttributes,
  ReactNode,
  SelectHTMLAttributes,
} from "react";
import styles from "./promotions.module.css";

export function Field({
  label,
  children,
}: {
  label: string;
  children: ReactNode;
}) {
  return (
    <label className={styles.field}>
      <span>{label}</span>
      {children}
    </label>
  );
}
export function TextField({
  label,
  ...props
}: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <Field label={label}>
      <input {...props} />
    </Field>
  );
}
export function Choice({
  label,
  children,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & {
  label: string;
  children: ReactNode;
}) {
  return (
    <Field label={label}>
      <select {...props}>{children}</select>
    </Field>
  );
}
export function Check({
  label,
  checked,
  onChange,
}: {
  label: string;
  checked: boolean;
  onChange: (checked: boolean) => void;
}) {
  return (
    <label className={styles.check}>
      <input
        type="checkbox"
        checked={checked}
        onChange={(event) => onChange(event.target.checked)}
      />
      <span>{label}</span>
    </label>
  );
}
export function dateInput(value: string | null) {
  return value
    ? new Intl.DateTimeFormat("sv-SE", {
        timeZone: "Asia/Ho_Chi_Minh",
        year: "numeric",
        month: "2-digit",
        day: "2-digit",
        hour: "2-digit",
        minute: "2-digit",
        hourCycle: "h23",
      })
        .format(new Date(value))
        .replace(" ", "T")
    : "";
}
export function dateValue(value: string) {
  return value ? new Date(`${value}:00+07:00`).toISOString() : null;
}
export function optionalNumber(value: string) {
  return value === "" ? null : Number(value);
}
export function readableError(error: unknown) {
  return error instanceof Error
    ? error.message
    : "Không thể hoàn tất thao tác. Vui lòng thử lại.";
}
