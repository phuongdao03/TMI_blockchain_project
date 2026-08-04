import { type InputHTMLAttributes, useId } from "react";

import { cn } from "@/lib/utils";

interface FormFieldProps extends InputHTMLAttributes<HTMLInputElement> {
  label: string;
  error?: string;
  hint?: string;
}

export function FormField({
  label,
  error,
  hint,
  className,
  id,
  ...props
}: FormFieldProps) {
  const generatedId = useId();
  const inputId = id ?? generatedId;
  const descriptionId = `${inputId}-description`;

  return (
    <div className="space-y-2">
      <label
        className="auth-field-label block font-mono text-[0.65rem] font-medium tracking-[0.1em] text-neutral-700 uppercase"
        htmlFor={inputId}
      >
        {label}
      </label>
      <input
        aria-describedby={error || hint ? descriptionId : undefined}
        aria-invalid={error ? true : undefined}
        className={cn(
          "auth-field-control min-h-12 w-full rounded-md border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-base text-neutral-950 outline-none transition-colors placeholder:text-neutral-500 hover:border-neutral-300 focus:border-primary-600 focus:bg-white focus:ring-3 focus:ring-primary-100",
          error && "border-error",
          className,
        )}
        id={inputId}
        {...props}
      />
      {error ? (
        <p
          className="auth-field-error text-sm font-medium text-error"
          id={descriptionId}
        >
          {error}
        </p>
      ) : hint ? (
        <p
          className="auth-field-hint text-sm text-neutral-500"
          id={descriptionId}
        >
          {hint}
        </p>
      ) : null}
    </div>
  );
}
