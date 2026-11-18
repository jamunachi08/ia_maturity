import { Children, isValidElement, useContext, useId, useRef, useState } from "react";
import type { ChangeEvent, ReactNode, SelectHTMLAttributes } from "react";
import * as Primitive from "@radix-ui/react-select";
import { Check, ChevronDown, ChevronUp } from "lucide-react";
import { FieldLabelContext } from "./fieldContext";
import { useLanguage } from "./i18n";

function optionText(node: ReactNode): string {
  if (typeof node === "string" || typeof node === "number") return String(node);
  if (isValidElement<{ children?: ReactNode }>(node)) return optionText(node.props.children);
  return Children.toArray(node).map(optionText).join("");
}

/** One portal menu for every selector; the native bridge preserves form validation/serialization. */
export default function Select({
  children,
  value,
  defaultValue,
  onChange,
  name,
  disabled,
  required,
  id,
  className,
  "aria-label": ariaLabel,
  "aria-describedby": describedBy,
  autoFocus,
  ...rest
}: SelectHTMLAttributes<HTMLSelectElement>) {
  const { lang, t } = useLanguage(),
    fieldLabel = useContext(FieldLabelContext),
    generatedId = useId();
  const options = Children.toArray(children)
    .filter(isValidElement)
    .map((child) => {
      const props = (child as React.ReactElement<React.OptionHTMLAttributes<HTMLOptionElement>>).props;
      return {
        value: String(props.value ?? optionText(props.children)),
        label: props.children,
        disabled: props.disabled,
      };
    });
  const [internal, setInternal] = useState<string | undefined>(
    defaultValue === undefined ? undefined : String(defaultValue),
  );
  const [open, setOpen] = useState(false),
    [invalid, setInvalid] = useState(false);
  const trigger = useRef<HTMLButtonElement>(null),
    native = useRef<HTMLSelectElement>(null);
  const current = String(value ?? internal ?? options.find((o) => !o.disabled)?.value ?? "");
  const selected = options.find((o) => o.value === current);
  function change(next: string) {
    const decoded = next === "__grc_empty_option__" ? "" : next;
    setInternal(decoded);
    setInvalid(false);
    if (native.current) {
      native.current.value = decoded;
      onChange?.({ target: native.current, currentTarget: native.current } as ChangeEvent<HTMLSelectElement>);
    }
  }
  return (
    <span className="grc-select">
      <Primitive.Root
        value={current || "__grc_empty_option__"}
        onValueChange={change}
        open={open}
        onOpenChange={setOpen}
        disabled={disabled}
        dir={lang === "ar" ? "rtl" : "ltr"}
      >
        <Primitive.Trigger
          ref={trigger}
          id={id || generatedId}
          autoFocus={autoFocus}
          className={"grc-select-trigger " + (className || "")}
          aria-label={ariaLabel || fieldLabel}
          aria-describedby={describedBy}
          aria-required={required}
          aria-invalid={invalid || undefined}
        >
          <Primitive.Value>{selected?.label || t("No selection")}</Primitive.Value>
          <Primitive.Icon>
            <ChevronDown size={16} />
          </Primitive.Icon>
        </Primitive.Trigger>
        <Primitive.Portal>
          <Primitive.Content
            data-grc-select-content=""
            className="grc-select-content"
            position="popper"
            sideOffset={6}
            align="start"
            collisionPadding={12}
            onEscapeKeyDown={(e) => e.stopPropagation()}
          >
            <Primitive.ScrollUpButton className="grc-select-scroll">
              <ChevronUp size={14} />
            </Primitive.ScrollUpButton>
            <Primitive.Viewport className="grc-select-viewport">
              {options.map((option) => (
                <Primitive.Item
                  key={option.value}
                  value={option.value || "__grc_empty_option__"}
                  disabled={option.disabled}
                  className="grc-select-option"
                  textValue={optionText(option.label)}
                >
                  <Primitive.ItemText>{option.label}</Primitive.ItemText>
                  <Primitive.ItemIndicator>
                    <Check size={15} />
                  </Primitive.ItemIndicator>
                </Primitive.Item>
              ))}
            </Primitive.Viewport>
            <Primitive.ScrollDownButton className="grc-select-scroll">
              <ChevronDown size={14} />
            </Primitive.ScrollDownButton>
          </Primitive.Content>
        </Primitive.Portal>
      </Primitive.Root>
      <select
        {...rest}
        ref={native}
        aria-hidden="true"
        tabIndex={-1}
        className="grc-select-native"
        name={name}
        value={current}
        disabled={disabled}
        required={required}
        onChange={(e) => change(e.target.value)}
        onInvalid={(e) => {
          e.preventDefault();
          setInvalid(true);
          trigger.current?.focus();
          setOpen(true);
        }}
      >
        {!options.length && <option value="" />}
        {children}
      </select>
      {invalid && (
        <span className="grc-select-error" role="alert">
          {t("Please select an option.")}
        </span>
      )}
    </span>
  );
}
