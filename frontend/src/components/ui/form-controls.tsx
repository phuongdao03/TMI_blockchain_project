"use client";

import { ChevronDown } from "lucide-react";
import {
  forwardRef,
  type InputHTMLAttributes,
  type SelectHTMLAttributes,
} from "react";

import { cn } from "@/lib/utils";

export const SelectControl = forwardRef<
  HTMLSelectElement,
  SelectHTMLAttributes<HTMLSelectElement>
>(function SelectControl({ className, children, ...props }, ref) {
  return (
    <span className="ui-select-control__frame">
      <select
        {...props}
        className={cn("ui-select-control", className)}
        ref={ref}
      >
        {children}
      </select>
      <ChevronDown
        aria-hidden="true"
        className="ui-select-control__icon"
        focusable="false"
        strokeWidth={1.75}
      />
    </span>
  );
});

export const DateControl = forwardRef<
  HTMLInputElement,
  Omit<InputHTMLAttributes<HTMLInputElement>, "type">
>(function DateControl({ className, ...props }, ref) {
  return (
    <input
      {...props}
      className={cn("ui-date-control", className)}
      ref={ref}
      type="date"
    />
  );
});
