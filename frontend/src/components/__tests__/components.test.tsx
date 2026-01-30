// @vitest-environment jsdom
import { beforeEach, describe, expect, it, vi } from "vitest";
import "@testing-library/jest-dom";
import { useDeleteResume, useDownloadResume } from "@/hooks/useResumes";
import type { AnalysisResult, Recommendation } from "@/types/optimization";
import {
	type Resume,
	ResumeFormat,
	ResumeStatus,
	TemplateType,
} from "@/types/resume";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { BrowserRouter } from "react-router-dom";

// Mock hooks
vi.mock("@/hooks/useResumes", () => ({
	useDownloadResume: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useDownloadOriginalResume: vi.fn(() => ({
		mutate: vi.fn(),
		isPending: false,
	})),
	useDownloadCoverLetter: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
	useDeleteResume: vi.fn(() => ({ mutate: vi.fn(), isPending: false })),
}));

import { ATSScoreDisplay } from "@/components/analysis/ATSScoreDisplay";
import { RecommendationsList } from "@/components/analysis/RecommendationsList";
import { SkillsMatch } from "@/components/analysis/SkillsMatch";
// Mock components
import { ResumeCard } from "@/components/dashboard/ResumeCard";
import { FileUpload } from "@/components/optimization/FileUpload";
import { TemplateSelector } from "@/components/optimization/TemplateSelector";

// Mock data
const mockResume: Resume = {
	id: "1",
	userId: "demo-user",
	title: "Senior Software Engineer Resume",
	status: ResumeStatus.NOT_APPLIED,
	createdAt: "2024-01-15T10:00:00Z",
	updatedAt: "2024-01-15T10:00:00Z",
	atsScore: 85,
	downloadUrl: "/resumes/senior-software-engineer.pdf",
	company: "TechCorp",
	position: "Senior Software Engineer",
	format: ResumeFormat.PDF,
	isOptimized: true,
	hasCoverLetter: true,
	sourceName: "Uploaded",
};

const mockAnalysis: AnalysisResult = {
	atsScore: 85,
	matchedSkills: ["React", "TypeScript", "Node.js"],
	missingSkills: ["Python", "Docker"],
	recommendations: [
		{
			id: "1",
			category: "skills",
			severity: "high",
			message: "Add more quantifiable achievements",
			suggestion: "Include specific metrics and results",
		} as Recommendation,
	],
};

// Mock query client
const createTestQueryClient = () =>
	new QueryClient({
		defaultOptions: {
			queries: { retry: false },
			mutations: { retry: false },
		},
	});

