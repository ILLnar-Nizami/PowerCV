import { ErrorBoundary } from "@/components/ErrorBoundary";
import { AppLayout } from "@/components/layout/AppLayout";
import { AnalysisPage } from "@/pages/AnalysisPage";
import { CoverLetterPage } from "@/pages/CoverLetterPage";
import { DashboardPage } from "@/pages/DashboardPage";
import { MasterCVPage } from "@/pages/MasterCVPage";
import { OptimizePage } from "@/pages/OptimizePage";
import { ResultsPage } from "@/pages/ResultsPage";
import { ResumePreviewPage } from "@/pages/ResumePreviewPage";
import { createBrowserRouter } from "react-router-dom";

export const router = createBrowserRouter([
	{
		path: "/",
		element: <AppLayout />,
		errorElement: <ErrorBoundary />,
		children: [
			{
				index: true,
				element: <DashboardPage />,
			},
			{
				path: "dashboard",
				element: <DashboardPage />,
			},
			{
				path: "optimize",
				element: <OptimizePage />,
			},
			{
				path: "analysis",
				element: <AnalysisPage />,
			},
			{
				path: "results",
				element: <ResultsPage />,
			},
			{
				path: "master-cv",
				element: <MasterCVPage />,
			},
			{
				path: "cover-letter",
				element: <CoverLetterPage />,
			},
			{
				path: "resume/:id",
				element: <ResumePreviewPage />,
			},
		],
	},
]);
