# Business-user design

The user's correction makes technical concepts secondary. Primary language is documents, concepts, attributes, rules, facts, checks, approvals, releases, evidence, and apps. Technical RDF source, vocabulary identifiers, graph mappings, model IDs, checksums, and release manifests are kept in Advanced views.

12ui generated four first-view candidates. Candidate C supplied the chosen system: a 212px navy sidebar, pale neutral workspace, flat bordered blocks, restrained blue actions, serif page titles, clean business tables, and small text-paired status labels. Nine sibling states and their HTML exports are retained under `design/branch/`.

The 12ui clickable-prototype pipeline failed while making a holding page, after all nine screen and HTML exports succeeded. Navigation SVG markup, token values, page/block structures, and typography from those exports were adapted into React. Actual persisted actions, keyboard semantics, narrow layouts, and the guided five-step form required additional structure. Target-based comparison kits covered all nine reference states; unsafe positional matches were not applied blindly. Accessible darker green/amber status text was retained after axe checks found low contrast in the original colors.

WeKnora informed the document-first onboarding, preparation timeline, and source-cited retrieval layout. This app retains its own release/governance model and the required PostgreSQL/pgvector, MinIO, RDF, and FalkorDB stack.
