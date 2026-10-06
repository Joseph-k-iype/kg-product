import type { Dispatch, SetStateAction } from "react";
import { FileText, Table2, Network, Upload, X } from "lucide-react";
import { api } from "../api/client";
import { Field, ErrorState } from "../components/shared";

export interface ImportPreview {
  kind: string;
  record_count: number;
  concept_count: number;
  relationship_count: number;
  columns: string[];
  sample_rows: Record<string, string>[];
  warnings: string[];
}
export interface ImportFile {
  id: string;
  file: File;
  loading: boolean;
  preview?: ImportPreview;
  error?: string;
}
export function DataFiles({
  items,
  setItems,
}: {
  items: ImportFile[];
  setItems: Dispatch<SetStateAction<ImportFile[]>>;
}) {
  async function add(files: File[]) {
    const additions = files.map((file) => ({
      id: crypto.randomUUID(),
      file,
      loading: true,
    }));
    setItems((current) => [...current, ...additions]);
    await Promise.all(
      additions.map(async (item) => {
        try {
          const body = new FormData();
          body.append("file", item.file);
          const preview = await api<ImportPreview>(
            "/imports/preview",
            "POST",
            body,
          );
          setItems((current) =>
            current.map((row) =>
              row.id === item.id ? { ...row, loading: false, preview } : row,
            ),
          );
        } catch (error) {
          setItems((current) =>
            current.map((row) =>
              row.id === item.id
                ? {
                    ...row,
                    loading: false,
                    error:
                      error instanceof Error
                        ? error.message
                        : "Could not read this file.",
                  }
                : row,
            ),
          );
        }
      }),
    );
  }
  return (
    <>
      <div className="intake-types">
        <div>
          <FileText size={20} />
          <h3>Documents</h3>
          <p>PDF, Word, text, Markdown</p>
          <small>Search passages with source evidence.</small>
        </div>
        <div>
          <Table2 size={20} />
          <h3>Structured records</h3>
          <p>CSV or JSON files</p>
          <small>Keep each row or object as a record.</small>
        </div>
        <div>
          <Network size={20} />
          <h3>Connected knowledge</h3>
          <p>Turtle files</p>
          <small>Import records, relationships, concepts, or rules.</small>
        </div>
      </div>
      <div className="upload-area">
        <Upload size={24} />
        <Field
          label="Add files"
          hint="Mix file types in one draft · up to 20 files · 20 MB each · UTF-8 for data files"
        >
          <input
            type="file"
            multiple
            accept=".pdf,.docx,.txt,.md,.csv,.json,.ttl,.turtle"
            onChange={(e) => {
              if (e.target.files) void add(Array.from(e.target.files));
              e.target.value = "";
            }}
          />
        </Field>
      </div>
      {items.map((item) => (
        <div className="import-file" key={item.id}>
          <div className="import-file-head">
            <div>
              <strong>{item.file.name}</strong>
              <p>
                {item.loading
                  ? "Checking this file…"
                  : item.error
                    ? "Fix or remove this file to continue"
                    : item.preview?.kind === "document"
                      ? "Document · text will be prepared after creation"
                      : item.preview?.kind === "definitions"
                        ? `${item.preview.concept_count} concept${item.preview.concept_count === 1 ? "" : "s"} · definitions only`
                        : `${item.preview?.record_count} records`}
              </p>
            </div>
            <button
              className="icon-button"
              type="button"
              aria-label={`Remove ${item.file.name}`}
              onClick={() =>
                setItems((current) =>
                  current.filter((row) => row.id !== item.id),
                )
              }
            >
              <X size={16} />
            </button>
          </div>
          {item.error && <ErrorState message={item.error} />}
          {!!item.preview?.columns.length && (
            <details>
              <summary>Preview columns and records</summary>
              <div className="table-wrap">
                <table>
                  <thead>
                    <tr>
                      {item.preview.columns.map((c) => (
                        <th key={c}>{c}</th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {item.preview.sample_rows.map((row, i) => (
                      <tr key={i}>
                        {item.preview!.columns.map((c) => (
                          <td key={c}>{row[c]}</td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </details>
          )}
          {!!item.preview?.warnings.length && (
            <p className="import-warning">
              Some advanced rules are unsupported. They will be listed under
              Concepts & Rules and may block quality checks.
            </p>
          )}
        </div>
      ))}
      {!items.length && (
        <p className="intake-note">
          No files yet. You can add them after creating the draft.
        </p>
      )}
    </>
  );
}

export interface SourceDraft {
  name: string;
  type: string;
  owner: string;
  location: string;
  freshness_days: number;
  config: {
    credential_env?: string;
    schema?: string;
    table?: string;
    token_env?: string;
    records_path?: string;
    format?: string;
    limit?: number;
  };
}
export const initialSource = (): SourceDraft => ({
  name: "",
  type: "postgres",
  owner: "Maya Chen",
  location: "",
  freshness_days: 30,
  config: {
    credential_env: "SOURCE_DATABASE_URL",
    schema: "public",
    table: "",
    limit: 1000,
  },
});
export function SourceFields({
  value,
  onChange,
}: {
  value: SourceDraft;
  onChange: (value: SourceDraft) => void;
}) {
  const change = (patch: Partial<SourceDraft>) =>
    onChange({ ...value, ...patch });
  const config = (patch: Partial<SourceDraft["config"]>) =>
    change({ config: { ...value.config, ...patch } });
  return (
    <div className="form-grid">
      <Field label="Source name">
        <input
          required
          value={value.name}
          onChange={(e) => change({ name: e.target.value })}
          placeholder="e.g. Customer database"
        />
      </Field>
      <Field label="Source type">
        <select
          value={value.type}
          onChange={(e) =>
            change({
              type: e.target.value,
              config:
                e.target.value === "postgres"
                  ? {
                      credential_env: "SOURCE_DATABASE_URL",
                      schema: "public",
                      table: "",
                      limit: 1000,
                    }
                  : e.target.value === "api"
                    ? { format: "json", records_path: "", limit: 1000 }
                    : {},
            })
          }
        >
          <option value="postgres">PostgreSQL database</option>
          <option value="api">HTTP API</option>
          <option value="cloud">Cloud storage — register location</option>
          <option value="business">Business app — register location</option>
          <option value="external">
            Website or other source — register location
          </option>
          <option value="local">Local file library</option>
          <option value="fixture">Demo fixture source</option>
        </select>
      </Field>
      <Field label="Source owner">
        <input
          value={value.owner}
          onChange={(e) => change({ owner: e.target.value })}
        />
      </Field>
      <Field
        label={value.type === "api" ? "API endpoint" : "Source location"}
        hint={
          value.type === "api"
            ? "GET endpoint returning JSON records or CSV. Your administrator approves its origin."
            : "Link, workspace, folder, or system name. Do not enter passwords here."
        }
      >
        <input
          required={value.type === "api"}
          value={value.location}
          onChange={(e) => change({ location: e.target.value })}
          placeholder={
            value.type === "api"
              ? "https://service.example/records"
              : "Where does this data come from?"
          }
        />
      </Field>
      {value.type === "postgres" && (
        <>
          <Field
            label="Saved database connection"
            hint="The connection name supplied by your administrator; credentials stay on the server."
          >
            <input
              required
              value={value.config.credential_env || ""}
              onChange={(e) => config({ credential_env: e.target.value })}
              placeholder="SOURCE_SALES_DATABASE_URL"
            />
          </Field>
          <Field
            label="Table to import"
            hint="We read this table; we do not change its data."
          >
            <input
              required
              value={value.config.table || ""}
              onChange={(e) => config({ table: e.target.value })}
              placeholder="customers"
            />
          </Field>
          <Field label="Database schema">
            <input
              value={value.config.schema || "public"}
              onChange={(e) => config({ schema: e.target.value })}
            />
          </Field>
        </>
      )}
      {value.type === "api" && (
        <>
          <Field label="Response format">
            <select
              value={value.config.format || "json"}
              onChange={(e) => config({ format: e.target.value })}
            >
              <option value="json">JSON records</option>
              <option value="csv">CSV records</option>
            </select>
          </Field>
          {value.config.format !== "csv" && (
            <Field
              label="Records inside the response"
              hint="Leave empty for an array. For { data: [...] }, enter data; nested arrays can use data.items."
            >
              <input
                value={value.config.records_path || ""}
                onChange={(e) => config({ records_path: e.target.value })}
                placeholder="e.g. data.items"
              />
            </Field>
          )}
          <Field
            label="Saved API credential (optional)"
            hint="A server connection name such as SOURCE_CRM_TOKEN. Leave empty for a public API."
          >
            <input
              value={value.config.token_env || ""}
              onChange={(e) => config({ token_env: e.target.value })}
            />
          </Field>
        </>
      )}
      {(value.type === "postgres" || value.type === "api") && (
        <Field
          label="Records per import"
          hint="Each import reads a snapshot. A preview will explain if more records are available."
        >
          <select
            value={value.config.limit || 1000}
            onChange={(e) => config({ limit: Number(e.target.value) })}
          >
            <option value={100}>Up to 100 records</option>
            <option value={1000}>Up to 1,000 records</option>
            <option value={10000}>Up to 10,000 records</option>
          </select>
        </Field>
      )}
      <Field
        label="Update target in days"
        hint="How often this source should be refreshed."
      >
        <input
          type="number"
          min={1}
          max={3650}
          value={value.freshness_days}
          onChange={(e) => change({ freshness_days: Number(e.target.value) })}
        />
      </Field>
      <div className="full-span guidance">
        {value.type === "postgres" || value.type === "api"
          ? "Test the connection, then import a read-only snapshot. The original snapshot remains available as evidence."
          : "This registers the source location. Use file exports now; a live connector for this system is not configured."}
      </div>
    </div>
  );
}
