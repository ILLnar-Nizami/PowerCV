import { apiClient } from "./client";

export interface CoverLetter {
	_id: string;
	resume_id: string;
	target_company: string;
	target_role: string;
	content_data?: {
		sender_name?: string;
	};
	created_at: string;
	updated_at: string;
}

export const coverLettersAPI = {
	getUserCoverLetters: async (userId: string) => {
		const response = await apiClient.get<CoverLetter[]>(
			`/cover-letter/user/${userId}`,
		);
		return response.data;
	},

	downloadCoverLetter: async (id: string) => {
		// Return full response to access headers for filename
		const response = await apiClient.get(`/cover-letter/${id}/download`, {
			responseType: "blob",
		});
		return response;
	},
};
