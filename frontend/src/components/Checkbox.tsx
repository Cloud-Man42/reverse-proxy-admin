import { InputHTMLAttributes, ReactNode, useId } from "react";

type CheckboxProps = Omit<InputHTMLAttributes<HTMLInputElement>, "type" | "onChange"> & {
  checked: boolean;
  onChange: (checked: boolean) => void;
  label: ReactNode;
  description?: ReactNode;
  variant?: "inline" | "card";
  labelClassName?: string;
};

export function Checkbox({
  checked,
  onChange,
  label,
  description,
  variant = "inline",
  className = "",
  labelClassName = "",
  disabled,
  id,
  ...rest
}: CheckboxProps) {
  const autoId = useId();
  const inputId = id ?? autoId;

  const labelClasses = [
    variant === "card" ? "ui-checkbox-card" : "ui-checkbox-label",
    variant === "inline" && !description ? "ui-checkbox-label-inline" : "",
    disabled ? "opacity-60 cursor-not-allowed" : "",
    labelClassName,
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <label htmlFor={inputId} className={labelClasses}>
      <input
        {...rest}
        id={inputId}
        type="checkbox"
        className={`ui-checkbox ${description || variant === "card" ? "mt-0.5" : ""} ${className}`.trim()}
        checked={checked}
        disabled={disabled}
        onChange={(e) => onChange(e.target.checked)}
      />
      {description ? (
        <span className="min-w-0 flex-1">
          <span className="block font-medium leading-5">{label}</span>
          <span className="mt-1 block text-sm leading-5 text-white/60">{description}</span>
        </span>
      ) : (
        <span className="min-w-0 leading-5">{label}</span>
      )}
    </label>
  );
}
