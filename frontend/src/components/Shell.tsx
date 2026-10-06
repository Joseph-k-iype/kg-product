import { NavLink, Link, useLocation } from "react-router-dom";
import {
  Bell,
  ChevronDown,
  Menu,
  X,
  LayoutGrid,
  Archive,
  Files,
  Network,
  Search,
  ShieldCheck,
  CircleCheck,
  ScanSearch,
  GitBranch,
  Cable,
  MessageSquare,
} from "lucide-react";
import { useState } from "react";
import type { ReactNode } from "react";
const navIcons = [
  LayoutGrid,
  Archive,
  Files,
  Network,
  Search,
  ShieldCheck,
  CircleCheck,
  ScanSearch,
  GitBranch,
  Cable,
  MessageSquare,
];
const destinations = [
  ["/overview", "Overview"],
  ["/products", "Knowledge Products"],
  ["/sources", "Documents & Sources"],
  ["/concepts", "Concepts & Rules"],
  ["/explorer", "Explore Knowledge"],
  ["/health", "Quality Checks"],
  ["/reviews", "Approvals"],
  ["/retrieval", "Search Playground"],
  ["/lineage", "Evidence Trail"],
  ["/consumers", "Connected Apps"],
  ["/chat", "AI Chat"],
];
export function Shell({ children }: { children: ReactNode }) {
  const [open, setOpen] = useState(false),
    [identity, setIdentity] = useState(
      sessionStorage.getItem("identity") || "Demo author",
    );
  const path = useLocation().pathname;
  const select = (value: string) => {
    setIdentity(value);
    sessionStorage.setItem("identity", value);
    window.dispatchEvent(new Event("knowledge-updated"));
  };
  return (
    <div className="app-shell">
      <a href="#main" className="skip-link">
        Skip to content
      </a>
      <aside className={"sidebar " + (open ? "open" : "")}>
        <Link className="brand" to="/overview">
          <span className="brand-mark" aria-hidden="true">
            {Array.from({ length: 9 }, (_, i) => (
              <i key={i} />
            ))}
          </span>
          <span>
            Knowledge<span className="brand-sub">PRODUCT MANAGER</span>
          </span>
        </Link>
        <button
          className="mobile-close icon-button"
          aria-label="Close navigation"
          onClick={() => setOpen(false)}
        >
          <X />
        </button>
        <nav aria-label="Main navigation">
          {destinations.map(([url, label], i) => {
            const Icon = navIcons[i];
            return (
              <NavLink
                key={url}
                to={url}
                onClick={() => setOpen(false)}
                className={({ isActive }) => (isActive ? "active" : "")}
              >
                <Icon
                  className="nav-icon"
                  aria-hidden="true"
                  strokeWidth={1.6}
                />
                {label}
              </NavLink>
            );
          })}
        </nav>
        <div className="sidebar-bottom">
          <span className="demo-dot" />
          Local demo workspace<p>Synthetic identities & documents</p>
          <Link to="/operations">
            Service status <ChevronDown size={12} />
          </Link>
        </div>
      </aside>
      <div className="content-shell">
        <header className="topbar">
          <div className="breadcrumb">
            <button
              className="mobile-menu icon-button"
              aria-label="Open navigation"
              onClick={() => setOpen(true)}
            >
              <Menu />
            </button>
            <Link to="/overview">Workspace</Link>
            <span>/</span>
            <span>
              {path.startsWith("/products/")
                ? "Knowledge product"
                : destinations.find(([url]) => url === path)?.[1] ||
                  "Operations"}
            </span>
          </div>
          <div className="topbar-right">
            <Link
              to="/overview"
              className="icon-button"
              aria-label="View attention queue"
            >
              <Bell size={18} />
            </Link>
            <span className="avatar">
              {identity === "Demo reviewer" ? "MR" : "MC"}
            </span>
            <label className="identity">
              <span className="sr-only">Demo identity</span>
              <select value={identity} onChange={(e) => select(e.target.value)}>
                <option>Demo author</option>
                <option>Demo reviewer</option>
              </select>
              <small>Synthetic identity</small>
            </label>
          </div>
        </header>
        <main id="main" tabIndex={-1}>
          {children}
        </main>
      </div>
    </div>
  );
}
