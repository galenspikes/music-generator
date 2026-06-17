// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
import React, { useCallback, useRef, useState } from "react";

const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));

// Touch devices: a vertical-drag knob fights page scroll and the target is
// tiny. Render the slider instead — far friendlier under a thumb.
const COARSE =
  typeof window !== "undefined" &&
  window.matchMedia &&
  window.matchMedia("(pointer: coarse)").matches;

function snap(v, step, min) {
  if (!step) return v;
  const n = Math.round((v - min) / step) * step + min;
  // avoid float crud like 0.30000000004
  const decimals = (String(step).split(".")[1] || "").length;
  return Number(n.toFixed(decimals));
}

const fmt = (v, step) => {
  const decimals = (String(step ?? "").split(".")[1] || "").length;
  return typeof v === "number" ? v.toFixed(decimals) : v;
};

/* Rotary knob — vertical drag to turn. ~270° sweep. */
export function Knob({ value, min = 0, max = 1, step = 0.01, onChange }) {
  const ref = useRef(null);
  const drag = useRef(null);
  const v = typeof value === "number" ? value : Number(value) || min;
  const frac = (clamp(v, min, max) - min) / (max - min || 1);
  const angle = -135 + frac * 270;

  const onDown = (e) => {
    e.preventDefault();
    drag.current = { y: e.clientY ?? e.touches?.[0]?.clientY, v };
    window.addEventListener("pointermove", onMove);
    window.addEventListener("pointerup", onUp);
  };
  const onMove = (e) => {
    if (!drag.current) return;
    const dy = drag.current.y - e.clientY;
    const next = snap(clamp(drag.current.v + (dy / 180) * (max - min), min, max), step, min);
    onChange(next);
  };
  const onUp = () => {
    drag.current = null;
    window.removeEventListener("pointermove", onMove);
    window.removeEventListener("pointerup", onUp);
  };
  const onWheel = (e) => {
    e.preventDefault();
    onChange(snap(clamp(v + (e.deltaY < 0 ? step : -step), min, max), step, min));
  };

  const R = 22;
  const a0 = ((-135 - 90) * Math.PI) / 180;
  const a1 = ((angle - 90) * Math.PI) / 180;
  const large = angle - -135 > 180 ? 1 : 0;
  const arc = (a) => `${28 + R * Math.cos(a)} ${28 + R * Math.sin(a)}`;

  return (
    <div className="knob" ref={ref} onPointerDown={onDown} onWheel={onWheel} title="drag · scroll">
      <svg viewBox="0 0 56 56" className="knob-svg">
        <circle cx="28" cy="28" r={R} className="knob-track" />
        <path d={`M ${arc(a0)} A ${R} ${R} 0 ${large} 1 ${arc(a1)}`} className="knob-arc" />
        <circle cx="28" cy="28" r="16" className="knob-cap" />
        <line
          x1="28" y1="28"
          x2={28 + 14 * Math.cos((angle - 90) * Math.PI / 180)}
          y2={28 + 14 * Math.sin((angle - 90) * Math.PI / 180)}
          className="knob-needle"
        />
      </svg>
      <span className="knob-val">{fmt(v, step)}</span>
    </div>
  );
}

export function Slider({ value, min = 0, max = 100, step = 1, onChange }) {
  const v = typeof value === "number" ? value : Number(value) || min;
  return (
    <div className="slider">
      <input
        type="range" min={min} max={max} step={step} value={v}
        onChange={(e) => onChange(snap(Number(e.target.value), step, min))}
      />
      <span className="slider-val">{fmt(v, step)}</span>
    </div>
  );
}

export function IntField({ value, min, max, onChange }) {
  return (
    <input
      className="intfield" type="number" value={value ?? ""}
      min={min} max={max}
      onChange={(e) => onChange(e.target.value === "" ? null : Number(e.target.value))}
    />
  );
}

export function Segmented({ value, options, onChange }) {
  return (
    <div className="segmented">
      {options.map((o) => (
        <button
          key={o}
          className={"seg" + (String(value) === String(o) ? " on" : "")}
          onClick={() => onChange(o)}
        >
          {o}
        </button>
      ))}
    </div>
  );
}

export function Dropdown({ value, options, onChange }) {
  return (
    <select className="dropdown" value={value ?? ""} onChange={(e) => onChange(e.target.value)}>
      {options.map((o) => (
        <option key={o} value={o}>{o}</option>
      ))}
    </select>
  );
}

export function Toggle({ value, onChange }) {
  const on = value === true || value === 1 || value === "1";
  return (
    <button className={"toggle" + (on ? " on" : "")} onClick={() => onChange(!on)} role="switch" aria-checked={on}>
      <span className="toggle-knob" />
      <span className="toggle-led" />
    </button>
  );
}

export function Chips({ value = [], options, onChange }) {
  const set = new Set((value || []).map(String));
  const flip = (o) => {
    const next = new Set(set);
    next.has(o) ? next.delete(o) : next.add(o);
    onChange([...next]);
  };
  return (
    <div className="chips">
      {options.map((o) => (
        <button key={o} className={"tchip" + (set.has(o) ? " on" : "")} onClick={() => flip(o)}>
          {o}
        </button>
      ))}
    </div>
  );
}

export function TagList({ value = [], onChange, placeholder }) {
  const [draft, setDraft] = useState("");
  const list = value || [];
  const add = () => {
    const t = draft.trim();
    if (t) { onChange([...list, t]); setDraft(""); }
  };
  return (
    <div className="taglist">
      <div className="tags">
        {list.map((t, i) => (
          <span key={i} className="tag">
            <code>{t}</code>
            <button onClick={() => onChange(list.filter((_, j) => j !== i))}>×</button>
          </span>
        ))}
      </div>
      <input
        value={draft}
        placeholder={placeholder || "add token…"}
        onChange={(e) => setDraft(e.target.value)}
        onKeyDown={(e) => e.key === "Enter" && add()}
        onBlur={add}
      />
    </div>
  );
}

export function TextField({ value, onChange, multiline, mono = true, placeholder }) {
  const cls = "textfield" + (mono ? " mono" : "");
  if (multiline) {
    return (
      <textarea
        className={cls} rows={2} spellCheck={false} placeholder={placeholder}
        value={value ?? ""} onChange={(e) => onChange(e.target.value)}
      />
    );
  }
  return (
    <input
      className={cls} spellCheck={false} placeholder={placeholder}
      value={value ?? ""} onChange={(e) => onChange(e.target.value)}
    />
  );
}

/* Dispatch a schema param to the right control. */
export function Control({ param, value, onChange }) {
  const c = param.control;
  const common = { value, onChange };
  switch (c) {
    case "knob":
      if (COARSE)
        return <Slider {...common} min={param.min ?? 0} max={param.max ?? 1} step={param.step ?? 0.01} />;
      return <Knob {...common} min={param.min ?? 0} max={param.max ?? 1} step={param.step ?? 0.01} />;
    case "slider":
      return <Slider {...common} min={param.min ?? 0} max={param.max ?? 100} step={param.step ?? 1} />;
    case "int":
      return <IntField {...common} min={param.min} max={param.max} />;
    case "segmented":
      return <Segmented {...common} options={param.choices || []} />;
    case "dropdown":
      return <Dropdown {...common} options={param.choices || []} />;
    case "toggle":
      return <Toggle {...common} />;
    case "chips":
      return <Chips {...common} options={param.choices || []} />;
    case "taglist":
      return <TagList {...common} />;
    case "text":
    default:
      return <TextField {...common} multiline={param.multiline} />;
  }
}
