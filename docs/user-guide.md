# Business user guide

A knowledge product is a collection of business information with a clear purpose, owner, evidence, and published version. You do not need to understand graphs or Turtle to use the guided workflows.

## Create a product

1. Open **Knowledge Products** and choose to create a product. Enter a name, purpose, domain, and owner.
2. In **Bring data**, add documents or structured files, or choose a saved database/API connection. Preview the data and remove invalid files before continuing. Mixed file types can belong to one product.
3. Choose a concept starter. Concepts describe useful business things, such as complaints and customers; attributes are their details, and relationships show how those things connect.
4. In **Readiness**, choose search and quality preferences. The matching-result count controls the maximum evidence matches returned by search. It is not a readiness score and does not mean checks have already passed.
5. Review the setup and create the draft. You can create an incomplete draft and add more data later.

A database/API credential reference must be configured by an administrator before a connection can read records. Other source locations can be registered and populated from exported files. **Import snapshot** captures the current selected records; it does not set up continuous synchronization.

## Prepare and inspect

Open **Prepare Knowledge** and run preparation. The timeline shows reading, evidence creation, search preparation, facts, and checks. The worker must be running. If a stage fails, inspect the reason, resolve it, and retry.

Open **Documents** to inspect originals and evidence. **Concepts & Rules** contains business forms; advanced representation views are available when technical inspection is needed. **Explore Knowledge** shows facts, relationships, and their supporting sources. A correction flag records a concern about the exact fact/version rather than changing an already published release.

## Understand quality checks

| Check | Business meaning |
|---|---|
| Sources up to date | Data falls within its configured freshness period. |
| Documents readable | Imported documents have usable extracted text. |
| Product details complete | Required business metadata is present. |
| Documents searchable | Evidence has compatible prepared search vectors. |
| Concepts ready to use | Defined concepts/properties have representation mappings. |
| Business rules met | Prepared instances satisfy supported constraints. |
| Facts supported by evidence | Facts carry source evidence. |

Each check displays its measured value and required threshold. Missing input can show insufficient data rather than failure. Follow the finding's link to fix the relevant data/concept/preparation issue, then rerun checks. Readiness preferences set thresholds; actual checks evaluate prepared inputs. Editing or source expiry can make prior checks stale.

## Approve and publish

Enter a change summary and request approval after checks pass. For the local demo, select **Demo reviewer** in the header to inspect changes and approve or request changes. These identities simulate roles; they are not real accounts.

Publish the approved revision. Published knowledge is read-only. To change it, open a new draft; the current release continues serving connected applications while you prepare and review its replacement. A failed publication does not replace the active release.

## Search and chat

Choose a product and version before searching. Published search uses an exact release snapshot; draft preview is labeled explicitly. Open evidence excerpts and original files to check the result. Graph/hybrid modes are optional ways to inspect connected information.

In **AI Chat**, ask a plain-language business question. You can request a summary, a table, or a fact card. The assistant streams its answer and attaches source evidence; selecting `S1`, `S2`, and other citations opens the matching source. Cards and tables are generated displays, so check them against the evidence before acting.

Preparation and a server model connection are required. An unavailable model produces an error rather than a fabricated success. **Clear** stops an answer in progress and starts a new conversation. Changing product/version also clears the conversation. Chat is session-local and does not archive conversations automatically.

## Refresh sources and connect applications

Import a changed database/API snapshot into an editable draft, then prepare/check/review/publish it. The prior draft source snapshot is superseded; earlier published data and original files remain intact.

In **Connected Apps**, register an association to a product. **Active** follows its newest active release; **Pinned** keeps a specific published release. Consumer usage displayed in this MVP is simulated. Use **Evidence Trail** and **Release Activity** to inspect lineage and publication history.
