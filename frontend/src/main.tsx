import * as Sentry from "@sentry/react";
import { StrictMode } from "react";
import { createRoot } from "react-dom/client";
import "./index.css";
import App from "./App.tsx";

// Initialize Sentry
Sentry.init({
	dsn: import.meta.env.VITE_SENTRY_DSN,
	integrations: [
		Sentry.browserTracingIntegration(),
		Sentry.replayIntegration(),
	],
	tracesSampleRate: 1.0,
	tracePropagationTargets: ["localhost", /^\//],
	replaysSessionSampleRate: 0.1,
	replaysOnErrorSampleRate: 1.0,
	environment: import.meta.env.MODE || "development",
});

createRoot(document.getElementById("root")!).render(
	<StrictMode>
		<App />
	</StrictMode>,
);
