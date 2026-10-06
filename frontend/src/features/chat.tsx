import { useEffect, useMemo, useRef, useState } from "react";
import {
  AssistantRuntimeProvider,
  useExternalStoreRuntime,
  ThreadPrimitive,
  MessagePrimitive,
  ComposerPrimitive,
  ActionBarPrimitive,
  useAuiState,
} from "@assistant-ui/react";
import { MarkdownTextPrimitive } from "@assistant-ui/react-markdown";
import {
  defaultGenerativeUILibrary,
  renderGenerativeUI,
} from "@assistant-ui/react-generative-ui";
import type { GenerativeUILibrary } from "@assistant-ui/react-generative-ui";
import { useAssistant } from "blume/hooks";
import { z } from "zod";
import {
  ArrowUp,
  Copy,
  MessageSquare,
  Plus,
  ArrowUpRight,
  BookOpen,
} from "lucide-react";
import { Link } from "react-router-dom";
import { api, useData } from "../api/client";
import type { Release } from "../api/types";
import { Block, Loading, ErrorState, Status } from "../components/shared";
import { useProduct } from "./product";

interface Source {
  citation: string;
  chunk_id: string;
  document_id: string;
  document_name: string;
  source_url: string;
  text: string;
  start: number;
  end: number;
  score: number;
}
interface Packet {
  id: string;
  state: string;
  revision_id: string;
  release_id: string | null;
  generation: number;
  label: string;
  sources: Source[];
  ui: unknown;
  error: string | null;
  model: string;
}
interface DisplayMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
  packet?: Packet;
}

function Evidence({ sources, prefix }: { sources: Source[]; prefix: string }) {
  return (
    <div className="chat-evidence">
      {sources.map((source) => (
        <details key={source.chunk_id} id={`${prefix}-${source.citation}`}>
          <summary>
            <BookOpen size={14} />
            <span>
              {source.citation} · {source.document_name}
            </span>
          </summary>
          <p>{source.text}</p>
          <a
            href={source.source_url}
            target="_blank"
            rel="noreferrer"
            aria-label={`Open ${source.document_name}`}
          >
            Open original <ArrowUpRight size={12} />
          </a>
        </details>
      ))}
    </div>
  );
}

function Presentation({ packet, prefix }: { packet: Packet; prefix: string }) {
  const library = useMemo<GenerativeUILibrary>(
    () => ({
      Col: defaultGenerativeUILibrary.Col!,
      Row: defaultGenerativeUILibrary.Row!,
      Card: {
        description: "A titled explanation with optional details",
        properties: z.object({
          title: z.string().optional(),
          description: z.string().optional(),
        }),
        render: ({ title, description, children }) => (
          <section data-aui="card">
            {title && <h3 data-aui="card-title">{title}</h3>}
            {description && <p>{description}</p>}
            {children}
          </section>
        ),
      },
      Fact: defaultGenerativeUILibrary.Fact!,
      Table: defaultGenerativeUILibrary.Table!,
      Evidence: {
        description: "Verified source evidence",
        properties: z.object({ citations: z.array(z.string()).max(20) }),
        render: ({ citations }) => (
          <Evidence
            prefix={prefix + "-display"}
            sources={packet.sources.filter((s) =>
              citations.includes(s.citation),
            )}
          />
        ),
      },
    }),
    [packet, prefix],
  );
  if (!packet.ui) return null;
  return (
    <div className="chat-presentation">
      {renderGenerativeUI(packet.ui, library, { status: "done" })}
    </div>
  );
}

