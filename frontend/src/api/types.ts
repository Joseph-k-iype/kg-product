export interface Revision {
  id: string;
  number: number;
  generation: number;
  state: string;
  ontology_id: string | null;
  mapping_id: string | null;
  graph_build_id: string | null;
  config: Record<string, unknown>;
}
export interface Product {
  id: string;
  name: string;
  purpose: string;
  domain: string;
  owner: string;
  tags: string[];
  active_release_id: string | null;
  draft: Revision | null;
  revisions: Revision[];
  documents_total?: number;
  documents_ready?: number;
  quality?: string;
  processing?: string;
  publication?: string;
  consumer_count?: number;
  lifecycle?: string;
}
export interface Catalog {
  items: Product[];
  total: number;
  offset: number;
  limit: number;
}
export interface Attention {
  id: string;
  product_name: string;
  owner: string;
  severity: string;
  issue: string;
  action: string;
  url: string;
  detail?: string;
}
export interface Evidence {
  chunk_id: string;
  document_id: string;
  text: string;
  start: number;
  end: number;
  source_url: string;
  document_name?: string;
  source_row?: number;
  source_subject?: string;
}
export interface Chunk extends Evidence {
  id: string;
  ordinal: number;
  embedded: boolean;
  model_name: string | null;
  model_revision: string | null;
}
export interface Job {
  id: string;
  stage: string;
  state: string;
  attempt_count: number;
  error: string | null;
  attempts: {
    state: string;
    number: number;
    error?: string;
    started_at: string;
  }[];
}
export interface DocumentRecord {
  id: string;
  name: string;
  data_kind: string;
  active: boolean;
  record_count: number;
  product_id: string;
  revision_id: string;
  source_id: string | null;
  content_type: string;
  size: number;
  state: string;
  sha256: string;
  object_key: string;
  uploaded_at: string;
  uploaded_by: string;
  processing_version: string;
  extracted_text: string | null;
  chunks: Chunk[];
  jobs: Job[];
}
export interface Source {
  id: string;
  name: string;
  type: string;
  owner: string;
  location: string;
  config: Record<string, unknown>;
  freshness_days: number;
  product_ids: string[];
  connection_state: string;
  last_synced_at: string | null;
}
export interface Concept {
  iri: string;
  label: string;
  description: string;
  parent: string;
}
export interface PropertyDefinition {
  iri: string;
  label: string;
  kind: string;
  description: string;
  domain: string;
  range: string;
}
export interface Rule {
  iri: string;
  target: string;
  path: string;
  min_count: number;
  max_count: number | null;
  datatype: string;
}
export interface Mapping {
  id: string;
  version: number;
  classes: { iri: string; label: string }[];
  properties: { iri: string; key: string; kind: string }[];
}
export interface Ontology {
  id: string | null;
  version: number;
  generation: number;
  classes: Concept[];
  properties: PropertyDefinition[];
  shapes: Rule[];
  namespaces: { prefix: string; iri: string }[];
  unsupported_constructs: string[];
  turtle: string;
  mapping: Mapping | null;
}
export interface Metric {
  key: string;
  label: string;
  value: number | null;
  threshold: number;
  state: string;
}
export interface Finding {
  id?: string;
  entity_id?: string;
  path?: string;
  message: string;
  url: string;
}
export interface Evaluation {
  id: string;
  revision_id: string;
  state: string;
  generation: number;
  metrics: Metric[];
  findings: Finding[];
  created_at: string;
  inputs: Record<string, unknown>;
}
export interface Review {
  id: string;
  product_id: string;
  product_name: string;
  revision_id: string;
  state: string;
  summary: string;
  requester: string;
  reviewer_id: string | null;
  decision_reason: string | null;
  evaluation_id: string;
  generation: number;
  created_at: string;
  changes: {
    before: Record<string, unknown> | null;
    after: Record<string, unknown>;
    quality_evidence: Metric[];
    ontology_diff?: {
      added: { iri: string; label: string }[];
      removed: { iri: string; label: string }[];
      changed: { before: { label: string }; after: { label: string } }[];
    };
    document_changes?: { before: string[]; after: string[] };
  };
}
export interface Release {
  id: string;
  product_id: string;
  revision_id: string;
  number: number;
  manifest: Record<string, unknown>;
  created_at: string;
  published_by: string;
  product_name?: string;
}
export interface OverviewData {
  summary: {
    active_products: number;
    pending_reviews: number;
    blocked_releases: number;
    overdue_sources: number;
  };
  products: Product[];
  attention: Attention[];
  publications: Release[];
}
export interface Entity {
  id: string;
  type: string;
  label: string;
  iri: string;
  attributes: Record<string, string>;
  evidence: Evidence[];
  build_id: string;
  extraction_version: string;
  provenance_label: string;
  type_label?: string;
  attribute_labels?: Record<string, string>;
}
export interface Relationship {
  source: string;
  target: string;
  type: string;
  evidence: Evidence[];
}
export interface Neighborhood {
  nodes: Entity[];
  relationships: Relationship[];
}
export interface Hit {
  score: number | null;
  evidence: Evidence;
  entity?: Entity;
  related_facts?: Neighborhood[];
}
export interface Retrieval {
  results: Hit[];
  label: string;
  diagnostics: Record<string, unknown>;
}
export interface Consumer {
  id: string;
  name: string;
  type: string;
  product_id: string;
  product_name: string;
  release_policy: string;
  release_id: string | null;
  resolved: { release_id: string | null; number: number; state: string };
  usage: { label: string; requests_last_7_days: number };
}
export interface LineageNode {
  id: string;
  type: string;
  label: string;
  record_id: string;
  [key: string]: unknown;
}
export interface Lineage {
  nodes: LineageNode[];
  edges: { source: string; target: string; label: string }[];
  revision_id: string;
  release_id: string | null;
  label: string;
}
