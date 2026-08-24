import { Eye, EyeOff } from "lucide-react";
import { type InputHTMLAttributes, useId, useState } from "react";

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
  const [passwordVisible, setPasswordVisible] = useState(false);
  const isPasswordField = props.type === "password";

  return (
    <div className="space-y-2">
      <label
        className="auth-field-label block font-mono text-[0.65rem] font-medium tracking-[0.1em] text-neutral-700 uppercase"
        htmlFor={inputId}
      >
        {label}
      </label>
      <div className={isPasswordField ? "relative" : undefined}>
        <input
          aria-describedby={error || hint ? descriptionId : undefined}
          aria-invalid={error ? true : undefined}
          className={cn(
            "auth-field-control min-h-12 w-full rounded-md border border-neutral-200 bg-neutral-50 px-3.5 py-2 text-base text-neutral-950 outline-none transition-colors placeholder:text-neutral-500 hover:border-neutral-300 focus:border-primary-600 focus:bg-white focus:ring-3 focus:ring-primary-100",
            isPasswordField && "pr-12",
            error && "border-error",
            className,
          )}
          id={inputId}
          {...props}
          type={isPasswordField && passwordVisible ? "text" : props.type}
        />
        {isPasswordField ? (
          <button
            aria-label={passwordVisible ? "Ẩn mật khẩu" : "Hiện mật khẩu"}
            className="auth-password-toggle absolute inset-y-0 right-0 grid w-12 place-items-center rounded-r-md text-neutral-500 hover:text-primary-700 focus-visible:outline-2 focus-visible:outline-offset-[-3px] focus-visible:outline-primary-600"
            onClick={() => setPasswordVisible((visible) => !visible)}
            type="button"
          >
            {passwordVisible ? (
              <EyeOff aria-hidden="true" size={18} />
            ) : (
              <Eye aria-hidden="true" size={18} />
            )}
          </button>
        ) : null}
      </div>
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
