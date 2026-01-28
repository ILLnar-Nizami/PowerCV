import { resumesAPI } from "@/api/resumes";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { useOptimizationStore } from "@/stores/optimizationStore";
import { ArrowLeft, Download, Eye, FileText, Mail, Share } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";

export function ResultsPage() {
	const navigate = useNavigate();
	const [isDownloading, setIsDownloading] = useState<"resume" | "cover" | null>(
		null,
	);
	const { result, request } = useOptimizationStore();

	// Debug logging
	console.log("ResultsPage result:", result);
	console.log("ResultsPage result.resumeId:", result?.resumeId);
	console.log("ResultsPage result.resume_id:", result?.resume_id);

	// Fallback to mock data if no result
	// Redirect if no result
	if (!result) {
		navigate("/optimize");
		return null;
	}

	const resultData = result;

	// Normalize the data structure for consistent access
	const atsScore = Number(
		resultData.ats_score ||
			(resultData.analysis as { ats_score?: number })?.ats_score ||
			0,
	);
	const originalAtsScore = Number(resultData.original_ats_score || 0);
	const improvement = atsScore - originalAtsScore;
	const matchedSkills = (resultData.matching_skills ||
		(resultData.analysis as { matchedSkills?: string[] })?.matchedSkills ||
		[]) as string[];
	const improvements = (resultData.improvements || []) as string[];

	const handleDownloadResume = async () => {
		setIsDownloading("resume");
		try {
			// Map template enum to actual template path for download
			const templateMap: Record<string, string> = {
				modern: "modern.typ",
				classic: "resume.typ",
				professional: "brilliant-cv/cv.typ",
				creative: "awesome-cv/cv.tex",
				minimal: "simple-xd-resume/cv.typ",
			};
			const templatePath =
				templateMap[request.template || "classic"] || "resume.typ";
			const resumeId = resultData.resumeId || "";
			if (!resumeId) throw new Error("Resume ID required");

			const response = await resumesAPI.downloadResume(resumeId, templatePath);
			const blob = response.data;
			const contentDisposition = response.headers["content-disposition"];
			let filename = `resume_optimized_${resultData.resumeId}.pdf`;

			if (contentDisposition) {
				const customFilename = contentDisposition
					.split("filename=")[1]
					?.replace(/['"]/g, "");
				if (customFilename) {
					filename = customFilename;
				}
			}

			const url = window.URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = filename;
			a.click();
			window.URL.revokeObjectURL(url);
		} catch (error) {
			console.error("Download failed:", error);
		} finally {
			setIsDownloading(null);
		}
	};

	const handleDownloadCoverLetter = async () => {
		setIsDownloading("cover");
		try {
			// For now, download as text file since there's no dedicated endpoint
			const coverLetterContent =
				result?.coverLetter || "Cover letter not available";
			const blob = new Blob([coverLetterContent], { type: "text/plain" });
			const url = window.URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			const company = (request.company || "Company")
				.toLowerCase()
				.replace(/[^a-z0-9]/g, "-");
			const position = (request.position || "Position")
				.toLowerCase()
				.replace(/[^a-z0-9]/g, "_");
			const date = new Date().toLocaleDateString("en-GB").replace(/\//g, ".");
			// Initial could be improved if user info available, defaulting to 'u' (user) or similar if not
			const filename = `cl_candidate_${company}_${position}_${date}.txt`;

			a.download = filename;
			a.click();
			window.URL.revokeObjectURL(url);
		} catch (error) {
			console.error("Download failed:", error);
		} finally {
			setIsDownloading(null);
		}
	};

	const handlePreview = () => {
		// Map template enum to actual template path for preview
		const templateMap: Record<string, string> = {
			modern: "modern.typ",
			classic: "resume.typ",
			professional: "brilliant-cv/cv.typ",
			creative: "awesome-cv/cv.tex",
			minimal: "simple-xd-resume/cv.typ",
		};
		const templatePath =
			templateMap[request.template || "classic"] || "resume.typ";
		window.open(
			`/api/resume/${resultData.resumeId}/download?template=${encodeURIComponent(templatePath)}`,
			"_blank",
		);
	};

	const handleShare = () => {
		// TODO: Implement share functionality
		if (navigator.share) {
			navigator.share({
				title: "My Optimized Resume",
				text: "Check out my newly optimized resume!",
				url: window.location.href,
			});
		} else {
			navigator.clipboard.writeText(window.location.href);
		}
	};

	const handleBackToDashboard = () => {
		navigate("/dashboard");
	};

	const handleCreateNew = () => {
		navigate("/optimize");
	};

	return (
		<div className="max-w-6xl mx-auto space-y-6">
			<div className="flex items-center gap-4">
				<Button variant="ghost" onClick={() => navigate("/analysis")}>
					<ArrowLeft className="mr-2 h-4 w-4" />
					Back
				</Button>
				<div>
					<h1 className="text-3xl font-bold">Optimization Complete!</h1>
					<p className="text-muted-foreground">
						Your resume has been successfully optimized
					</p>
				</div>
			</div>

			<div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
				<div className="lg:col-span-2 space-y-6">
					<Card>
						<CardHeader>
							<CardTitle className="flex items-center gap-2">
								<FileText className="h-5 w-5" />
								Optimized Resume
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-4">
							<div
								className={`flex items-center justify-between p-4 rounded-lg ${
									atsScore >= 76
										? "bg-green-50 border border-green-200"
										: atsScore >= 60
											? "bg-yellow-50 border border-yellow-200"
											: "bg-red-50 border border-red-200"
								}`}
							>
								<div className="flex gap-8">
									<div>
										<div
											className={`text-sm font-medium ${
												atsScore >= 76
													? "text-green-800"
													: atsScore >= 60
														? "text-yellow-800"
														: "text-red-800"
											}`}
										>
											ATS Score
										</div>
										<div
											className={`text-2xl font-bold ${
												atsScore >= 76
													? "text-green-900"
													: atsScore >= 60
														? "text-yellow-900"
														: "text-red-900"
											}`}
										>
											{atsScore}%
										</div>
									</div>

									{originalAtsScore > 0 && (
										<div className="border-l border-gray-200 pl-8">
											<div className="text-sm text-muted-foreground font-medium">
												Original
											</div>
											<div className="text-xl font-semibold text-muted-foreground">
												{originalAtsScore}%
											</div>
										</div>
									)}

									{improvement !== 0 && (
										<div className="border-l border-gray-200 pl-8">
											<div className="text-sm text-muted-foreground font-medium">
												Improvement
											</div>
											<div
												className={`text-xl font-bold ${improvement > 0 ? "text-green-600" : "text-red-600"}`}
											>
												{improvement > 0 ? `+${improvement}` : improvement}%
											</div>
										</div>
									)}
								</div>
								<Badge
									variant="default"
									className={
										atsScore >= 76
											? "bg-green-500"
											: atsScore >= 60
												? "bg-yellow-500"
												: "bg-red-500"
									}
								>
									{atsScore >= 76
										? "Excellent"
										: atsScore >= 60
											? "Good"
											: "Poor"}
								</Badge>
							</div>

							<div className="space-y-3">
								<h3 className="font-semibold">Improvements Made:</h3>
								<ul className="space-y-2">
									{improvements.map((improvement: string) => (
										<li
											key={improvement}
											className="flex items-start gap-2 text-sm"
										>
											<div className="w-2 h-2 bg-green-500 rounded-full mt-2 flex-shrink-0" />
											{improvement}
										</li>
									))}
								</ul>
							</div>

							<div className="flex gap-3 pt-4">
								<Button
									onClick={handleDownloadResume}
									disabled={isDownloading === "resume"}
									className="flex-1"
								>
									<Download className="mr-2 h-4 w-4" />
									{isDownloading === "resume"
										? "Downloading..."
										: "Download Resume"}
								</Button>
								<Button variant="outline" onClick={handlePreview}>
									<Eye className="mr-2 h-4 w-4" />
									Preview
								</Button>
							</div>
						</CardContent>
					</Card>

					<Card>
						<CardHeader>
							<CardTitle className="flex items-center gap-2">
								<Mail className="h-5 w-5" />
								Cover Letter
							</CardTitle>
						</CardHeader>
						<CardContent className="space-y-4">
							<p className="text-sm text-muted-foreground">
								A personalized cover letter has been generated based on your
								resume and the job description.
							</p>
							<Button
								onClick={handleDownloadCoverLetter}
								disabled={isDownloading === "cover"}
								variant="outline"
								className="w-full"
							>
								<Download className="mr-2 h-4 w-4" />
								{isDownloading === "cover"
									? "Downloading..."
									: "Download Cover Letter"}
							</Button>
						</CardContent>
					</Card>
				</div>

				<div className="space-y-6">
					<Card>
						<CardHeader>
							<CardTitle>Quick Actions</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							<Button
								onClick={handleShare}
								variant="outline"
								className="w-full"
							>
								<Share className="mr-2 h-4 w-4" />
								Share Results
							</Button>
							<Button
								onClick={handleCreateNew}
								variant="outline"
								className="w-full"
							>
								<FileText className="mr-2 h-4 w-4" />
								Create New Resume
							</Button>
							<Button onClick={handleBackToDashboard} className="w-full">
								<FileText className="mr-2 h-4 w-4" />
								Back to Dashboard
							</Button>
						</CardContent>
					</Card>

					<Card>
						<CardHeader>
							<CardTitle>Skills Match</CardTitle>
						</CardHeader>
						<CardContent className="space-y-3">
							<div className="text-sm">
								<div className="flex justify-between mb-2">
									<span>Matched Skills</span>
									<Badge variant="default">{matchedSkills.length}</Badge>
								</div>
								<div className="flex flex-wrap gap-1">
									{matchedSkills.map((skill: string) => (
										<Badge key={skill} variant="secondary" className="text-xs">
											{skill}
										</Badge>
									))}
								</div>
							</div>
						</CardContent>
					</Card>
				</div>
			</div>
		</div>
	);
}
