# assistant-ui and Blume integration research

Research date: 2026-10-06. Scope: official documentation linked from the requested [assistant-ui Generative UI](https://www.assistant-ui.com/docs/tools/generative-ui) and [Blume quickstart](https://useblume.dev/docs/quickstart), their complete documentation indexes/corpora, and published npm package declarations/source. This note records research; it does not install dependencies or implement the product.

## Recommended integration for this application

The existing application is Vite 6 + React 19 + TypeScript, with FastAPI/Python owning knowledge-product retrieval, immutable release evidence, graph queries, and business actions. assistant-ui can render the conversational interface while FastAPI remains the backend. Its LocalRuntime adapter is the clearest route for native streamed text, tool calls, structured UI, cancellation, and later persistence. When another library already owns messages, ExternalStoreRuntime translates those messages instead. Neither route requires Next.js or Assistant Cloud. [Architecture](https://www.assistant-ui.com/docs/architecture), [runtime selection](https://www.assistant-ui.com/docs/runtimes/pick-a-runtime), [custom backend overview](https://www.assistant-ui.com/docs/runtimes/custom/overview).

Blume is an Astro documentation-site framework, rather than a general agent framework. However, its published `blume/hooks` entry includes a React `useAssistant` hook that can point at an externally owned text-stream endpoint. This creates two reasonable scopes:

1. **One text chat using both libraries:** let Blume own text-message state and streaming, and bridge it into assistant-ui ExternalStoreRuntime for the conversational UI. Attach separately fetched and validated product evidence/UI as application-owned state. This fits a chat whose structured facts are independently fetched, but cannot turn Blume's raw text stream into native tool events.
2. **Structured product assistant plus contextual help:** use assistant-ui LocalRuntime for the full product agent protocol; use Blume's assistant hook for a text-only help experience if a distinct help interaction is wanted. Avoid introducing an Astro site merely to obtain that hook.

A separate Blume site is useful when the actual desired deliverable is a searchable product handbook/API reference. It would be a separate package and process, with `blume.config.ts`, a docs content directory, and generated Astro runtime. Do not replace the existing Vite app's `dev`/`build` scripts with Blume CLI scripts. [Blume introduction](https://useblume.dev/docs), [quickstart](https://useblume.dev/docs/quickstart), [islands](https://useblume.dev/docs/content/islands), [deployment](https://useblume.dev/docs/deployment).

These recommendations are design inferences from the interfaces below, not promises that the integration has already passed this repository's build or browser tests.

## Verified published package surface

The npm `latest` metadata and package tarballs were fetched read-only; no package lifecycle scripts were run. Versions are point-in-time observations on the research date.

| Package | Verified version | Relevant compatibility/export |
| --- | --- | --- |
| `@assistant-ui/react` | `0.15.25` | React/React DOM `^18 || ^19` peers; root exports runtime providers, primitives, `useLocalRuntime`, `useExternalStoreRuntime`, `defineToolkit`, `Tools`, `AuiConfig` |
| `@assistant-ui/react-generative-ui` | `0.0.24` | React 18/19, assistant-ui React `^0.15.0`, and Zod `^4.0.0` peers; root browser/server conditions and `/ir`, `/a2ui`, `/slack`, `/teams` |
| `@assistant-ui/vite` | `0.0.20` | Vite `>=6` peer; exports `aui(options?)` with `backendless?: boolean` |
| `blume` | `2.1.3` | Node `>=22.12.0`; exports `./hooks` directly to TS source; direct React/React DOM dependencies `^19.3.0` |

Sources: [React package metadata](https://registry.npmjs.org/@assistant-ui%2freact/0.15.25), [Generative UI metadata](https://registry.npmjs.org/@assistant-ui%2freact-generative-ui/0.0.24), [Vite metadata](https://registry.npmjs.org/@assistant-ui%2fvite/0.0.20), [Blume metadata](https://registry.npmjs.org/blume/2.1.3).

`blume/hooks` exports `useAssistant`, `useBlume`, `usePage`, `useSearch`, and associated TypeScript types. **`AssistantProvider` and `createBlumeClient` are not Blume exports in this verified package.** The source was inspected directly in the npm tarball, including `src/components/islands/hooks.ts`; these names should not be invented. [Published hooks source](https://unpkg.com/blume@2.1.3/src/components/islands/hooks.ts), [published package manifest](https://unpkg.com/blume@2.1.3/package.json).

## assistant-ui runtime and protocol integration

### LocalRuntime and custom FastAPI transport

Implement `ChatModelAdapter.run` and pass it to `useLocalRuntime`. The input includes readonly thread messages, `abortSignal`, `context`, and run configuration; the return is either a result promise or an async generator. An async generator yields **the complete accumulated assistant content** on each iteration; each yield replaces the previous snapshot. Preserve previous tool calls across later text chunks. Forward `abortSignal` to `fetch`. [Model adapter reference](https://www.assistant-ui.com/docs/api-reference/adapters/model), [LocalRuntime](https://www.assistant-ui.com/docs/runtimes/custom/local-runtime).

A Python endpoint may emit JSON, NDJSON, or SSE; your adapter parses that chosen protocol and translates it into assistant-ui message parts. Using FastAPI does not imply that its raw stream already implements AI SDK's UI-message protocol. For a simple answer, return `{content:[{type:"text",text:answer}]}`. For incremental answers, accumulate text and yield that shape repeatedly. Handle non-2xx responses before reading answer text, and record interrupted/error status rather than displaying JSON error bodies as answers. [Custom backends](https://www.assistant-ui.com/docs/runtimes/custom/overview), [data-stream runtime](https://www.assistant-ui.com/docs/runtimes/custom/data-stream), [Assistant Transport](https://www.assistant-ui.com/docs/runtimes/custom/assistant-transport).

Native tool-call parts include `type:"tool-call"`, a stable `toolCallId`, `toolName`, arguments, and eventual result. Frontend tool schemas are available through the runtime context when tools are registered. A plain backend-owned toolkit entry can define `type:"backend"`, `display:"standalone"`, and `render`, with server execution/schema kept in Python. This avoids making a JavaScript backend a prerequisite. [Tool UI](https://www.assistant-ui.com/docs/tools/tool-ui), [defining tools](https://www.assistant-ui.com/docs/tools/defining-tools), [toolkit reference](https://www.assistant-ui.com/docs/api-reference/tools/toolkits).

### ExternalStoreRuntime and the Blume bridge

`useExternalStoreRuntime({messages,isRunning,convertMessage,onNew})` bridges external state. `convertMessage` returns assistant-ui's `ThreadMessageLike`; mapping a Blume message to `{role,content:[{type:"text",text:content}]}` is sufficient for text. Set `isRunning` from Blume `loading`, and have `onNew` collect text parts then call `ask`. Provide stable message IDs using the Blume thread ID plus turn index, since Blume messages do not carry IDs. This bridge is inferred from both documented interfaces and still needs integration tests. [ExternalStoreRuntime](https://www.assistant-ui.com/docs/runtimes/custom/external-store), [external-store reference](https://www.assistant-ui.com/docs/api-reference/external-store/runtime), [Blume hooks source](https://unpkg.com/blume@2.1.3/src/components/islands/hooks.ts).

ExternalStoreRuntime enables capabilities only when their handlers are supplied. `onEdit`, `onReload`, `setMessages`, `onCancel`, and tool-result handlers must actually implement the matching behavior. Blume supplies only `ask` and `reset`; reset aborts **and clears** the conversation. Do not expose an assistant-ui stop button that silently clears history or editing/regeneration buttons that cannot update Blume state. [External store handler matrix](https://www.assistant-ui.com/docs/runtimes/custom/external-store#handler-matrix).

### Persistence, attachments, and optional services

Conversation persistence is an adapter concern, not automatic FastAPI storage. LocalRuntime supports standard persistence/thread adapters; ExternalStoreRuntime requires the state owner to persist. Assistant Cloud is optional hosted infrastructure, with separate identities, storage, and reporting; it is unnecessary for a local knowledge-product release system. [Runtime adapters](https://www.assistant-ui.com/docs/runtimes/concepts/adapters), [threads](https://www.assistant-ui.com/docs/runtimes/concepts/threads), [persistence API](https://www.assistant-ui.com/docs/api-reference/adapters/persistence), [cloud local runtime](https://www.assistant-ui.com/docs/cloud/local-runtime).

Attachments require their own adapter and backend ingestion, even when chat primitives render attachment chips. Product originals already managed by MinIO should be referenced by server-owned identifiers rather than duplicated into a hosted attachment service by accident. [Attachment guide](https://www.assistant-ui.com/docs/guides/attachments), [attachment adapter reference](https://www.assistant-ui.com/docs/api-reference/adapters/attachments).

## The distinct generative UI APIs

### Model-composed `present` tool

The requested guide uses `JSONGenerativeUI` from `@assistant-ui/react-generative-ui`, with a component library and optional action registry. `generative.present({display:"standalone"})` produces a frontend tool. `generative.promptUser()` produces a human-input tool. The shipped default vocabulary contains 29 components. Its nodes are flat JSON objects such as `{ "$type":"Fact", "label":"Evidence", "value":"7 sources" }`, with `children` for nesting; `$key`, `$action`, and `$status` are framework fields. [Generative UI guide](https://www.assistant-ui.com/docs/tools/generative-ui), [JSONGenerativeUI API](https://www.assistant-ui.com/docs/api-reference/generative-ui/json-generative-ui), [component API](https://www.assistant-ui.com/docs/api-reference/generative-ui/components).

The default library renders unstyled semantic HTML carrying `data-aui` attributes. A registry-installed stylesheet/theme and markdown override supply the shipped appearance; without them, use the app's CSS and a real markdown renderer. Stock default `Markdown` renders its source as plain text. Prefer a small business-domain vocabulary—evidence list, product readiness, definition preview, suggested field mapping, query table—when broad layout generation would obscure verified evidence. [Vocabulary reference](https://www.assistant-ui.com/elements/vocabulary), [generative UI styling](https://www.assistant-ui.com/docs/tools/generative-ui#styling).

The AI SDK example's automatic send condition and backend step budget allow the frontend tool result to return before the model continues. A custom Python adapter must implement its own corresponding result/continuation behavior; copying the `present` renderer alone does not create a tool loop. [AI SDK v7 runtime](https://www.assistant-ui.com/docs/runtimes/ai-sdk/v7), [backend tools](https://www.assistant-ui.com/docs/tools/backend), [JSONGenerativeUI API](https://www.assistant-ui.com/docs/api-reference/generative-ui/json-generative-ui).

### Compiler-only helpers and plain runtime rendering

`defineGenerativeComponents` is a compiler authoring helper with **no runtime implementation**: it throws when reached outside a compiled `"use generative"` module. Vite uses `aui()` from `@assistant-ui/vite`. With no JavaScript backend importing server schema builds—as in this Python application—the verified plugin options include `aui({backendless:true})` to retain client-uploadable schemas. Verify this option against the actual backend's schema handling; it does not implement Python transport. [Components API](https://www.assistant-ui.com/docs/api-reference/generative-ui/components), [Vite declaration](https://unpkg.com/@assistant-ui/vite@0.0.20/dist/index.d.ts).

For direct server-delivered JSON artifacts, use a **plain typed `GenerativeUILibrary` literal** (or the default library) and `renderGenerativeUI(node,library,{status:"done",dispatch})`; no compiler-only authoring helper is needed on this route. A component entry contains `description`, Zod `properties`, and `render`. `streamProperties:true` widens streaming props to partial values; otherwise components wait for complete props. `buildPresentParameters(library)` exports the model-facing JSON schema if an integration needs it. [Rendering API](https://www.assistant-ui.com/docs/api-reference/generative-ui/rendering), [published declarations](https://unpkg.com/@assistant-ui/react-generative-ui@0.0.24/dist/index.shared.d.ts), [component types](https://unpkg.com/@assistant-ui/react-generative-ui@0.0.24/dist/types.d.ts).

`createActionRegistry({actionType:handler})` routes model-produced `$action.type`; handlers receive `{payload}` and controls merge submitted values under `$input`. No registry means actions do nothing. A `prompt_user` can finish through a handler result, whereas `present` actions do not generate tool results. Business write operations should call the existing authenticated/validated server action, respecting current revision state, rather than treating a rendered button as business authorization. [Action API](https://www.assistant-ui.com/docs/api-reference/generative-ui/actions).

### Native `MessagePrimitive.GenerativeUI`

This is a different backend-driven API. A native part is `{type:"generative-ui",spec:{root:{component:"Evidence",props:{...},children:[...]}}}`. The `component/props/root` spec is **not** the flat `$type` present-tree format. Explicitly render the primitive with a component allowlist, or configure `MessagePrimitive.Parts` with its `generativeUI` renderer. The stock Thread does not display these native parts automatically. Unknown component names throw a typed render error unless a fallback is supplied. Props need separate validation; the allowlist does not validate them. [Generative UI primitive](https://www.assistant-ui.com/docs/tools/generative-ui-primitive), [spec API](https://www.assistant-ui.com/docs/api-reference/generative-ui/spec).

For known backend operations, toolkit tool UI is usually simpler than freely generated layout. For stateful editable artifacts, the current interactables API is explicitly `unstable_` and requires state snapshots plus persistence semantics; do not introduce it casually for read-only evidence. AG-UI/A2UI, LangGraph UI, OpenUI, MCP apps, and Slack/Teams converters solve distinct protocol/surface problems and are unnecessary for the initial Vite/FastAPI implementation. [Interactables](https://www.assistant-ui.com/docs/tools/interactables), [A2UI](https://www.assistant-ui.com/docs/tools/a2ui), [LangGraph UI](https://www.assistant-ui.com/docs/runtimes/langgraph/generative-ui), [MCP apps](https://www.assistant-ui.com/docs/tools/mcp-apps).

## Blume's reusable assistant hook and actual limits

The package source verifies this shape:

```ts
import { useAssistant } from "blume/hooks";

const { ask, messages, loading, reset, thread } = useAssistant({
  endpoint: "/api/product-assistant/ask",
  errorMessage: "The answer could not be completed. Please try again.",
});
```

`UseAssistantOptions` contains optional `endpoint`, `errorMessage`, `rateLimitMessage`, `verifyMessage`, and `captcha`. Return messages are `{role:"user"|"assistant",content:string}`. `ask(question)` returns `Promise<void>`. There is no callback for tool events, no message setter, no stop-only function, and no custom `fetch`, request-header, or authorization-header option in this verified version. [Versioned hook source](https://unpkg.com/blume@2.1.3/src/components/islands/hooks.ts).

The hook sends `POST` JSON with `messages`, `page:{path}`, and optionally `captcha`. It derives `page.path` from the current browser path minus Vite's base URL, reads response bytes with a streaming `TextDecoder`, and appends them to the assistant message. Endpoint selection is explicit and does **not** depend on the generated layout snapshot. `useBlume` and `usePage`, separately, read `#blume-client-data`; they are unavailable without that snapshot. [Published hook source](https://unpkg.com/blume@2.1.3/src/components/islands/hooks.ts), [islands/hooks documentation](https://useblume.dev/docs/content/islands#hooks).

The endpoint must return successful **plain UTF-8 text**, not SSE event records or NDJSON; those encodings would appear verbatim in the answer. The hook trims sent history to at most 40 messages/24,000 JSON characters, creates a thread identifier for local analytics/support, guards stale streams, and reset aborts and clears state. It does not send its `thread` field in the request body. If a product route must identify context, encode a validated product ID in the endpoint path or route context, rather than assuming an extensible payload field exists. [External endpoint contract](https://useblume.dev/docs/configuration/assistant#external-endpoint), [published limits](https://unpkg.com/blume@2.1.3/src/ai/ask-limits.ts), [hook source](https://unpkg.com/blume@2.1.3/src/components/islands/hooks.ts).

### Vite integration risks to verify

- `blume/hooks` also contains `useSearch`'s dynamic `import("blume:search-client")`. That virtual module is generated by Blume, and plain Vite may still resolve it even when only `useAssistant` is imported. A project-level Vite alias/virtual-module adapter or a maintained package change may be needed. Treat this as a source-detected integration risk, not an observed build failure. [Hooks source](https://unpkg.com/blume@2.1.3/src/components/islands/hooks.ts).
- Blume directly depends on React/React DOM `^19.3.0`; the existing application requests `^19.1.0`. Inspect the resolved lock versions and deduplicate React/React DOM, including Vite `resolve.dedupe` if necessary, before calling a hook across packages. A nested second React runtime can cause invalid-hook failures. [Blume manifest](https://unpkg.com/blume@2.1.3/package.json), [React invalid hook guidance](https://react.dev/warnings/invalid-hook-call-warning).
- The Blume dependency includes Astro, AI SDK, markdown tooling, generators, and adapters. Importing a small hook does not make the npm installation a small standalone chat library. Node's minimum is also stricter than this repository's documented Node 20 baseline. [Versioned package manifest](https://unpkg.com/blume@2.1.3/package.json).
- The hook's analytics helper calls only already-present provider globals and emits `blume:track`; reading source does not show it installing analytics providers. The package does import `@vercel/analytics`. Review actual bundle behavior if that helper is included. [Analytics client source](https://unpkg.com/blume@2.1.3/src/components/layout/analytics-client.ts).

### Generated Blume assistant versus externally owned backend

A generated Blume assistant endpoint can ground answers in a build-time docs snapshot and expose server-only `search_docs`/`read_page` tools. Provider adapters are descriptors from `blume/ai`; direct providers/compatible gateways use configured environment-variable names. Enabling that built-in endpoint requires server output with a host adapter. An external endpoint instead leaves retrieval, model access, citations, authorization, and limits to the caller's backend, allowing the docs site itself to remain static. [Assistant configuration](https://useblume.dev/docs/configuration/assistant), [AI adapter declarations](https://unpkg.com/blume@2.1.3/dist/types/ai/index.d.ts), [deployment](https://useblume.dev/docs/deployment).

Blume's default docs retrieval is lexical Orama against its documentation snapshot, not this product's pgvector/graph/release evidence. Reusing the hook with a FastAPI endpoint does not import that docs retrieval behavior. The server must return grounded answer text and ordinary safe Markdown citation links itself. [Search configuration](https://useblume.dev/docs/configuration/search), [docs JSON API](https://useblume.dev/docs/discoverability/json-api), [MCP docs server](https://useblume.dev/docs/discoverability/mcp).

## Implementation checks implied by the research

1. Verify package import compilation in this repository, duplicate React resolution, and any Blume virtual-module adaptation before UI work depends on the hook.
2. Decide whether the primary chat protocol is native structured agent events or Blume plain text; define the FastAPI response contract accordingly.
3. Keep retrieval product/revision/release-scoped and cite actual stored evidence. Do not present docs search as knowledge-product retrieval.
4. Validate model-produced component names/props/URLs against a small shipped vocabulary. Neither renderer should execute model-produced JavaScript, HTML, or arbitrary imports.
5. Keep query/read tools separate from confirmed product mutations. The server remains authoritative for review, approval, publication, and data ingestion.
6. Verify empty answers, missing model configuration, invalid requests, provider errors, cancellation/reset, changes of product scope, safe links, and correct persistence behavior using the selected runtime's real capabilities.

## Documentation coverage and limitations

Both official full-text corpora were downloaded successfully over HTTPS with `curl`. The browser research tool returned internal errors for their full-text URLs; local Python's default SSL certificate store also rejected the domains. System `curl` verified HTTPS and succeeded without disabling certificate validation. The mistaken URL `/docs/runtimes/custom/local` returned 404; the canonical page is `/docs/runtimes/custom/local-runtime`. Several API-reference HTML pages were inaccessible through the research browser tool but were present in the complete assistant-ui text corpus.

assistant-ui: **508 unique corpus entries**, including **337 documentation pages** and **171 additional elements/design/example entries**. Every one of the 337 documentation URLs in its index matched a corpus entry. Blume: **356 corpus entries**, matching its JSON API's `count:356`/`generator:"blume@2.1.3"`; this comprises **63 English docs + 252 translations (63 each in German, Hindi, Japanese, Portuguese) + 41 changelogs**. The additional Blume index link `/api/docs/pages.json` is a discovery endpoint, not a missing documentation page; it was fetched separately. [assistant-ui index](https://www.assistant-ui.com/llms.txt), [assistant-ui full corpus](https://www.assistant-ui.com/llms-full.txt), [Blume index](https://useblume.dev/llms.txt), [Blume full corpus](https://useblume.dev/llms-full.txt), [Blume JSON page inventory](https://useblume.dev/api/docs/pages.json).

Coverage means complete corpus retrieval, URL reconciliation, per-page heading inventory, and detailed reading of integration-relevant material. It does **not** mean every sentence of every translated page, cloud API entry, or unrelated platform/example was examined equally deeply. Translation copies were inventoried rather than interpreted as distinct API specifications. The appendices expose exactly the covered documentation URLs and topic inventory. No inaccessible indexed documentation page was silently claimed as read. Site content and npm latest may change after the research date; versions were verified, but no dependency install, compilation, backend call, model call, or browser interaction was performed by this research task.

### Retrieved corpus fingerprints

| Corpus | UTF-8 bytes | SHA-256 |
| --- | ---: | --- |
| assistant | 4,985,710 | `8ac4e197ec6acab8dba5ce51a1747ce3df5a88ea1e55133ff0e18d8d896cb9a5` |
| blume | 4,435,262 | `52895360b8729ecd997e46174ab4b8a5fd7f405fbab95ce64a20547e350c33bb` |

## Appendix A: all assistant-ui documentation pages

All 337 pages below were present in the retrieved official corpus. Each entry shows its canonical topic and up to five section labels as an inventory, rather than suggesting equal depth of review.

### architecture (1)

- [Architecture](https://www.assistant-ui.com/docs/architecture) — assistant-ui is built on these main pillars:; 1. Frontend components; 2. Runtime; 3. Assistant Cloud; What each layer owns

### root (1)

- [Overview](https://www.assistant-ui.com/docs) — Pick a surface; Bring your own backend; Everything else

### llm (1)

- [Agent Skills](https://www.assistant-ui.com/docs/llm) — AI Accessible Documentation; Context Files; assistant-ui; Skills; MCP

### base-ui (1)

- [Radix UI and Base UI](https://www.assistant-ui.com/docs/base-ui) — Component registry; How compatibility works; Behavior notes; FAQ

### cli (1)

- [CLI](https://www.assistant-ui.com/docs/cli) — init; create; cloud; add; update

### devtools (1)

- [DevTools](https://www.assistant-ui.com/docs/devtools) — Setup; Custom tabs

### installation (1)

- [Installation](https://www.assistant-ui.com/docs/installation) — Quick Start; Manual Setup; What's Next?

### rtl (1)

- [RTL Support](https://www.assistant-ui.com/docs/rtl) — Setup; 1. Install the `direction` component; 2. Set `dir` on your root element; 3. Wrap your app with `DirectionProvider`; How it works

### api-reference (85)

- [Attachment Adapters](https://www.assistant-ui.com/docs/api-reference/adapters/attachments) — API Reference; AttachmentAdapter; CloudFileAttachmentAdapter; CompositeAttachmentAdapter; SimpleImageAttachmentAdapter
- [Feedback Adapter](https://www.assistant-ui.com/docs/api-reference/adapters/feedback) — API Reference; FeedbackAdapter
- [Adapters API Reference](https://www.assistant-ui.com/docs/api-reference/adapters) — Pages
- [Model Adapters](https://www.assistant-ui.com/docs/api-reference/adapters/model) — API Reference; ChatModelAdapter; ChatModelRunOptions; ChatModelRunResult; ChatModelRunUpdate
- [Persistence Adapters](https://www.assistant-ui.com/docs/api-reference/adapters/persistence) — API Reference; ExportedMessageRepository; GenericThreadHistoryAdapter; InMemoryThreadListAdapter; MessageFormatAdapter
- [Runtime Adapter Context](https://www.assistant-ui.com/docs/api-reference/adapters/runtime) — API Reference; RuntimeAdapters
- [Suggestion Adapters](https://www.assistant-ui.com/docs/api-reference/adapters/suggestions) — API Reference; createSuggestionAdapter; SuggestionAdapter
- [AssistantRuntimeProvider](https://www.assistant-ui.com/docs/api-reference/context-providers/assistant-runtime-provider) — API Reference; AssistantRuntimeProvider; AuiProvider
- [Context Providers API Reference](https://www.assistant-ui.com/docs/api-reference/context-providers) — Pages
- [Scoped Providers](https://www.assistant-ui.com/docs/api-reference/context-providers/scoped-providers) — API Reference; ChainOfThoughtByIndicesProvider; ChainOfThoughtPartByIndexProvider; ComposerAttachmentByIndexProvider; MessageAttachmentByIndexProvider
- [External Store API Reference](https://www.assistant-ui.com/docs/api-reference/external-store) — Pages
- [Message Conversion](https://www.assistant-ui.com/docs/api-reference/external-store/message-conversion) — API Reference; getExternalStoreMessages; unstable_convertExternalMessages; unstable_createExternalMessageConversionCache; unstable_createMessageConverter
- [External Store Runtime](https://www.assistant-ui.com/docs/api-reference/external-store/runtime) — API Reference; ExternalStoreAdapter; ExternalThread; ExternalThreadProps; ExternalThreadQueueAdapter
- [A2UI](https://www.assistant-ui.com/docs/api-reference/generative-ui/a2ui) — API Reference; A2uiOperation; A2uiOperationResult; A2uiState; A2uiSurfaceState
- [Generative UI Actions](https://www.assistant-ui.com/docs/api-reference/generative-ui/actions) — API Reference; ActionDispatchContext; ActionHandler; ActionRegistry; createActionRegistry
- [Generative UI Components](https://www.assistant-ui.com/docs/api-reference/generative-ui/components) — API Reference; defaultGenerativeUILibrary; defineGenerativeComponents; GenerativeUIComponent; GenerativeUILibrary
- [Generative UI API Reference](https://www.assistant-ui.com/docs/api-reference/generative-ui) — Pages
- [JSONGenerativeUI](https://www.assistant-ui.com/docs/api-reference/generative-ui/json-generative-ui) — API Reference; JSONGenerativeUI; JSONGenerativeUIOptions; PresentToolOptions
- [Generative UI Rendering](https://www.assistant-ui.com/docs/api-reference/generative-ui/rendering) — API Reference; buildPresentParameters; GenerativeUIRender; GenerativeUIRenderContext; GenerativeUIRenderError
- [Slack Block Kit](https://www.assistant-ui.com/docs/api-reference/generative-ui/slack) — API Reference; decodeBlockAction; fromSlackBlocks; FromSlackBlocksResult; SlackBlocksResult
- [Generative UI Spec](https://www.assistant-ui.com/docs/api-reference/generative-ui/spec) — API Reference; GenerativeUIMessagePart; GenerativeUINode; GenerativeUISpec
- [Microsoft Teams](https://www.assistant-ui.com/docs/api-reference/generative-ui/teams) — API Reference; AdaptiveCardResult; decodeSubmitData; TeamsAttachmentsResult; TeamsConversionWarning
- [Generative UI Tokens](https://www.assistant-ui.com/docs/api-reference/generative-ui/tokens) — API Reference; ALERT_TONES; ALIGNS; BUTTON_STYLES; COLORS
- [Composer Trigger Hooks](https://www.assistant-ui.com/docs/api-reference/hooks/composer-triggers) — API Reference; unstable_useTriggerPopoverRootContext; unstable_useTriggerPopoverRootContextOptional; unstable_useTriggerPopoverScopeContext; unstable_useTriggerPopoverScopeContextOptional
- [Hooks API Reference](https://www.assistant-ui.com/docs/api-reference/hooks) — Pages
- [Model Context Hooks](https://www.assistant-ui.com/docs/api-reference/hooks/model-context) — API Reference; useAuiToolOverrides
- [Primitive Hooks](https://www.assistant-ui.com/docs/api-reference/hooks/primitives) — API Reference; useCloudThreadListAdapter; useMessageQuote; useMessageTiming; useRuntimeAdapters
- [Runtime Hooks](https://www.assistant-ui.com/docs/api-reference/hooks/runtimes) — API Reference; useCloudThreadListRuntime; useLocalRuntime; useRemoteThreadListRuntime
- [State Hooks](https://www.assistant-ui.com/docs/api-reference/hooks/state) — API Reference; useAui; useAuiEvent; useAuiState
- [@assistant-ui/ai-sdk](https://www.assistant-ui.com/docs/api-reference/integrations/ai-sdk) — API Reference; AISDKChat; AISDKThreads; AISDKToolkit; AssistantChatTransport
- [assistant-cloud/ai-sdk](https://www.assistant-ui.com/docs/api-reference/integrations/assistant-cloud-ai-sdk) — API Reference; aiSDKV6FormatAdapter; extractAISDKRunTelemetry
- [assistant-cloud/telemetry](https://www.assistant-ui.com/docs/api-reference/integrations/assistant-cloud-telemetry) — API Reference; assistantCloudTraceExportOptions; assistantCloudTraceMetadata; createAssistantCloudSpanProcessor; createAssistantCloudTraceExporter
- [assistant-cloud](https://www.assistant-ui.com/docs/api-reference/integrations/assistant-cloud) — The client; Building an integration; API Reference; AssistantCloud; AssistantCloudEvents
- [@assistant-ui/eve](https://www.assistant-ui.com/docs/api-reference/integrations/eve) — API Reference; convertEveMessage; convertEveMessages; getEveMessageContent; toEveInputResponse
- [Integrations API Reference](https://www.assistant-ui.com/docs/api-reference/integrations) — Pages
- [@assistant-ui/react-data-stream](https://www.assistant-ui.com/docs/api-reference/integrations/react-data-stream) — API Reference; useCloudRuntime; useDataStreamRuntime; toLanguageModelMessages
- [Model Context](https://www.assistant-ui.com/docs/api-reference/model-context/context) — API Reference; makeAssistantVisible; mergeModelContexts; ModelContextClient; ModelContextProvider
- [Model Context API Reference](https://www.assistant-ui.com/docs/api-reference/model-context) — Pages
- [Model Context Registry](https://www.assistant-ui.com/docs/api-reference/model-context/registry) — API Reference; ModelContextRegistry
- [API Reference](https://www.assistant-ui.com/docs/api-reference/overview) — Start Here; Highest Level Context Providers; Assistant Context; AssistantRuntime; Instructions
- [ActionBarMorePrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/action-bar-more) — Anatomy; API Reference; Root; Trigger; Content
- [ActionBarPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/action-bar) — Anatomy; API Reference; Root; Copy; Reload
- [AuiIf](https://www.assistant-ui.com/docs/api-reference/primitives/assistant-if) — Anatomy; Overview; AssistantState; Examples; Thread State Conditions
- [AssistantModalPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/assistant-modal) — Anatomy; API Reference; Root; Trigger; Content
- [AttachmentPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/attachment) — Anatomy; API Reference; Root; Name; Remove
- [BranchPickerPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/branch-picker) — Anatomy; API Reference; Root; Next; Previous
- [ChainOfThoughtPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/chain-of-thought) — API Reference; Root; AccordionTrigger; Parts
- [ComposerPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/composer) — Anatomy; API Reference; Root; Input; Send
- [Composition](https://www.assistant-ui.com/docs/api-reference/primitives/composition)
- [ErrorPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/error) — Anatomy; API Reference; Root; Message
- [Primitives API Reference](https://www.assistant-ui.com/docs/api-reference/primitives) — Pages
- [MessagePartPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/message-part) — Anatomy; API Reference; Text; Image; InProgress
- [MessagePrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/message) — Anatomy; API Reference; Root; Parts; PartByIndex
- [QueueItemPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/queue-item) — API Reference; Text; Steer; Remove
- [SelectionToolbarPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/selection-toolbar) — Anatomy; API Reference; Root; Quote
- [SuggestionPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/suggestion) — API Reference; Title; Description; Trigger
- [ThreadListItemMorePrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/thread-list-item-more) — Anatomy; API Reference; Root; Trigger; Content
- [ThreadListItemPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/thread-list-item) — Anatomy; API Reference; Root; Archive; Unarchive
- [ThreadListPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/thread-list) — Anatomy; API Reference; Root; New; Items
- [ThreadPrimitive](https://www.assistant-ui.com/docs/api-reference/primitives/thread) — Anatomy; API Reference; Root; Empty; If
- [AssistantRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/assistant-runtime) — API Reference; AssistantRuntime
- [AttachmentRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/attachment-runtime) — API Reference; AttachmentRuntime; AttachmentRuntimeState; AttachmentState
- [ComposerRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/composer-runtime) — API Reference; ComposerRuntime; ComposerRuntimeState; EditComposerRuntime; EditComposerState
- [Runtime State API Reference](https://www.assistant-ui.com/docs/api-reference/runtimes) — Pages
- [MessagePartRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/message-part-runtime) — API Reference; EnrichedPartState; MessagePartRuntime; MessagePartState; PartState
- [MessageRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/message-runtime) — API Reference; MessageRuntime; MessageRuntimeState; MessageState
- [QueueItemState](https://www.assistant-ui.com/docs/api-reference/runtimes/queue-state) — API Reference; QueueItemState
- [ThreadListItemRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/thread-list-item-runtime) — API Reference; ThreadListItemRuntime; ThreadListItemRuntimeState; ThreadListItemState
- [ThreadListRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/thread-list-runtime) — API Reference; ThreadListRuntime; ThreadListState
- [ThreadRuntime](https://www.assistant-ui.com/docs/api-reference/runtimes/thread-runtime) — API Reference; ThreadComposerRuntime; ThreadComposerState; ThreadRuntime; ThreadRuntimeState
- [Component Tools](https://www.assistant-ui.com/docs/api-reference/tools/component-tools) — API Reference; makeAssistantTool; useAssistantTool
- [Tools API Reference](https://www.assistant-ui.com/docs/api-reference/tools) — Pages
- [Interactables (legacy)](https://www.assistant-ui.com/docs/api-reference/tools/interactables-legacy) — API Reference; Interactables; useAssistantInteractable; useInteractableState
- [Interactables](https://www.assistant-ui.com/docs/api-reference/tools/interactables) — API Reference; unstable_Interactables; unstable_useInteractable; unstable_useInteractableState; unstable_useInteractableVersions
- [Tool Rendering](https://www.assistant-ui.com/docs/api-reference/tools/rendering) — API Reference; DataRenderers; getMcpAppFromToolPart; makeAssistantDataUI; McpAppRenderer
- [Tool Status](https://www.assistant-ui.com/docs/api-reference/tools/status) — API Reference; useToolArgsStatus; useToolCallElapsed
- [Toolkits](https://www.assistant-ui.com/docs/api-reference/tools/toolkits) — API Reference; tool; ToolDefinition; Toolkit; Tools
- [Assistant Transport](https://www.assistant-ui.com/docs/api-reference/transport/assistant-transport) — API Reference; AssistantTransportCommand; AssistantTransportConnectionMetadata; AssistantTransportProtocol; SendCommandsRequestBody
- [Assistant Frame](https://www.assistant-ui.com/docs/api-reference/transport/frame) — API Reference; AssistantFrameHost; AssistantFrameProvider; FRAME_MESSAGE_CHANNEL; FrameMessage
- [Transport API Reference](https://www.assistant-ui.com/docs/api-reference/transport) — Pages
- [Utilities API Reference](https://www.assistant-ui.com/docs/api-reference/utilities) — Pages
- [Utilities](https://www.assistant-ui.com/docs/api-reference/utilities/miscellaneous) — API Reference; AssistantCloud; AuiConfig; ChainOfThoughtClient; CloudRendererHost
- [Voice API Reference](https://www.assistant-ui.com/docs/api-reference/voice) — Pages
- [Voice Sessions](https://www.assistant-ui.com/docs/api-reference/voice/session) — API Reference; createVoiceSession; RealtimeVoiceAdapter; useVoiceControls; useVoiceState
- [Speech and Dictation](https://www.assistant-ui.com/docs/api-reference/voice/speech-dictation) — API Reference; DictationAdapter; DictationState; SpeechSynthesisAdapter; WebSpeechDictationAdapter

### cloud (63)

- [Allowed origins](https://www.assistant-ui.com/docs/cloud/allowed-origins) — How the browser check works; Wildcards match subdomains, not the base domain; Configure allowed origins; Recipes; Preview deployments
- [Anonymous sessions](https://www.assistant-ui.com/docs/cloud/anonymous-sessions) — How an anonymous session works; Letting a runtime create the client; Configure anonymous access; From your code; Costs and limits
- [API keys](https://www.assistant-ui.com/docs/cloud/api-keys) — How API keys authenticate a request; Create and manage a key; What a key can call; From your code; Request refusals
- [Auth providers](https://www.assistant-ui.com/docs/cloud/auth-providers) — How a rule accepts a token; Configure an auth rule; Exchange provider tokens in the browser; From your code; Mint a token on your server
- [Authentication](https://www.assistant-ui.com/docs/cloud/authorization) — Choose a client mode; What happens to a request; Users and workspaces; Authentication errors
- [Users and workspaces](https://www.assistant-ui.com/docs/cloud/users-and-workspaces) — Identity and thread ownership; What the dashboard shows; Active users and the monthly limit; Erase a user through the API; Troubleshooting
- [Attachments](https://www.assistant-ui.com/docs/cloud/attachments) — How an attachment moves through the composer; Accepted files and storage; What the dashboard shows; From your code; Events, costs, and limits
- [Messages](https://www.assistant-ui.com/docs/cloud/messages) — How messages form a tree; Stored formats and read conversion; Configure persistence; What the thread view shows; From your code
- [Retention](https://www.assistant-ui.com/docs/cloud/retention) — What retention removes; Configure retention; Shortening a window; Who can change it and what is recorded; What the hourly pass can process
- [Thread titles](https://www.assistant-ui.com/docs/cloud/thread-titles) — How a thread gets its title; What the model reads; The model call; One title per thread; When the title reaches your app
- [Threads](https://www.assistant-ui.com/docs/cloud/threads) — How a thread is created and loaded; Loading the thread list; Configure the thread list; What the dashboard shows; From your code
- [Assistants](https://www.assistant-ui.com/docs/cloud/assistants) — How it works; Configure; What the page shows; From your code; Costs and limits
- [Evaluators](https://www.assistant-ui.com/docs/cloud/evaluators) — Configure evaluator rules; Manage verdicts; Where verdicts appear; Troubleshooting
- [Harnesses](https://www.assistant-ui.com/docs/cloud/harnesses) — How it works; Configure; What the page shows; Costs and limits; Observe runs and conversations
- [Intelligence](https://www.assistant-ui.com/docs/cloud/intelligence) — What Intelligence produces; Skills; How a pass runs; Configure; What the pages show
- [LLM providers](https://www.assistant-ui.com/docs/cloud/llm-providers) — How providers are used; Provider list and pages; Configure a provider; Form rules; How model discovery works
- [AI SDK](https://www.assistant-ui.com/docs/cloud/ai-sdk) — What you get; Setup; Cloud options; Control reports and events; Persist and report a run
- [Custom thread list](https://www.assistant-ui.com/docs/cloud/custom-thread-list) — Wrap a per-thread runtime; Use the adapter directly; What the adapter calls; Use AG-UI or A2A; Persist another message format
- [LangGraph, LangChain and ADK](https://www.assistant-ui.com/docs/cloud/langgraph) — What the cloud adds; Connect your backend; Choose one thread-list owner; Give the first thread a title; Fill Runs and Models with traces
- [Local runtime](https://www.assistant-ui.com/docs/cloud/local-runtime) — Setup; What the cloud adds; Store local messages as `aui/v0`; Report a local run; Compose the thread list yourself
- [Migrate from Cloud AI SDK](https://www.assistant-ui.com/docs/cloud/migrate-cloud-ai-sdk) — The assistant-ui runtime; The client on its own
- [Which runtime](https://www.assistant-ui.com/docs/cloud/runtimes) — The matrix; What decides the column; The three platforms; Choosing
- [Servers and bots](https://www.assistant-ui.com/docs/cloud/servers) — Create the API key client; Store one bot conversation; Create or find the thread; Store the user's message; Store the assistant's reply
- [Stored message formats](https://www.assistant-ui.com/docs/cloud/formats) — The stored formats; The `aui/v0` shape; Message fields; Message parts; Attachments and metadata
- [Limits](https://www.assistant-ui.com/docs/cloud/limits) — Rate limits; Request sizes; List pages; Time; Per project
- [The assistant-cloud client](https://www.assistant-ui.com/docs/cloud/sdk) — Package and entry points; Construct the client; Configure telemetry; Choose authentication; Identify the SDK and send requests
- [Engagement events](https://www.assistant-ui.com/docs/cloud/engagement) — How events are recorded; Delivery, validation, and storage; What the dashboard derives; What the Engagement page shows; From your code
- [Run reports](https://www.assistant-ui.com/docs/cloud/run-reports) — What a report accepts; Step fields; Tool call fields; Attributes and size limits; How the SDK builds a report
- [Feedback and scores](https://www.assistant-ui.com/docs/cloud/scores) — Message feedback; Collecting a comment in a custom thread; When a feedback click is skipped; Write a score; Source, author, and replacement
- [Traces](https://www.assistant-ui.com/docs/cloud/traces) — Set up the AI SDK exporter; The trace receiver; How spans become runs; Attributes the receiver reads; Stable ids and reexports
- [Auth tokens](https://www.assistant-ui.com/docs/cloud/api/auth-tokens) — The token response; Mint a backend access token; Start an anonymous session; Refresh an anonymous session
- [Events](https://www.assistant-ui.com/docs/cloud/api/events) — The event object; Create events
- [Files](https://www.assistant-ui.com/docs/cloud/api/files) — Generate an upload URL; Generate a download URL
- [Conventions](https://www.assistant-ui.com/docs/cloud/api) — Hosts and credentials; Headers; Send a request; Ids, time and paging; Errors
- [MCP](https://www.assistant-ui.com/docs/cloud/api/mcp) — The MCP endpoint; `list_runs`; `get_run`; `usage_daily`; `usage_period`
- [Messages](https://www.assistant-ui.com/docs/cloud/api/messages) — The message object; Create a message; List messages; Delete messages; Update a message
- [Project read API](https://www.assistant-ui.com/docs/cloud/api/project) — The project run object; The project span object; List project runs; Get a project run; Get daily project usage
- [Runs](https://www.assistant-ui.com/docs/cloud/api/runs) — The run result; Record a run; Tool calls; Sampling calls; Steps
- [Scores](https://www.assistant-ui.com/docs/cloud/api/scores) — The score object; Create a score; Message feedback
- [Threads](https://www.assistant-ui.com/docs/cloud/api/threads) — The thread object; Create a thread; List threads; Get a thread; Update a thread
- [Traces](https://www.assistant-ui.com/docs/cloud/api/traces) — Export traces; Span mapping; Receiver attributes; Limits and identifiers; Re export and client reports
- [Users](https://www.assistant-ui.com/docs/cloud/api/users) — Delete a project user; Erasure order; Audit entry
- [Concepts](https://www.assistant-ui.com/docs/cloud/concepts) — The project and its two hosts; Users and workspaces; Threads and messages; Runs and spans; Events and scores
- [Conversation views](https://www.assistant-ui.com/docs/cloud/dashboard/conversation-views) — What Structured draws; What each runtime stores; Show a conversation as your users saw it
- [Engagement page](https://www.assistant-ui.com/docs/cloud/dashboard/engagement) — Feedback; What the page answers; Conversation funnel; Satisfaction; Interaction mix
- [Exports](https://www.assistant-ui.com/docs/cloud/dashboard/exports) — Choose what to export; Pick a file format; Fields in each export; Runs; Threads
- [Using the dashboard](https://www.assistant-ui.com/docs/cloud/dashboard) — The pages; Ranges and buckets; Filters, sorting and paging; Time; Roles
- [Intelligence page](https://www.assistant-ui.com/docs/cloud/dashboard/intelligence) — What the page answers; The six tiles; Reading the Topics pivot; Tasks, questions, and judged outcomes; Follow a figure to the conversations
- [Models page](https://www.assistant-ui.com/docs/cloud/dashboard/models) — What the page answers; Tiles and charts; Sampling calls; Inspect one model; Troubleshooting
- [Overview page](https://www.assistant-ui.com/docs/cloud/dashboard/overview) — What the page measures; Read outcomes and configuration changes; Find the next conversation; Troubleshooting
- [Runs page](https://www.assistant-ui.com/docs/cloud/dashboard/runs) — Read the range summary; Find a run in List; Compare runs in Analysis; Inspect one run; Troubleshooting
- [Threads page](https://www.assistant-ui.com/docs/cloud/dashboard/threads) — Search the conversation list; Filter by conversation and behaviour; Review threads; Inspect one thread; Troubleshooting
- [Users page](https://www.assistant-ui.com/docs/cloud/dashboard/users) — What the page answers; Charts; Inspect one user; Page users and billed active users; Troubleshooting
- [Introduction](https://www.assistant-ui.com/docs/cloud) — What you get; How it fits together; Pick your integration; How the book is organised; Where to start
- [Plans and pricing](https://www.assistant-ui.com/docs/cloud/pricing) — Plans; What counts as an active user; What every plan includes; At the cap; Changing plans
- [Quickstart](https://www.assistant-ui.com/docs/cloud/quickstart) — When the first turn does not show up; Next
- [Alerts](https://www.assistant-ui.com/docs/cloud/settings/alerts) — Metrics and evaluation; Configure a rule; Rule allowance; Webhook delivery; Recent deliveries
- [Audit log](https://www.assistant-ui.com/docs/cloud/settings/audit-log) — What an entry records; Actions by resource; Find an entry; User erasure; Configuration markers on Overview
- [Billing and usage](https://www.assistant-ui.com/docs/cloud/settings/billing) — Billing; Plan and active users; Pace and projected use; Plan details; What the plan includes
- [General](https://www.assistant-ui.com/docs/cloud/settings/general) — Project details; Edit project; Data retention; Danger zone; Permissions and audit record
- [Settings](https://www.assistant-ui.com/docs/cloud/settings) — The pages; Who may change what; What the audit log records
- [Model prices](https://www.assistant-ui.com/docs/cloud/settings/model-prices) — How a stored run gets a price; Price overrides; Unpriced models; How Models reads price data; Audit record
- [Telemetry settings](https://www.assistant-ui.com/docs/cloud/settings/telemetry) — Endpoints; Trace link; Renderer URL; Clients; Troubleshooting

### copilots (5)

- [Assistant Frame API](https://www.assistant-ui.com/docs/copilots/assistant-frame) — Overview; Basic Usage; In the iframe (Provider); In the parent window (Host); Advanced Usage
- [makeAssistantVisible](https://www.assistant-ui.com/docs/copilots/make-assistant-visible) — Usage; API Reference; Parameters; Behavior; Example
- [Model Context](https://www.assistant-ui.com/docs/copilots/model-context) — Core Concepts; System Instructions; Tools; Context Provider System; Provider Composition
- [Intelligent Components](https://www.assistant-ui.com/docs/copilots/motivation) — The Evolution of Components; Adding Intelligence; 1. Making Components Readable (makeAssistantVisible); 2. Adding System Instructions (useAssistantInstructions); 3. Creating Tools
- [useAssistantInstructions](https://www.assistant-ui.com/docs/copilots/use-assistant-instructions) — Usage; API Reference; Parameters; Behavior; Example

### guides (28)

- [File Attachments](https://www.assistant-ui.com/docs/guides/attachments) — Overview; Getting Started; Built-in Attachment Adapters; AI SDK Runtime (Default); SimpleImageAttachmentAdapter
- [Message Branching](https://www.assistant-ui.com/docs/guides/branching) — Shortest Working Pattern; Triggering Reload; Programmatic Branch Navigation; Grouped Parts After Branching
- [Chain of Thought UI](https://www.assistant-ui.com/docs/guides/chain-of-thought) — Overview; Quick Start; LangGraph; Legacy: ChainOfThoughtPrimitive; Reading Collapsed State
- [ChatGPT Subscription](https://www.assistant-ui.com/docs/guides/chatgpt-subscription) — Log in with Codex; AI SDK route; Eve agents; OpenAI-compatible proxy
- [Assistant Context API](https://www.assistant-ui.com/docs/guides/context-api) — Introduction; Core Concepts; Scopes and Hierarchy; State Management Model; Essential Hooks
- [Speech-to-Text Dictation](https://www.assistant-ui.com/docs/guides/dictation) — WebSpeechDictationAdapter; DictationAdapter interface; Interim vs final results; Disabling input during dictation; UI: ComposerPrimitive.Dictate
- [Message Editing](https://www.assistant-ui.com/docs/guides/editing) — Mental Model; Enabling Edit Support; Detecting Edit Mode; Imperative API; Editing While Streaming
- [Electron](https://www.assistant-ui.com/docs/guides/electron) — Choose a connection pattern; Pattern 1: hosted backend; Pattern 2: local main process; 1. Define a data-only protocol; 2. Expose one preload capability
- [Headless Composer Input](https://www.assistant-ui.com/docs/guides/headless-composer-input) — Usage; Hook Result; What You Still Own; Trigger Popovers; Related
- [Image Generation](https://www.assistant-ui.com/docs/guides/image-generation) — Generate in your backend; Store it as an `ImageMessagePart`; Render with the `Image` component; Example
- [Guides](https://www.assistant-ui.com/docs/guides) — Composer; Messages; Tools & Generative UI; Display; Audio
- [Input History](https://www.assistant-ui.com/docs/guides/input-history) — Usage; Behavior
- [LaTeX in Chat Messages](https://www.assistant-ui.com/docs/guides/latex) — Supported Formats; Supporting Alternative LaTeX Delimiters; Currency amounts
- [Mentions in Chat](https://www.assistant-ui.com/docs/guides/mentions) — How It Works; Quick Start; Trigger Adapter; Async Mention Search; Built-in Mention Adapter
- [Message Timing & Token Stats](https://www.assistant-ui.com/docs/guides/message-timing) — Reading Timing Data; `useMessageTiming()` Return Fields; Runtime Support; Data Stream; AI SDK (`useChatRuntime`)
- [Message Part Grouping](https://www.assistant-ui.com/docs/guides/part-grouping) — Basic Usage; How Adjacent Grouping Works; Use Cases & Examples; Group by Parent ID; Group by Tool Name
- [Quote Selected Text](https://www.assistant-ui.com/docs/guides/quoting) — Get Started; How It Works; Data Shape; Backend Handling; Claude SDK Citations
- [Resumable Stream Deployment](https://www.assistant-ui.com/docs/guides/resumable-stream-deployment) — Authentication and authorization; `waitUntil` on serverless; TTL strategy; Multi-tenant key isolation; Observability hooks
- [Custom Resumable Stream Stores](https://www.assistant-ui.com/docs/guides/resumable-stream-stores) — Interface walkthrough; Acquire semantics; The cursor contract; A worked example; TTL and eviction
- [Resumable Streams](https://www.assistant-ui.com/docs/guides/resumable-streams) — What it solves; Server side: minimum wiring; Client side: native integration; Multiple threads; Storage choices
- [Custom Scrollbar](https://www.assistant-ui.com/docs/guides/scrollbar) — Related Components
- [Slash Commands](https://www.assistant-ui.com/docs/guides/slash-commands) — How It Works; Quick Start; 1. Define Commands with `unstable_useSlashCommandAdapter`; `unstable_useSlashCommandAdapter` options; 2. Controlling the Chip
- [Text-to-Speech for Chat](https://www.assistant-ui.com/docs/guides/speech) — SpeechSynthesisAdapter; WebSpeechSynthesisAdapter; UI: ActionBarPrimitive.Speak; Custom adapters; Related guides
- [Reading State Outside the Thread](https://www.assistant-ui.com/docs/guides/state-outside-the-thread) — Put the provider above the chrome; One value per selector; React to events from anywhere; Another React root or plain code
- [Streamdown Markdown Renderer](https://www.assistant-ui.com/docs/guides/streamdown) — Installation; CSS setup; Basic Usage; With Plugins (Recommended); Migration from react-markdown
- [Suggested Prompts](https://www.assistant-ui.com/docs/guides/suggestions) — Quick Start; Suggestion Format; Simple Strings; Objects with Title and Description; Displaying Suggestions
- [Thread Virtualization](https://www.assistant-ui.com/docs/guides/virtualization) — Do you need this?; Rows, not messages; Rendering a row; Padding spacers, not absolute positioning; Owning the scroll element
- [Realtime Voice Chat](https://www.assistant-ui.com/docs/guides/voice) — Three voice modes; RealtimeVoiceAdapter; Typed text during a session; createVoiceSession; Configuration

### ink (6)

- [Adapters](https://www.assistant-ui.com/docs/ink/adapters) — createFileStorageAdapter; Attachment adapters; TitleGenerationAdapter; RemoteThreadListAdapter; Which option to choose?
- [Custom Backend](https://www.assistant-ui.com/docs/ink/custom-backend) — Option 1: ChatModelAdapter only; Option 2: Local file persistence; Options; When this fits; Option 3: Full backend thread management
- [Hooks](https://www.assistant-ui.com/docs/ink/hooks) — State Hooks; useAuiState; useAui; useAuiEvent; useNotification
- [Installation](https://www.assistant-ui.com/docs/ink) — Quick Start; Manual Setup; What's Next?
- [Migration from Web](https://www.assistant-ui.com/docs/ink/migration) — What stays the same; What changes; Step-by-step; Monorepo code sharing
- [Primitives](https://www.assistant-ui.com/docs/ink/primitives) — Thread; Root; Messages; AuiIf; Empty (deprecated)

### integrations (15)

- [Custom attachment uploads](https://www.assistant-ui.com/docs/integrations/attachments/custom-adapter) — How it works; Setup; Variants; Opaque file references (LangGraph / LangChain); Notes
- [better-auth](https://www.assistant-ui.com/docs/integrations/auth/better-auth) — How it works; Setup; Notes; Related
- [Clerk](https://www.assistant-ui.com/docs/integrations/auth/clerk) — How it works; Setup; Notes; Related
- [Auth.js (next-auth)](https://www.assistant-ui.com/docs/integrations/auth/next-auth) — How it works; Setup; Notes; Related
- [Vercel AI SDK](https://www.assistant-ui.com/docs/integrations/frameworks/ai-sdk) — Where it slots in; Pick a version; When to pick AI SDK; Related
- [Cloudflare Agents](https://www.assistant-ui.com/docs/integrations/frameworks/cloudflare-agents) — Architecture; Requirements; Setup; Notes; Type compatibility with `useChat`
- [Full-stack integration](https://www.assistant-ui.com/docs/integrations/frameworks/mastra/full-stack) — Setup; Notes; Related
- [Mastra Integration](https://www.assistant-ui.com/docs/integrations/frameworks/mastra/overview) — Pick a pattern; Architecture; Requirements; Next
- [Separate server integration](https://www.assistant-ui.com/docs/integrations/frameworks/mastra/separate-server) — Setup; Notes; Related
- [LLM Gateway Integrations](https://www.assistant-ui.com/docs/integrations/gateways) — Compare; Common pattern; OpenRouter; Portkey; LiteLLM Proxy
- [Integrations](https://www.assistant-ui.com/docs/integrations) — Where integrations slot in; Frameworks; Tools; Gateways; Observability
- [Assistant Cloud](https://www.assistant-ui.com/docs/integrations/observability/assistant-cloud)
- [Langfuse](https://www.assistant-ui.com/docs/integrations/observability/langfuse) — How it works; Setup; Notes; Related
- [LangSmith](https://www.assistant-ui.com/docs/integrations/observability/langsmith) — How it works; Setup; Notes; Related
- [Custom thread persistence](https://www.assistant-ui.com/docs/integrations/persistence/custom-adapter) — Prerequisites; How it works; Schema; Setup; Notes

### migrations (9)

- [Deprecation Policy](https://www.assistant-ui.com/docs/migrations/deprecation-policy) — Experimental Features; Beta Features; Stable Features
- [Migration Guides](https://www.assistant-ui.com/docs/migrations) — Version upgrades; APIs and integrations; Stability
- [Using old React versions](https://www.assistant-ui.com/docs/migrations/react-compatibility) — React 18; Updating the Button Component; Updating the Input Component; Updating the Collapsible Component; Updating Popover Content
- [Migrating to react-langgraph v0.7](https://www.assistant-ui.com/docs/migrations/react-langgraph-v0-7) — Overview; Key Changes; 1. Simplified Thread Management; 2. New `initialize` Parameter; 3. Direct Cloud Integration
- [Migrating Tools to Toolkits](https://www.assistant-ui.com/docs/migrations/toolkit-tools) — Before; After; Mechanical Steps; UI-Only Tool Renderers; Dynamic Tools
- [Migration to v0.11](https://www.assistant-ui.com/docs/migrations/v0-11) — ContentPart renamed to MessagePart; What changed; MessagePrimitive.Content renamed to MessagePrimitive.Parts; Migration; Why this change?
- [Migration to v0.12](https://www.assistant-ui.com/docs/migrations/v0-12) — Major Architecture Change: Unified State API; Automatic Migration; Breaking Changes; 1. Assistant API Hooks Renamed; 2. Context Hooks Replaced with Unified State API
- [Migration to v0.14](https://www.assistant-ui.com/docs/migrations/v0-14) — Automatic Migration; Hook Aliases Removed; Runtime API Cleanups; `AssistantRuntime`; `ThreadRuntime`
- [Migration to v0.15](https://www.assistant-ui.com/docs/migrations/v0-15) — Migrate with an AI Agent; Automatic Migration; Scope Accessors Are Properties; Legacy Context Hooks Removed; `ToolsState.tools` Removed

### primitives (13)

- [ActionBar](https://www.assistant-ui.com/docs/primitives/action-bar) — Quick Start; Core Concepts; Auto-Hide & Floating; Automatic Disabling; Copy State
- [AssistantModal](https://www.assistant-ui.com/docs/primitives/assistant-modal) — Quick Start; Core Concepts; Popover Architecture; Anchor vs Trigger; Auto-Open on Run Start
- [Attachment](https://www.assistant-ui.com/docs/primitives/attachment) — Quick Start; Core Concepts; Two Contexts; Iterator Pattern; Remove Button
- [BranchPicker](https://www.assistant-ui.com/docs/primitives/branch-picker) — Quick Start; Core Concepts; Branch Navigation; Number & Count; hideWhenSingleBranch
- [ChainOfThought](https://www.assistant-ui.com/docs/primitives/chain-of-thought) — Recommended: GroupedParts; GroupedParts API Reference; Legacy: ChainOfThoughtPrimitive; Quick Start; Concepts
- [Composer](https://www.assistant-ui.com/docs/primitives/composer) — Quick Start; Core Concepts; New Message vs Edit Mode; The `asChild` Pattern; Trigger Popovers
- [Error](https://www.assistant-ui.com/docs/primitives/error) — Quick Start; Core Concepts; Auto-Rendering on Error; Automatic Error Text; ErrorPrimitive vs MessagePrimitive.Error
- [Overview](https://www.assistant-ui.com/docs/primitives) — Primitives or elements?; How they work; Available primitives; Related primitive references; Common mistakes
- [Message](https://www.assistant-ui.com/docs/primitives/message) — Quick Start; Core Concepts; Parts Pipeline; Part Types; Tool Resolution
- [SelectionToolbar](https://www.assistant-ui.com/docs/primitives/selection-toolbar) — Quick Start; Core Concepts; Automatic Positioning; Single-Message Validation; Quote Regions
- [Suggestion](https://www.assistant-ui.com/docs/primitives/suggestion) — Quick Start; Core Concepts; Context-Based Rendering; Title and Description; Send vs Populate
- [ThreadList](https://www.assistant-ui.com/docs/primitives/thread-list) — Quick Start; Core Concepts; Three Namespaces; Active State; Keyboard Navigation
- [Thread](https://www.assistant-ui.com/docs/primitives/thread) — Quick Start; Core Concepts; Viewport & Auto-Scroll; Turn Anchor; Viewport Scroll Options

### react-native (14)

- [Adapters](https://www.assistant-ui.com/docs/react-native/adapters) — Persistence; Assistant Cloud; History adapter; RemoteThreadListAdapter; Title generation
- [Attachments](https://www.assistant-ui.com/docs/react-native/attachments) — Install the element; What the installed element does; Adapters for files; What the model receives; Accept documents
- [Custom Backend](https://www.assistant-ui.com/docs/react-native/custom-backend) — Option 1: ChatModelAdapter only; Option 2: Full backend thread management; Adapter methods; Which option to choose?
- [Elements](https://www.assistant-ui.com/docs/react-native/elements) — What ships; Install; Thread slots; The `TaskGroup` slot; The agent elements
- [Add to an Existing App](https://www.assistant-ui.com/docs/react-native/existing-app) — What stays yours; Add Uniwind next to StyleSheet; Install the elements; Mount the thread in your screen; Check it
- [Windowed History](https://www.assistant-ui.com/docs/react-native/history) — Paging through the runtime; The runtime side; The thread element; Your own list; What the elements see
- [Hooks](https://www.assistant-ui.com/docs/react-native/hooks) — State Hooks; useAuiState; useAui; useAuiEvent; Runtime Hooks
- [Installation](https://www.assistant-ui.com/docs/react-native) — Quick Start; Manual Setup; What's Next?
- [Migration from Web](https://www.assistant-ui.com/docs/react-native/migration) — What stays the same; What changes; Step-by-step; Monorepo code sharing
- [Primitives](https://www.assistant-ui.com/docs/react-native/primitives) — Thread; ThreadPrimitive.Root; ThreadPrimitive.Messages; ThreadPrimitive.MessagesFlatList; ThreadPrimitive.RowsFlatList
- [Testing the native kit](https://www.assistant-ui.com/docs/react-native/testing) — Install the test dependencies; Mirror the kit configuration; Test an element with plain props; Test a runtime binding; Preserve classes when a test needs them
- [Thread list](https://www.assistant-ui.com/docs/react-native/thread-list) — Install the element; Create a thread-list runtime; Share one provider; Next steps
- [Tool UI and approvals](https://www.assistant-ui.com/docs/react-native/tool-ui) — Replace the thread fallback; Register a named tool interface; Ask for approval; Choose the right layer
- [Static web export](https://www.assistant-ui.com/docs/react-native/web-export) — Export the example; History does not stay anchored on web; Wait for hydration before reading the CSSOM; Keep clean URLs disabled; Verify the browser build

### runtimes (44)

- [Client and hooks](https://www.assistant-ui.com/docs/runtimes/a2a/client-and-hooks) — A2AClient; Client options; Client methods; useA2ARuntime options; Hooks
- [A2A Agent Runtime](https://www.assistant-ui.com/docs/runtimes/a2a/overview) — When to use it; Architecture; Requirements; A2UI surfaces and stored conversations; Install
- [Quickstart](https://www.assistant-ui.com/docs/runtimes/a2a/quickstart) — Auth and headers; Adding adapters; Next
- [Agent state](https://www.assistant-ui.com/docs/runtimes/ag-ui/agent-state) — Basic usage; Example; How state is synced; Write-back timing; Relationship to other state
- [AG-UI Agent Runtime](https://www.assistant-ui.com/docs/runtimes/ag-ui/overview) — When to use it; Architecture; Requirements; Install; Example
- [Quickstart](https://www.assistant-ui.com/docs/runtimes/ag-ui/quickstart) — Showing thinking and reasoning; Adding adapters; Next
- [Runtime options](https://www.assistant-ui.com/docs/runtimes/ag-ui/runtime-options) — useAgUiRuntime options; Adapter slots; Activity snapshots; Loading conversation history; Building AG-UI run input
- [Vercel AI SDK Runtime](https://www.assistant-ui.com/docs/runtimes/ai-sdk/overview) — Pick a version; Architecture; Choosing useChatRuntime vs useAISDKRuntime; Next
- [AI SDK v4 (legacy)](https://www.assistant-ui.com/docs/runtimes/ai-sdk/v4-legacy) — Why legacy; Setup; Differences from v6; Migration to v7; Alternative: react-ai-sdk\@0.10.16
- [AI SDK v5 (legacy)](https://www.assistant-ui.com/docs/runtimes/ai-sdk/v5-legacy) — Why legacy; Setup; Differences from v6; Migration to v6; Related
- [AI SDK v6 (legacy)](https://www.assistant-ui.com/docs/runtimes/ai-sdk/v6-legacy) — Quickstart; Frontend tools and system messages; Multi-step tool calls; Server-side tool approval; Quote context
- [AI SDK v7](https://www.assistant-ui.com/docs/runtimes/ai-sdk/v7) — Quickstart; Frontend tools and system messages; Multi-step tool calls; Server-side tool approval; Quote context
- [Claude Managed Agents](https://www.assistant-ui.com/docs/runtimes/claude-managed-agents) — The event-to-message mapping; Sessions are the thread list; The approval gate; Token streaming; Security boundary
- [Adapters](https://www.assistant-ui.com/docs/runtimes/concepts/adapters) — Support matrix; Attachment adapter; Speech adapter; Dictation adapter; Feedback adapter
- [Runtime architecture](https://www.assistant-ui.com/docs/runtimes/concepts/architecture) — The three layers; Core runtimes; Protocol layers; Framework adapters; How features flow
- [Stability](https://www.assistant-ui.com/docs/runtimes/concepts/stability) — What `unstable_` means; Why we ship them; Currently unstable APIs; When something stabilizes; Related
- [Threads](https://www.assistant-ui.com/docs/runtimes/concepts/threads) — Single thread (default); Multi-thread paths; AssistantCloud; RemoteThreadListRuntime (custom database); Persisting messages
- [Assistant Transport](https://www.assistant-ui.com/docs/runtimes/custom/assistant-transport) — When to use it; Mental model; Command lifecycle; Building a backend endpoint; Handling commands
- [Data Stream Protocol](https://www.assistant-ui.com/docs/runtimes/custom/data-stream) — When to use it; Wire protocols; Install; Quickstart; Headers and authentication
- [ExternalStoreRuntime](https://www.assistant-ui.com/docs/runtimes/custom/external-store) — When to use it; Architecture; Quickstart; Message conversion; Inline `convertMessage`
- [LocalRuntime](https://www.assistant-ui.com/docs/runtimes/custom/local-runtime) — When to use it; Quickstart; Streaming responses; Only the last part streams; Streaming with tool calls
- [Custom Runtime](https://www.assistant-ui.com/docs/runtimes/custom/overview) — The four paths; Decision tree; What each path gives you; Common building blocks; Next
- [Eve Runtime](https://www.assistant-ui.com/docs/runtimes/eve/overview) — When to use it; Architecture; Connector authorization; Store threads in Assistant Cloud; Requirements
- [Quickstart](https://www.assistant-ui.com/docs/runtimes/eve/quickstart) — From the template; With the Eve CLI; Manual setup in an existing app; Production auth; Next
- [API reference](https://www.assistant-ui.com/docs/runtimes/google-adk/api) — createAdkStream; Direct ADK server connection; Server helpers; createAdkApiRoute; adkEventStream
- [Hooks](https://www.assistant-ui.com/docs/runtimes/google-adk/hooks) — Agent and session state; Tool confirmations; Auth requests; Input requests; Artifacts
- [Google ADK Runtime](https://www.assistant-ui.com/docs/runtimes/google-adk/overview) — When to use it; Architecture; Requirements; Install; Next
- [Quickstart](https://www.assistant-ui.com/docs/runtimes/google-adk/quickstart) — Adding adapters; Next
- [LangChain React Runtime](https://www.assistant-ui.com/docs/runtimes/langchain) — When to use it; Architecture; Requirements; Quickstart; `useStreamRuntime` options
- [Agent state](https://www.assistant-ui.com/docs/runtimes/langgraph/agent-state) — Enable the `values` stream mode; Basic usage; Example; How state is synced; Write-back timing
- [LangGraph Generative UI](https://www.assistant-ui.com/docs/runtimes/langgraph/generative-ui) — Enable the `custom` stream mode; Custom state key; Emit a UI message from your graph; Register a renderer on the client; Register renderers via `uiComponents`
- [Interrupts and message editing](https://www.assistant-ui.com/docs/runtimes/langgraph/interrupts) — Interrupt persistence; Message editing and regeneration; Next
- [LangGraph UI Runtime](https://www.assistant-ui.com/docs/runtimes/langgraph/overview) — When to use it; Architecture; Requirements; Install; Next
- [Quickstart](https://www.assistant-ui.com/docs/runtimes/langgraph/quickstart) — From the template; Manual setup in an existing project; Production proxy backend; Next
- [Streaming](https://www.assistant-ui.com/docs/runtimes/langgraph/streaming) — Message accumulator; Message conversion; Event handlers; Message metadata; Generative UI
- [Threads](https://www.assistant-ui.com/docs/runtimes/langgraph/threads) — Basic thread support; Cloud persistence; Custom thread list; Next
- [Introduction](https://www.assistant-ui.com/docs/runtimes/langgraph/tutorial/introduction) — Prerequisites; Final result; Get started
- [Part 1: Setup frontend](https://www.assistant-ui.com/docs/runtimes/langgraph/tutorial/part-1) — Create a new project; Setup environment variables; Start the server; Explore features; Streaming
- [Part 2: Generative UI](https://www.assistant-ui.com/docs/runtimes/langgraph/tutorial/part-2) — PriceSnapshotTool; Bind tool UI; Try it out!; Visualizing tool results; Install dependencies
- [Part 3: Approval UI](https://www.assistant-ui.com/docs/runtimes/langgraph/tutorial/part-3) — Background: LangGraph implementation details; Add approval UI; Bind approval UI; Try it out!; Add `TransactionConfirmationFinal` to show approval result
- [Hooks](https://www.assistant-ui.com/docs/runtimes/opencode/hooks) — Permissions; Questions; Session; Thread state; Runtime extras
- [OpenCode Runtime](https://www.assistant-ui.com/docs/runtimes/opencode/overview) — When to use it; Architecture; Requirements; Sub-agent conversations; Install
- [Quickstart](https://www.assistant-ui.com/docs/runtimes/opencode/quickstart) — Default model and agent; Bring your own client; Resuming a session; Store threads in Assistant Cloud; Next
- [Picking a runtime](https://www.assistant-ui.com/docs/runtimes/pick-a-runtime) — Lens 1: by framework; First-party adapters; Integration guides; Lens 2: by needs; Shared concepts

### store (11)

- [API Reference](https://www.assistant-ui.com/docs/store/api-reference) — Hooks; useAui(); AuiConfig; useAuiState; useAuiEvent
- [Child Scopes](https://www.assistant-ui.com/docs/store/child-scopes) — The pattern; Step by step; 1. Register both scopes; 2. Build the parent resource with useClientLookup; 3. Use Derived to create the child scope
- [Events](https://www.assistant-ui.com/docs/store/events) — Declaring events; Emitting events; Subscribing to events; Event scoping; Listening to child events
- [Meta](https://www.assistant-ui.com/docs/store/meta) — Root scopes; Derived scopes; Unavailable scopes; Summary
- [Methods](https://www.assistant-ui.com/docs/store/methods) — Defining methods; useAui; Scope accessors; Don't read state during render; Checking if a scope exists
- [Quickstart](https://www.assistant-ui.com/docs/store/quickstart) — Installation; Define your scope types; Create a resource; Use it in React; Next steps
- [Rendering Lists](https://www.assistant-ui.com/docs/store/rendering-lists) — The pattern; Why this pattern?; Length-based subscription; RenderChildrenWithAccessor; Built-in primitives
- [Scopes](https://www.assistant-ui.com/docs/store/scopes) — Registering scopes; Filling scopes
- [Sibling Scopes](https://www.assistant-ui.com/docs/store/sibling-scopes) — The problem; useAssistantClientRef; attachTransformScopes; Checking parent.source; Adding derived scopes
- [State](https://www.assistant-ui.com/docs/store/state) — Defining state; useAuiState; Selecting from multiple scopes; Checking if a scope exists; AuiIf
- [Why Store](https://www.assistant-ui.com/docs/store/why-store) — The gap; How Store bridges the gap

### tap (11)

- [API Reference](https://www.assistant-ui.com/docs/tap/api-reference) — resource; withKey; Hooks; useResource; useResources
- [Composition](https://www.assistant-ui.com/docs/tap/composition) — useResource; useResources; Composition creates ownership
- [Context](https://www.assistant-ui.com/docs/tap/context) — createContext; Reading context; useContextProvider
- [How tap differs from React](https://www.assistant-ui.com/docs/tap/differences-from-react) — Effects run in call order; The tree re-renders from the root; `useLayoutEffect` collapses onto `useEffect`; Where a throwing snapshot surfaces depends on the host
- [Introduction](https://www.assistant-ui.com/docs/tap) — Resources are the unit of state composition; 1. Write a Hook; 2. Create a Resource; 3. Use it in React; 4. Swap the implementation
- [Lifecycle](https://www.assistant-ui.com/docs/tap/lifecycle) — Render and commit; Effect ordering; Mount and unmount; Concurrent mode; Offscreen / Activity
- [Motivation](https://www.assistant-ui.com/docs/tap/motivation) — Composable configuration; State management with React's lifecycle
- [Outside React](https://www.assistant-ui.com/docs/tap/outside-react) — createTapRoot; Scheduling and flushing; flushTapSync; React interop
- [Quickstart](https://www.assistant-ui.com/docs/tap/quickstart) — Install; Define a Resource; Use it in React; Next steps
- [Resources](https://www.assistant-ui.com/docs/tap/resources) — Package a Hook as a Resource; Configuration is a value; Hosting a Resource; Next
- [Trees & Re-renders](https://www.assistant-ui.com/docs/tap/trees-and-rerenders) — Resource trees; Re-renders; Separate scheduling with useTapRoot; Tree roots and scheduling; flushTapSync

### tools (17)

- [A2UI over AG-UI](https://www.assistant-ui.com/docs/tools/a2ui) — Wire contract; Quick start; Actions; Component mapping; Limitations
- [Backend Tools](https://www.assistant-ui.com/docs/tools/backend) — The request body; Generative toolkits: `AISDKToolkit`; Client-defined tools: `frontendTools`; Multi-modal results; Multi-step tool calls
- [Defining Tools](https://www.assistant-ui.com/docs/tools/defining-tools) — Define tools with `"use generative"`; Quick start (`"use generative"`); How the compiler splits a generative file; Running without your own backend; Tool kinds
- [Dynamic Tools](https://www.assistant-ui.com/docs/tools/dynamic-tools) — 1. Declare the contract with `stubTool()`; 2. Supply the executor with `useAuiToolOverrides`; When to use this vs. Interactables
- [Generative UI primitive](https://www.assistant-ui.com/docs/tools/generative-ui-primitive) — When not to use the primitive; Quick start; 1. Define your component allowlist; 2. Wire the primitive into your message renderer; 3. Have the agent emit UI
- [Generative UI on Slack](https://www.assistant-ui.com/docs/tools/generative-ui-slack) — Posting a tree; Warnings; Component mapping; Date and time pickers; Cards
- [Generative UI on Microsoft Teams](https://www.assistant-ui.com/docs/tools/generative-ui-teams) — Sending a card; Warnings; Component mapping; Layout differences; Inputs
- [Generative UI](https://www.assistant-ui.com/docs/tools/generative-ui) — Which generative UI pattern?; Quick start; What the model emits; Extending the vocabulary; Actions
- [Tools](https://www.assistant-ui.com/docs/tools) — Start here; Define tools with `"use generative"`; Rendering AI output as UI; Connect external tools; Reference & components
- [Interactable Tool UIs](https://www.assistant-ui.com/docs/tools/interactables) — Overview; Types of Interactables; Features; Use Cases; Quick Start
- [MCP Apps](https://www.assistant-ui.com/docs/tools/mcp-apps) — Overview; Quick start; Install the MCP client; Client; Per-app options
- [Model Context Protocol (MCP)](https://www.assistant-ui.com/docs/tools/mcp) — How it works; Setup; Notes; Related
- [Multi-Agent Chat UI](https://www.assistant-ui.com/docs/tools/multi-agent) — Overview; Quick Start; Subgraph Namespace Events; Recursive Sub-Agents; Status
- [OpenUI](https://www.assistant-ui.com/docs/tools/openui) — How it relates to the `present` tool; Quick start; Interaction and replay; Customization; Related
- [Tool UI](https://www.assistant-ui.com/docs/tools/tool-ui) — Overview; Creating Tool UIs; 1. Client-Defined Tools; 2. UI-Only for Existing Tools; Quick Start Example
- [User-managed MCP servers](https://www.assistant-ui.com/docs/tools/user-managed-mcp) — How it works; Setup; Form elicitation; Storage; Auth
- [WebMCP provider](https://www.assistant-ui.com/docs/tools/webmcp) — Browser support; Usage; Choosing which tools to publish; Lifecycle; API

### utilities (3)

- [heat-graph](https://www.assistant-ui.com/docs/utilities/heat-graph) — Installation; Quick Start; Anatomy; API Reference; Root
- [react-o11y](https://www.assistant-ui.com/docs/utilities/react-o11y) — Installation; Quick start; Examples; Status states; Collapsible subtrees
- [tw-shimmer](https://www.assistant-ui.com/docs/utilities/tw-shimmer) — Installation; Quick Start; Text Shimmer; Skeleton Loader; Skeleton Card with Auto-Sizing

### vue (5)

- [Introduction](https://www.assistant-ui.com/docs/vue) — Start here; How it fits together
- [Quickstart](https://www.assistant-ui.com/docs/vue/quickstart) — Next steps
- [Runtimes](https://www.assistant-ui.com/docs/vue/runtimes) — AISDKChat; AISDKThreads; External store
- [Server rendering](https://www.assistant-ui.com/docs/vue/ssr) — What belongs on the server; Nuxt wiring
- [Tool UI](https://www.assistant-ui.com/docs/vue/tool-ui) — Register data renderers; Register tool UIs in config; Register a Vue component at runtime; Human-in-the-loop actions; Chain of thought

## Appendix B: all Blume English documentation pages

All 63 English documentation pages below were present in the corpus. These also have corresponding `/de/docs`, `/hi/docs`, `/ja/docs`, and `/pt/docs` translations (63 per locale), all retrieved in that same corpus.
- [Introduction](https://useblume.dev/docs) — Why Blume exists; What makes Blume different; Fast by default; AI-ready out of the box; Zero configuration — even the template
- [Quickstart](https://useblume.dev/docs/quickstart) — Install and run; Write your first page; Next steps
- [Deployment](https://useblume.dev/docs/deployment) — Deploy anywhere (static); Set your site URL; Monorepos; Preview locally; Subpath deploys
- [Migrate to Blume](https://useblume.dev/docs/migrating) — Migrate with one command; Sources; What the agent does; Other agents; Compare first
- [Upgrade to Blume 2](https://useblume.dev/docs/upgrading) — Upgrade with one command; Search; Deployment; Content sources; API references
- [FAQ](https://useblume.dev/docs/faq) — How is Blume different from Mintlify, Fumadocs, and others?; Is Blume free and open-source?; Do I need to know Astro, React, or Tailwind?; Can I use React components and MDX?; Where can I deploy it?
- [Pages](https://useblume.dev/docs/content) — Markdown and MDX; Files and routes; Ordering with numeric prefixes; Group folders; Drafts
- [Navigation](https://useblume.dev/docs/content/navigation) — The generated sidebar; Page label, icon, and badge; Folder groups; Display modes; Per-group overrides
- [Folder meta](https://useblume.dev/docs/content/meta) — Defining meta; Fields; Computed meta; Ordering within a group; Internationalization
- [Frontmatter](https://useblume.dev/docs/content/frontmatter) — Layout; Related pages; Sidebar; SEO; Search
- [Syntax](https://useblume.dev/docs/content/syntax) — Headings; Section; Subsection; Custom anchors; Getting started [#setup]
- [Includes](https://useblume.dev/docs/content/includes) — Partials; Props; Including code files; Rules and diagnostics
- [Variables](https://useblume.dev/docs/content/variables) — What's new in {{version}}; Where they apply; Undefined names
- [Components](https://useblume.dev/docs/content/components) — Card and CardGroup; Steps; Tabs; View; Install the client
- [Islands](https://useblume.dev/docs/content/islands) — The `islands/` convention; Registering islands in `components.ts`; Hydration; Frameworks; Hooks
- [Internationalization](https://useblume.dev/docs/content/i18n) — Enable it; Organize translated content; Filename suffixes; Shared files; Default-locale URLs
- [Versioning](https://useblume.dev/docs/content/versioning) — Enable it; Cut a version; The switcher and the notice; SEO; Search
- [Obsidian](https://useblume.dev/docs/content/sources/obsidian)
- [Remote MDX](https://useblume.dev/docs/content/sources/remote-mdx)
- [GitHub Releases](https://useblume.dev/docs/content/sources/github-releases)
- [Sanity](https://useblume.dev/docs/content/sources/sanity)
- [Notion](https://useblume.dev/docs/content/sources/notion) — Writing MDX in Notion
- [Contentful](https://useblume.dev/docs/content/sources/contentful)
- [Payload](https://useblume.dev/docs/content/sources/payload)
- [Strapi](https://useblume.dev/docs/content/sources/strapi)
- [Custom sources](https://useblume.dev/docs/content/sources/custom)
- [Configuration file](https://useblume.dev/docs/configuration) — A complete example; Site; Logo; Favicon; Apple touch icon
- [Theming](https://useblume.dev/docs/configuration/theming) — Config tokens; Accent; Radius; Color mode; Fonts
- [Customization](https://useblume.dev/docs/configuration/customization) — Component overrides; Reference form; Typing an override; Layout slots; Interactive islands
- [Search](https://useblume.dev/docs/configuration/search) — Using search; Popular pages; What's indexed; Tags; Ranking
- [Assistant](https://useblume.dev/docs/configuration/assistant) — Suggested questions; Asking about code; Contact support; Custom instructions; Grounding
- [Rate limiting](https://useblume.dev/docs/configuration/rate-limiting) — Where the count lives; Memory; Upstash; Cloudflare; Behind a reverse proxy
- [Narration](https://useblume.dev/docs/configuration/narration) — What it reads; Listening; Browser voices; Generated voices; OpenAI and self-hosted voices
- [Analytics](https://useblume.dev/docs/configuration/analytics) — Adapters; PostHog; Vercel Web Analytics; Cloudflare Web Analytics; Google Analytics 4
- [Cookie consent](https://useblume.dev/docs/configuration/consent) — Adapters; Blume's banner; Osano; Ethyca; Changing an answer
- [Export](https://useblume.dev/docs/configuration/export) — Enable it; PDF; EPUB; What gets exported
- [SEO and GEO](https://useblume.dev/docs/discoverability) — What the build emits; Checking your work
- [Metadata](https://useblume.dev/docs/discoverability/metadata) — X attribution; Your own tags; Per-page overrides
- [Open Graph images](https://useblume.dev/docs/discoverability/open-graph) — Brand the generated card; Show, hide, or override card layers; Card fonts; Card cache; Custom page titles
- [Structured data](https://useblume.dev/docs/discoverability/structured-data) — Site identity; Custom pages
- [RSS feeds](https://useblume.dev/docs/discoverability/rss)
- [Sitemap and robots](https://useblume.dev/docs/discoverability/sitemap-and-robots) — Sitemap; Robots; Content signals
- [llms.txt](https://useblume.dev/docs/discoverability/llms-txt) — Options; Generated sections; Excluding a page; Bringing your own
- [Markdown for agents](https://useblume.dev/docs/discoverability/markdown) — Raw Markdown; Content negotiation; Custom component serializers; Copy as Markdown; Open in chat
- [JSON API](https://useblume.dev/docs/discoverability/json-api) — Errors; OpenAPI description; Turning it off
- [MCP server](https://useblume.dev/docs/discoverability/mcp) — Tools and resources; Scoping by content type and facets; Server output required
- [Agent discovery](https://useblume.dev/docs/discoverability/agent-discovery) — Agent readability; Discovery Link header; API catalog; AI catalog; WebMCP
- [Skills](https://useblume.dev/docs/advanced/skills) — Blume; Migration; Self-updating docs; Writing your site's skill
- [Custom pages](https://useblume.dev/docs/advanced/custom-pages) — Add a page; Files and routes; Reading site data; Runtime helpers; Using the site layout
- [Changelogs](https://useblume.dev/docs/advanced/changelog) — Write an entry; The `changelog` object; The index page; From GitHub Releases; Keep entries out of the sidebar
- [Blog](https://useblume.dev/docs/advanced/blog) — Write a post; The RSS feed; Structured data; Building an index
- [OpenAPI](https://useblume.dev/docs/references/openapi) — A local spec; OpenAPI 3.2; Route; Code samples and schemas; Your own samples
- [AsyncAPI](https://useblume.dev/docs/references/asyncapi) — Spec versions; Code samples; Shared options; Embedding Scalar instead; Try it for events
- [GraphQL](https://useblume.dev/docs/references/graphql) — Generated examples; Type pages; Multiple schemas; Try it playground
- [Scalar](https://useblume.dev/docs/references/scalar) — What the embed doesn't do; Passing Scalar options; AsyncAPI documents
- [Hand-written API pages](https://useblume.dev/docs/references/api-pages) — The playground and samples; Site defaults
- [Overview](https://useblume.dev/docs/cli) — Commands; Common flags; Verifying while the dev server runs; Type-checking
- [Doctor](https://useblume.dev/docs/cli/doctor) — What it checks; The summary; Exit code and JSON
- [Validate](https://useblume.dev/docs/cli/validate) — What counts as a page; Flags; Diagnostics; JSON output
- [Audit](https://useblume.dev/docs/cli/audit) — Flags; Failing CI; Checking a live deployment; Fixing the findings with an agent; What it does and doesn't check
- [Evals](https://useblume.dev/docs/cli/evals) — How it works; Writing evals; Failing CI; Fixing the findings; Flags
- [Translate](https://useblume.dev/docs/cli/translate) — How it works; What gets translated; Validation; Failing CI; Limitations
- [Version](https://useblume.dev/docs/cli/version) — Listing versions; Flags; When it refuses

## Appendix C: broader topic implications

| Documentation family | What was assessed for this application |
| --- | --- |
| assistant-ui architecture, installation, guides, primitives, store | Runtime ownership, React message/composer primitives, streaming states, state access, chat lifecycle, attachment and persistence seams |
| assistant-ui tool and generative UI guides/API | Known-tool rendering versus model-composed `$type` trees versus native specs; compiler/runtime split; Zod vocabulary; action dispatch and continuation |
| assistant-ui runtimes/integrations | Local/external/custom protocols compared with AI SDK, LangGraph, AG-UI, A2A, Eve, ADK, and managed-agent integrations; custom Python adapter is viable |
| assistant-ui Cloud API and SDK | Hosted persistence/auth/telemetry are optional; no Cloud setup required for local FastAPI architecture |
| assistant-ui native, Ink, Vue, TAP | Separate platforms/protocols; outside this React web task |
| assistant-ui migrations/experimental APIs | Avoid older helper names and unstable interactables unless specifically required |
| Blume content/navigation/syntax/components | Markdown/MDX authoring conventions for a documentation site; components/overrides are generally Astro-oriented rather than Vite-ready chat components |
| Blume islands/customization | React hook entry, generated snapshot dependency for page/site hooks, hydration conventions, CLI copying/ejection do not create a generic chat provider |
| Blume search/assistant/rate limits | Docs snapshot lexical search differs from governed product retrieval; hook supports external plain-text endpoint; built-in provider route needs server deployment |
| Blume content sources | Build-time docs adapters for remote Markdown, CMS, Obsidian and custom sources; do not reuse as product ingestion adapters without a separate contract |
| Blume i18n/versioning | Documentation locale/version conventions; unrelated to knowledge-product immutable releases |
| Blume discoverability | llms corpus, Markdown mirrors, read-only JSON docs API, optional MCP, SEO/discovery surfaces; relevant for a separate docs portal |
| Blume references | OpenAPI/AsyncAPI/GraphQL/Scalar documentation renderer; potential separate FastAPI reference site |
| Blume deployment | Static versus server build; external AI endpoint retains static docs output; Node >=22.12 requirement |
| Blume CLI/advanced/upgrading/changelog | Authoring/audit/evaluation/migration maintenance workflows; no CLI or migration was run |

The implementation recommendations above are intentionally restricted to APIs verified in the official documentation and package source.
