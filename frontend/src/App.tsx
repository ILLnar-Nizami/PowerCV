import { router } from "@/router";
import * as Sentry from "@sentry/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { RouterProvider } from "react-router-dom";
import { Toaster } from "sonner";
import "./index.css";

const queryClient = new QueryClient({
	defaultOptions: {
		queries: {
			staleTime: 1000 * 60 * 5, // 5 minutes
			retry: 1,
		},
	},
});

function TestSentryButton() {
	const triggerError = () => {
		try {
			throw new Error("This is a test error for Sentry integration.");
		} catch (error) {
			Sentry.captureException(error);
			alert("Test error triggered! Check Sentry dashboard.");
		}
	};

	return (
		<button
			type="button"
			onClick={triggerError}
			style={{
				position: "fixed",
				bottom: "20px",
				right: "20px",
				padding: "10px 15px",
				backgroundColor: "#ff4444",
				color: "white",
				border: "none",
				borderRadius: "5px",
				cursor: "pointer",
				zIndex: 1000,
			}}
		>
			Test Sentry Error
		</button>
	);
}

function App() {
	return (
		<QueryClientProvider client={queryClient}>
			<RouterProvider router={router} />
			<Toaster position="top-right" richColors />
			<TestSentryButton />
		</QueryClientProvider>
	);
}

export default App;
