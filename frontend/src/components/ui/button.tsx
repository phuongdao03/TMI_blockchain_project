import { cva, type VariantProps } from "class-variance-authority";
import { forwardRef, type ButtonHTMLAttributes } from "react";

import { cn } from "@/lib/utils";

const buttonVariants = cva(
  "ui-button inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 py-2 text-sm font-semibold transition-[background-color,border-color,color,transform,box-shadow] focus-visible:outline-2 focus-visible:outline-offset-2 active:translate-y-px disabled:pointer-events-none disabled:opacity-50",
  {
    variants: {
      variant: {
        default: "ui-button--primary",
        outline: "ui-button--outline border",
        ghost: "ui-button--ghost",
      },
    },
    defaultVariants: {
      variant: "default",
    },
  },
);

type ButtonProps = ButtonHTMLAttributes<HTMLButtonElement> &
  VariantProps<typeof buttonVariants>;

const Button = forwardRef<HTMLButtonElement, ButtonProps>(function Button(
  { className, type = "button", variant, ...props },
  ref,
) {
  return (
    <button
      className={cn(buttonVariants({ variant }), className)}
      ref={ref}
      type={type}
      {...props}
    />
  );
});

export { Button, buttonVariants };
export type { ButtonProps };
