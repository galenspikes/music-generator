// Music Generator — Copyright (c) 2026 Galen Spikes. MIT License.
// https://github.com/galenspikes/music-generator
//
// A small toast/notification primitive. Two users today: load confirmations
// ("Loaded: …") and generation errors (a friendly line + a collapsible
// "Details" for the raw message). Kept deliberately minimal — no portal, no
// external deps — so it fits the in-process, single-App state model.
import React, { useCallback, useRef, useState } from "react";

let _seq = 0;

// Hook: owns the live toast list and their auto-dismiss timers. `push` returns
// the id so a caller can dismiss early. Errors are sticky by default (ttl 0) so
// a failure the user glanced away from is still there when they look back.
export function useToasts() {
  const [toasts, setToasts] = useState([]);
  const timers = useRef({});

  const dismiss = useCallback((id) => {
    setToasts((ts) => ts.filter((t) => t.id !== id));
    if (timers.current[id]) {
      clearTimeout(timers.current[id]);
      delete timers.current[id];
    }
  }, []);

  const push = useCallback((toast) => {
    const id = ++_seq;
    const type = toast.type || "info";
    setToasts((ts) => [...ts, { id, type, ...toast }]);
    const ttl = toast.ttl ?? (type === "error" ? 0 : 3200);
    if (ttl > 0) timers.current[id] = setTimeout(() => dismiss(id), ttl);
    return id;
  }, [dismiss]);

  return { toasts, push, dismiss };
}

const ICON = { error: "⚠", success: "✓", info: "◆" };

export function ToastStack({ toasts, onDismiss }) {
  if (!toasts || toasts.length === 0) return null;
  return (
    <div className="toast-stack" role="region" aria-live="polite" aria-label="notifications">
      {toasts.map((t) => (
        <Toast key={t.id} toast={t} onDismiss={() => onDismiss(t.id)} />
      ))}
    </div>
  );
}

function Toast({ toast, onDismiss }) {
  const [showDetails, setShowDetails] = useState(false);
  return (
    <div className={"toast toast-" + toast.type} role="alert">
      <span className="toast-icon">{ICON[toast.type] || ICON.info}</span>
      <div className="toast-body">
        <div className="toast-msg">{toast.message}</div>
        {toast.details && (
          <div className="toast-details">
            <button className="toast-details-toggle"
              onClick={() => setShowDetails((s) => !s)}>
              {showDetails ? "Hide details" : "Details"}
            </button>
            {showDetails && <pre className="toast-details-body">{toast.details}</pre>}
          </div>
        )}
      </div>
      <button className="toast-close" onClick={onDismiss} aria-label="dismiss">×</button>
    </div>
  );
}
