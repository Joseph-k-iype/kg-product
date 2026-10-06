import {
  createContext,
  useContext,
  useState,
  useEffect,
  useRef,
  useId,
  cloneElement,
} from "react";
import type { ReactNode, FormEvent, ReactElement } from "react";
import { Link } from "react-router-dom";
import {
  ArrowUpRight,
  Check,
  ChevronRight,
  FileText,
  LoaderCircle,
  X,
} from "lucide-react";
import { refresh } from "../api/client";
const labels: Record<string, string> = {
  not_checked: "Needs checks",
  insufficient_data: "Needs input",
  stale: "Checks out of date",
  queued: "Waiting",
  running: "Preparing",
  ready: "Ready",
  failed: "Needs attention",
  draft: "Draft",
  submitted: "Awaiting approval",
  approved: "Approved",
  published: "Published",
  superseded: "Request superseded",
  rejected: "Changes requested",
  active: "Active",
  needs_preparation: "Needs preparation",
  fixture_synced: "Demo sync completed",
  registered: "Registered source",
  connected: "Connected · snapshot imported",
  definitions_ready: "Definitions imported",
  local_upload: "Local uploads",
  uploaded: "Uploaded",
  extracted: "Text ready",
  chunked: "Excerpts ready",
  embedded: "Search ready",
  graph_built: "Facts ready",
  validated: "Validated",
  passed: "Passed",
};
export function Status({ value, label }: { value: string; label?: string }) {
  return (
    <span className={"status " + value}>
      {label || labels[value] || value.replaceAll("_", " ")}
    </span>
  );
}
export function Block({
  title,
  subtitle,
  action,
  children,
  className = "",
}: {
  title?: string;
  subtitle?: string;
  action?: ReactNode;
  children: ReactNode;
  className?: string;
}) {
  return (
    <section className={"block " + className}>
      {title && (
        <header className="block-head">
          <div>
            <h2>{title}</h2>
            {subtitle && <p>{subtitle}</p>}
          </div>
          {action}
        </header>
      )}
      {children}
    </section>
  );
}
export function PageTitle({
  eyebrow,
  title,
  description,
  action,
}: {
  eyebrow?: string;
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="page-title">
      <div>
        {eyebrow && <div className="eyebrow">{eyebrow}</div>}
        <h1>{title}</h1>
        <p>{description}</p>
      </div>
      {action}
    </div>
  );
}
export function Empty({
  title,
  description,
  action,
}: {
  title: string;
  description: string;
  action?: ReactNode;
}) {
  return (
    <div className="empty">
      <div className="round-icon">
        <FileText size={23} />
      </div>
      <h3>{title}</h3>
      <p>{description}</p>
      {action}
    </div>
  );
}
export function Field({
  label,
  children,
  hint,
}: {
  label: string;
  children: ReactNode;
  hint?: string;
}) {
  const id = useId();
  return (
    <div className="field">
      <label htmlFor={id}>{label}</label>
      {cloneElement(children as ReactElement<Record<string, unknown>>, {
        id,
        "aria-describedby": hint ? id + "-hint" : undefined,
      })}
      {hint && <small id={id + "-hint"}>{hint}</small>}
    </div>
  );
}
export function Loading() {
  return (
    <div className="empty">
      <LoaderCircle className="spin" />
      <p>Loading your workspace…</p>
    </div>
  );
}
export function ErrorState({ message }: { message: string }) {
  return (
    <div className="error" role="alert">
      {message}
    </div>
  );
}
export function EvidenceLink({
  id,
  children = "Open source",
}: {
  id: string;
  children?: ReactNode;
}) {
  return (
    <a
      className="inline-link"
      href={"/api/documents/" + id + "/original"}
      target="_blank"
      rel="noreferrer"
    >
      {children}
      <ArrowUpRight size={14} />
    </a>
  );
}
export function NextLink({
  to,
  children,
}: {
  to: string;
  children: ReactNode;
}) {
  return (
    <Link className="inline-link" to={to}>
      {children}
      <ChevronRight size={14} />
    </Link>
  );
}
export function Drawer({
  title,
  onClose,
  children,
}: {
  title: string;
  onClose: () => void;
  children: ReactNode;
}) {
  const ref = useRef<HTMLDialogElement>(null);
  useEffect(() => {
    const old = document.activeElement as HTMLElement;
    ref.current?.showModal();
    return () => old?.focus();
  }, []);
  return (
    <dialog
      className="drawer"
      ref={ref}
      onCancel={onClose}
      onClick={(e) => {
        if (e.target === e.currentTarget) onClose();
      }}
    >
      <header>
        <h2>{title}</h2>
        <button
          className="icon-button"
          aria-label="Close details"
          onClick={onClose}
        >
          <X />
        </button>
      </header>
      {children}
    </dialog>
  );
}
export const NoticeContext = createContext<{
  busy: boolean;
  run: <T>(
    message: string,
    operation: () => Promise<T>,
  ) => Promise<T | undefined>;
}>({ busy: false, run: async () => undefined });
export function NoticeProvider({ children }: { children: ReactNode }) {
  const [notice, setNotice] = useState<{
      message: string;
      error: boolean;
    } | null>(null),
    [busy, setBusy] = useState(false);
  async function run<T>(
    message: string,
    operation: () => Promise<T>,
  ): Promise<T | undefined> {
    setBusy(true);
    try {
      const result = await operation();
      setNotice({ message, error: false });
      refresh();
      return result;
    } catch (e) {
      setNotice({
        message:
          e instanceof Error ? e.message : "Unable to finish this action",
        error: true,
      });
      return undefined;
    } finally {
      setBusy(false);
    }
  }
  return (
    <NoticeContext.Provider value={{ busy, run }}>
      {children}
      {notice && (
        <div
          className={"toast " + (notice.error ? "error" : "")}
          role={notice.error ? "alert" : "status"}
        >
          {notice.error ? <X size={16} /> : <Check size={16} />}
          <span>{notice.message}</span>
          <button aria-label="Dismiss message" onClick={() => setNotice(null)}>
            <X size={16} />
          </button>
        </div>
      )}
    </NoticeContext.Provider>
  );
}
export function useNotice() {
  return useContext(NoticeContext);
}
export function stopSubmit(e: FormEvent) {
  e.preventDefault();
}
export function date(value: string) {
  return new Date(value).toLocaleDateString("en", {
    month: "short",
    day: "numeric",
    year: "numeric",
  });
}