function UserMessage() {
  return (
    <MessagePrimitive.Root className="chat-message chat-user">
      <span className="chat-author">You</span>
      <MessagePrimitive.Parts />
    </MessagePrimitive.Root>
  );
}
function AssistantMessage() {
  const custom = useAuiState((s) => s.message.metadata.custom);
  const id = useAuiState((s) => s.message.id);
  const packet = custom.packet as Packet | undefined;
  const prefix = "chat-evidence-" + id.replaceAll(":", "-");
  const Text = () => (
    <MarkdownTextPrimitive
      smooth={false}
      skipHtml
      preprocess={(text) =>
        text.replace(/\[S\d+\]/g, (marker) => {
          const citation = marker.slice(1, -1);
          return packet?.sources.some((s) => s.citation === citation)
            ? `${marker}(#${prefix}-${citation})`
            : marker;
        })
      }
      components={{
        img: ({ alt }) => (
          <span>{alt ? `[Image: ${alt}]` : "[Image omitted]"}</span>
        ),
        a: ({ href, children }) =>
          href?.startsWith(`#${prefix}-`) ? (
            <a
              href={href}
              onClick={() => {
                const target = document.getElementById(href.slice(1));
                if (target instanceof HTMLDetailsElement) target.open = true;
              }}
            >
              {children}
            </a>
          ) : (
            <span>{children}</span>
          ),
      }}
    />
  );
  return (
    <MessagePrimitive.Root className="chat-message chat-assistant">
      <div className="chat-answer-header">
        <span className="chat-author">
          <span className="chat-brand-dot" />
          Knowledge assistant
        </span>
        <ActionBarPrimitive.Root>
          <ActionBarPrimitive.Copy asChild>
            <button className="icon-button" aria-label="Copy answer">
              <Copy size={14} />
            </button>
          </ActionBarPrimitive.Copy>
        </ActionBarPrimitive.Root>
      </div>
      <MessagePrimitive.Parts components={{ Text }} />
      {packet && (
        <>
          <Presentation packet={packet} prefix={prefix} />
          {!!packet.sources.length && (
            <div className="chat-sources-label">
              Source evidence · {packet.label.toLowerCase()}
            </div>
          )}
          <Evidence sources={packet.sources} prefix={prefix} />
          {packet.error && <ErrorState message={packet.error} />}
        </>
      )}
    </MessagePrimitive.Root>
  );
}

