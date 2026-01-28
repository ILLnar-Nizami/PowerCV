import type { MasterCV } from "@/types/resume";
import { apiClient } from "./client";

export const masterCVAPI = {
	getAll: async () => {
		const { data } = await apiClient.get<MasterCV[]>(
			"/v1/resumes/master-cv/user/local-user",
		);
		return data;
	},

	upload: async (file: File) => {
		const formData = new FormData();
		formData.append("file", file);

		const { data } = await apiClient.post<Record<string, string>>(
			"/v1/resumes/master-cv/upload",
			formData,
			{
				headers: { "Content-Type": "multipart/form-data" },
			},
		);
		return data;
	},

	delete: async (id: string) => {
		await apiClient.delete(`/v1/resumes/master-cv/${id}`);
	},

	getById: async (id: string) => {
		const { data } = await apiClient.get<MasterCV>(
			`/v1/resumes/master-cv/${id}`,
		);
		return data;
	},

	download: async (id: string) => {
		const { data } = await apiClient.get<Blob>(
			`/v1/resumes/master-cv/${id}/download`,
			{
				responseType: "blob",
			},
		);
		return data;
	},
};
