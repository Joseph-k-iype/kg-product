/// <reference types="vite/client" />

declare module "blume:search-client" {
  export function createSearch(): Promise<
    (
      query: string,
      options?: { locale?: string; section?: string },
    ) => Promise<{
      hits: Array<{
        url: string;
        title: string;
        excerpt: string;
        content?: string;
      }>;
      sections: Array<{ label: string; count: number }>;
    }>
  >;
}

declare module "html-escaper" {
  export function escape(value: string): string;
  export function unescape(value: string): string;
}
