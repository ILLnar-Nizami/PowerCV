import { type CoverLetter, coverLettersAPI } from "@/api/coverLetters";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardHeader } from "@/components/ui/card";
import { Input } from "@/components/ui/input";
import { useQuery } from "@tanstack/react-query";
import { Download, FileText, Loader2, Mail, Plus, Search } from "lucide-react";
import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { toast } from "sonner";

export function CoverLetterPage() {
	const navigate = useNavigate();
	const [search, setSearch] = useState("");
	// Hardcoded user ID for now, similar to other parts of the app
	const userId = "local-user";

	const { data: coverLetters = [], isLoading } = useQuery({
		queryKey: ["coverLetters", userId],
		queryFn: () => coverLettersAPI.getUserCoverLetters(userId),
	});

	const filteredLetters = coverLetters.filter(
		(letter: CoverLetter) =>
			(letter.target_company || "")
				.toLowerCase()
				.includes(search.toLowerCase()) ||
			(letter.target_role || "").toLowerCase().includes(search.toLowerCase()),
	);

	const handleDownload = async (coverLetter: CoverLetter) => {
		try {
			const response = await coverLettersAPI.downloadCoverLetter(
				coverLetter._id,
			);
			const blob = response.data;
			const contentDisposition = response.headers["content-disposition"];

			let filename = `${coverLetter.target_company}_CoverLetter.pdf`;
			if (contentDisposition) {
				const filenameMatch = contentDisposition.match(/filename="?([^"]+)"?/);
				if (filenameMatch?.[1]) {
					filename = filenameMatch[1];
				}
			}

			const url = window.URL.createObjectURL(blob);
			const a = document.createElement("a");
			a.href = url;
			a.download = filename;
			a.click();
			window.URL.revokeObjectURL(url);
			toast.success("Download started");
		} catch (error) {
			console.error("Download failed:", error);
			toast.error("Failed to download cover letter");
		}
	};

	const formatDate = (dateString: string) => {
		return new Date(dateString).toLocaleDateString("en-US", {
			year: "numeric",
			month: "short",
			day: "numeric",
		});
	};

	if (isLoading) {
		return (
			<div className="flex justify-center items-center py-12">
				<Loader2 className="h-8 w-8 animate-spin text-muted-foreground" />
			</div>
		);
	}

	return (
		<div className="max-w-6xl mx-auto space-y-6">
			<div className="flex items-center justify-between">
				<div>
					<h1 className="text-3xl font-bold">Cover Letters</h1>
					<p className="text-muted-foreground">
						Manage your generated cover letters
					</p>
				</div>
				<Button onClick={() => navigate("/optimize")}>
					<Plus className="mr-2 h-4 w-4" />
					Generate New
				</Button>
			</div>

			<div className="flex gap-4 flex-wrap">
				<div className="relative flex-1 min-w-[300px]">
					<Search className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
					<Input
						placeholder="Search by company or position..."
						value={search}
						onChange={(e) => setSearch(e.target.value)}
						className="pl-10"
					/>
				</div>
			</div>

			{filteredLetters.length === 0 ? (
				<Card className="text-center py-12">
					<CardContent>
						<Mail className="h-12 w-12 text-muted-foreground mx-auto mb-4" />
						<h3 className="text-lg font-semibold mb-2">
							No Cover Letters Found
						</h3>
						<p className="text-muted-foreground mb-4">
							{search
								? "Try adjusting your search terms"
								: "Generate your first cover letter to get started"}
						</p>
						<Button onClick={() => navigate("/optimize")}>
							<FileText className="mr-2 h-4 w-4" />
							Generate Cover Letter
						</Button>
					</CardContent>
				</Card>
			) : (
				<>
					<div className="flex items-center gap-2 text-sm text-muted-foreground">
						<span>
							{filteredLetters.length} Cover Letter
							{filteredLetters.length !== 1 ? "s" : ""}
						</span>
						{search && <span>filtered by "{search}"</span>}
					</div>

					<div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
						{filteredLetters.map((letter: CoverLetter) => (
							<Card key={letter._id}>
								<CardHeader>
									<div className="space-y-1">
										<h3 className="font-semibold text-lg">
											{letter.target_role || "Unknown Role"}
										</h3>
										<p className="text-sm text-muted-foreground">
											{letter.target_company || "Unknown Company"}
										</p>
									</div>
								</CardHeader>

								<CardContent className="space-y-4">
									<div className="flex items-center justify-between text-sm">
										<span className="text-muted-foreground">Generated:</span>
										<span className="font-medium">
											{formatDate(letter.created_at)}
										</span>
									</div>

									<div className="flex items-center justify-between text-sm">
										<span className="text-muted-foreground">Type:</span>
										<Badge variant="secondary">AI Generated</Badge>
									</div>

									<Button
										onClick={() => handleDownload(letter)}
										className="w-full"
										variant="outline"
									>
										<Download className="mr-2 h-4 w-4" />
										Download Cover Letter
									</Button>
								</CardContent>
							</Card>
						))}
					</div>
				</>
			)}
		</div>
	);
}
