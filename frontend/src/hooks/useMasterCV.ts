import { masterCVAPI } from "@/api/masterCV";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { toast } from "sonner";

export function useMasterCVs() {
	return useQuery({
		queryKey: ["master-cvs"],
		queryFn: () => masterCVAPI.getAll(),
	});
}

export function useMasterCV(id: string) {
	return useQuery({
		queryKey: ["master-cv", id],
		queryFn: () => masterCVAPI.getById(id),
		enabled: !!id,
	});
}

export function useUploadMasterCV() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (file: File) => masterCVAPI.upload(file),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["master-cvs"] });
			toast.success("Master CV uploaded successfully");
		},
		onError: () => {
			toast.error("Failed to upload Master CV");
		},
	});
}

export function useDeleteMasterCV() {
	const queryClient = useQueryClient();

	return useMutation({
		mutationFn: (id: string) => masterCVAPI.delete(id),
		onSuccess: () => {
			queryClient.invalidateQueries({ queryKey: ["master-cvs"] });
			toast.success("Master CV deleted successfully");
		},
		onError: () => {
			toast.error("Failed to delete Master CV");
		},
	});
}

export function useDownloadMasterCV() {
	return useMutation({
		mutationFn: async (id: string) => {
			const response = await masterCVAPI.download(id);
			return response;
		},
		onSuccess: (data, id) => {
			const url = window.URL.createObjectURL(data);
			const a = document.createElement("a");
			a.href = url;
			a.download = `master_cv_${id}`; // Fallback name, ideally get from headers if possible
			a.click();
			window.URL.revokeObjectURL(url);
			toast.success("Master CV downloaded successfully");
		},
		onError: () => {
			toast.error("Failed to download Master CV");
		},
	});
}
