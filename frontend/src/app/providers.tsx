import type { ReactNode } from "react";
import { BrowserRouter } from "react-router-dom";
import { NoticeProvider } from "@/components/shared";

export function AppProviders({ children }: { children: ReactNode }) {
  return (
    <BrowserRouter>
      <NoticeProvider>{children}</NoticeProvider>
    </BrowserRouter>
  );
}