function Conversation({
  releaseId,
  configured,
  model,
}: {
  releaseId: string | null;
  configured: boolean;
  model: string;
}) {
  const { product, revision, readonly } = useProduct();
  const [conversationId, setConversationId] = useState(() =>
    crypto.randomUUID(),
  );
  const [packets, setPackets] = useState<Record<number, Packet>>({});
  const [metadataLoading, setMetadataLoading] = useState(false);
  const requestId = useRef(crypto.randomUUID());
  const requestGeneration = useRef(0);
  const parameters = new URLSearchParams({
    conversation_id: conversationId,
    request_id: requestId.current,
    revision_id: revision.id,
    preview: String(!readonly),
  });
  if (releaseId) parameters.set("release_id", releaseId);
  const blume = useAssistant({
    endpoint: `/api/products/${product.id}/chat?${parameters}`,
    errorMessage:
      "The assistant could not start. Prepare knowledge for this version, then check the model connection and try again.",
    rateLimitMessage: "The assistant is busy. Please try again shortly.",
  });
  useEffect(
    () => () => {
      requestGeneration.current++;
      blume.reset();
    },
    [blume.reset],
  );
  const clear = () => {
    requestGeneration.current++;
    blume.reset();
    setPackets({});
    setMetadataLoading(false);
    requestId.current = crypto.randomUUID();
    setConversationId(crypto.randomUUID());
  };
  const messages: DisplayMessage[] = blume.messages.map((message, index) => ({
    id: `${conversationId}:${index}`,
    role: message.role,
    content: message.content,
    packet: packets[index],
  }));
  const runtime = useExternalStoreRuntime<DisplayMessage>({
    isRunning: blume.loading || metadataLoading,
    isSendDisabled: !configured || metadataLoading,
    messages,
    convertMessage: (message) => ({
      id: message.id,
      role: message.role,
      content: [{ type: "text", text: message.content }],
      metadata: { custom: { packet: message.packet } },
    }),
    onNew: async (message) => {
      const question = message.content
        .filter((part) => part.type === "text")
        .map((part) => part.text)
        .join("\n");
      const turn = blume.messages.length + 1;
      const generation = requestGeneration.current;
      const expectedRequest = requestId.current;
      setMetadataLoading(true);
      await blume.ask(question);
      if (generation !== requestGeneration.current) return;
      try {
        const packet = await api<Packet>(
          `/products/${product.id}/chat/runs/${expectedRequest}`,
        );
        if (
          generation === requestGeneration.current &&
          packet.id === expectedRequest &&
          packet.revision_id === revision.id &&
          packet.release_id === releaseId &&
          packet.generation === revision.generation
        )
          setPackets((current) => ({ ...current, [turn]: packet }));
      } catch {
        /* A refused request has no run; Blume already shows the refusal. */
      } finally {
        if (generation === requestGeneration.current) {
          requestId.current = crypto.randomUUID();
          setMetadataLoading(false);
        }
      }
    },
  });
  const prompts = [
    "What does this knowledge cover?",
    "Summarize the key points with sources.",
    "Show the important facts in a table.",
  ];
  return (
    <AssistantRuntimeProvider runtime={runtime}>
      <Block
        title="AI chat"
        subtitle="Ask a business question. Get an answer with evidence."
        action={
          <button onClick={clear} aria-label="Clear conversation">
            <Plus size={14} />
            {blume.loading || metadataLoading ? "Stop and clear" : "Clear"}
          </button>
        }
      >
        <div className="chat-topline">
          <span>
            <span className="chat-brand-dot" />
            {model.replace("deepseek/", "")}
          </span>
          <Status
            value={readonly ? "published" : "draft"}
            label={readonly ? "Published evidence" : "Draft preview"}
          />
        </div>
        {!configured && (
          <div className="block-body">
            <ErrorState message="An administrator needs to configure the server model connection before you can chat." />
          </div>
        )}
        <ThreadPrimitive.Root className="chat-thread">
          <ThreadPrimitive.Viewport
            className="chat-transcript"
            role="log"
            aria-label="Conversation"
          >
            {!blume.messages.length && (
              <div className="chat-welcome">
                <div className="chat-welcome-icon">
                  <MessageSquare size={26} />
                </div>
                <h3>Start with a question.</h3>
                <p>
                  Ask about {product.name}. Answers use the files and records in
                  this version.
                </p>
                <div className="chat-prompts">
                  {prompts.map((prompt) => (
                    <button
                      disabled={!configured}
                      key={prompt}
                      onClick={() =>
                        runtime.thread.append({
                          role: "user",
                          content: [{ type: "text", text: prompt }],
                        })
                      }
                    >
                      {prompt}
                      <ArrowUpRight size={14} />
                    </button>
                  ))}
                </div>
              </div>
            )}
            <ThreadPrimitive.Messages
              components={{ UserMessage, AssistantMessage }}
            />
            {blume.loading && (
              <div className="chat-progress" role="status">
                Reading evidence and composing an answer…
              </div>
            )}
          </ThreadPrimitive.Viewport>
          <ComposerPrimitive.Root className="chat-composer">
            <ComposerPrimitive.Input
              aria-label="Message the assistant"
              placeholder="Ask about your knowledge…"
              rows={2}
              maxLength={2000}
            />
            <ComposerPrimitive.Send asChild>
              <button className="primary" aria-label="Send message">
                <ArrowUp size={18} />
              </button>
            </ComposerPrimitive.Send>
          </ComposerPrimitive.Root>
          <p className="chat-footnote">
            Check the source evidence before acting. Clear starts a new
            conversation and stops an answer in progress.
            <Link to={`/products/${product.id}/processing`}>
              Prepare knowledge
            </Link>
          </p>
        </ThreadPrimitive.Root>
      </Block>
    </AssistantRuntimeProvider>
  );
}

export function ChatPage() {
  const { product, revision, readonly } = useProduct();
  const status = useData<{ configured: boolean; model: string }>(
    "/chat/status",
  );
  const releases = useData<Release[]>(
    readonly ? `/products/${product.id}/releases` : null,
  );
  if (status.loading || (readonly && releases.loading)) return <Loading />;
  if (status.error) return <ErrorState message={status.error} />;
  const releaseId = readonly
    ? releases.data?.find((release) => release.revision_id === revision.id)
        ?.id || null
    : null;
  if (readonly && !releaseId)
    return <ErrorState message="This published version could not be found." />;
  return (
    <Conversation
      key={`${product.id}:${revision.id}:${revision.generation}:${releaseId}`}
      releaseId={releaseId}
      configured={!!status.data?.configured}
      model={status.data?.model || "DeepSeek"}
    />
  );
}
