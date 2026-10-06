import { createRoot } from "react-dom/client";
import { App } from "@/app/App";
import "./style.css";
import "@fontsource-variable/inter";
import "@fontsource-variable/geist";
import "@fontsource-variable/geist-mono";

const root = document.getElementById("root");
if (!root) throw new Error("The application root is missing");
createRoot(root).render(<App />);
