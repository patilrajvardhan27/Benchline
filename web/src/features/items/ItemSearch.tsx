import { useId } from "react";

interface Props {
  value: string;
  onChange: (value: string) => void;
}

export function ItemSearch({ value, onChange }: Props) {
  const id = useId();
  const hintId = `${id}-hint`;
  return (
    <div className="field">
      <label htmlFor={id}>Search products</label>
      <input id={id} type="search" value={value} autoComplete="off" aria-describedby={hintId}
        onChange={(e) => { onChange(e.target.value); }} placeholder="atorvastatin 20 mg" />
      <span id={hintId} className="hint">Search by drug name or the start of an 11-digit NDC.</span>
    </div>
  );
}