describe("Component Tests", () => {
	beforeEach(() => {
		vi.clearAllMocks();
	});

	describe("ResumeCard", () => {
		it("renders resume information correctly", () => {
			const queryClient = createTestQueryClient();

			render(
				<QueryClientProvider client={queryClient}>
					<BrowserRouter>
						<ResumeCard resume={mockResume} />
					</BrowserRouter>
				</QueryClientProvider>,
			);

			expect(screen.getByText(mockResume.position || "")).toBeInTheDocument();
			expect(screen.getByText(/85/)).toBeInTheDocument();
		});

		it("handles download click", async () => {
			const mockMutate = vi.fn();
			// biome-ignore lint/suspicious/noExplicitAny: needed for mock
			const mockDownload = { mutate: mockMutate, isPending: false } as any;
			vi.mocked(useDownloadResume).mockReturnValue(mockDownload);

			const queryClient = createTestQueryClient();

			render(
				<QueryClientProvider client={queryClient}>
					<BrowserRouter>
						<ResumeCard resume={mockResume} />
					</BrowserRouter>
				</QueryClientProvider>,
			);

			const downloadButton = screen.getByRole("button", { name: "Optimized" }); // Exact match
			fireEvent.click(downloadButton);

			expect(mockMutate).toHaveBeenCalledWith(mockResume.id);
		});

		it("handles delete click", async () => {
			const mockMutate = vi.fn();
			// biome-ignore lint/suspicious/noExplicitAny: needed for mock
			const mockDelete = { mutate: mockMutate, isPending: false } as any;
			vi.mocked(useDeleteResume).mockReturnValue(mockDelete);
			window.confirm = vi.fn(() => true);

			const queryClient = createTestQueryClient();

			render(
				<QueryClientProvider client={queryClient}>
					<BrowserRouter>
						<ResumeCard resume={mockResume} />
					</BrowserRouter>
				</QueryClientProvider>,
			);

			const deleteButton = screen.getByRole("button", {
				name: "Delete resume",
			});
			fireEvent.click(deleteButton);

			expect(window.confirm).toHaveBeenCalledWith(
				"Are you sure you want to delete this resume?",
			);
			expect(mockMutate).toHaveBeenCalledWith(mockResume.id);
		});
	});

	describe("FileUpload", () => {
		it("renders file upload area", () => {
			render(<FileUpload onFileSelect={vi.fn()} />);

			expect(screen.getByText(/drag and drop/i)).toBeInTheDocument();
			expect(screen.getByText(/choose file/i)).toBeInTheDocument();
		});

		it("handles file selection", async () => {
			const mockFileSelect = vi.fn();
			const file = new File(["test"], "resume.pdf", {
				type: "application/pdf",
			});

			const { container } = render(
				<FileUpload onFileSelect={mockFileSelect} />,
			);

			const input = container.querySelector(
				'input[type="file"]',
			) as HTMLInputElement;
			fireEvent.change(input, { target: { files: [file] } });

			await waitFor(() => {
				expect(mockFileSelect).toHaveBeenCalledWith(file);
			});
		});

		it("validates file types", async () => {
			const invalidFile = new File(["test"], "resume.exe", {
				type: "application/exe",
			});

			const { container } = render(<FileUpload onFileSelect={vi.fn()} />);

			const input = container.querySelector(
				'input[type="file"]',
			) as HTMLInputElement;
			fireEvent.change(input, { target: { files: [invalidFile] } });

			await waitFor(() => {
				expect(
					screen.getByText(/Only PDF, DOCX, TXT, and MD files are allowed/),
				).toBeInTheDocument();
			});
		});
	});

	describe("TemplateSelector", () => {
		it("renders template options", () => {
			const mockSelect = vi.fn();

			render(
				<TemplateSelector
					selectedTemplate={TemplateType.MODERN}
					onTemplateSelect={mockSelect}
				/>,
			);

			expect(screen.getAllByText("Modern")[0]).toBeInTheDocument();
			expect(screen.getByText("Professional")).toBeInTheDocument();
			expect(screen.getByText("Creative")).toBeInTheDocument();
		});

		it("handles template selection", async () => {
			const mockSelect = vi.fn();

			render(
				<TemplateSelector
					selectedTemplate={TemplateType.MODERN}
					onTemplateSelect={mockSelect}
				/>,
			);

			const professionalTemplate = screen.getByText("Professional");
			fireEvent.click(professionalTemplate);

			await waitFor(() => {
				expect(mockSelect).toHaveBeenCalledWith("professional");
			});
		});
	});

	describe("Analysis Components", () => {
		it("renders ATS score display", () => {
			render(<ATSScoreDisplay score={mockAnalysis.atsScore} />);

			expect(screen.getAllByText(/85/)[0]).toBeInTheDocument();
			expect(screen.getByText("Good")).toBeInTheDocument();
		});

		it("renders skills match", () => {
			render(
				<SkillsMatch
					matchedSkills={mockAnalysis.matchedSkills}
					missingSkills={mockAnalysis.missingSkills}
				/>,
			);

			expect(screen.getByText("React")).toBeInTheDocument();
			expect(screen.getByText("TypeScript")).toBeInTheDocument();
			expect(screen.getByText("Python")).toBeInTheDocument();
		});

		it("renders recommendations", () => {
			render(
				<RecommendationsList recommendations={mockAnalysis.recommendations} />,
			);

			expect(
				screen.getByText(/Add more quantifiable achievements/),
			).toBeInTheDocument();
		});
	});
});
