import { cva, type VariantProps } from "class-variance-authority";
import type { ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-xl px-4 py-2 text-sm font-bold transition-all focus-visible:outline-2 focus-visible:outline-offset-2 disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default:
          "bg-primary-600 text-white shadow-md shadow-primary-950/10 hover:-translate-y-px hover:bg-primary-700 focus-visible:outline-primary-600",
        outline:
          "border border-neutral-200 bg-surface text-neutral-950 hover:bg-primary-50 focus-visible:outline-primary-600",
        ghost:
          "text-neutral-700 hover:bg-primary-50 hover:text-primary-700 focus-visible:outline-primary-600",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

function Button({
  className,
  type = "button",
  variant,
  ...props
}: ButtonProps) {
  return (
    <button
      className={cn(buttonVariants({ variant }), className)}
      type={type}
      {...props}
    />
  );
}

export { Button, buttonVariants };
export type { ButtonProps };
