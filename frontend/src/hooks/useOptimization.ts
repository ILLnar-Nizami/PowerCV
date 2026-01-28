import { optimizationAPI } from "@/api/optimization";
import type {
	AnalysisResult,
	OptimizationRequest,
	OptimizationResult,
} from "@/types/optimization";
import { useMutation } from "@tanstack/react-query";
import { toast } from "sonner";

export function useAnalyzeResume() {
	return useMutation({
		mutationFn: (request: OptimizationRequest) =>
			optimizationAPI.analyze(request),
		onSuccess: (data: AnalysisResult) => {
			toast.success("Resume analysis completed");
			return data;
		},
		onError: () => {
			toast.error("Failed to analyze resume");
		},
	});
}

export function useOptimizeResume() {
	return useMutation({
		mutationFn: (request: OptimizationRequest) =>
			optimizationAPI.optimize(request),
		onSuccess: (data: OptimizationResult) => {
			toast.success("Resume optimization completed");
			return data;
		},
		onError: () => {
			toast.error("Failed to optimize resume");
		},
	});
}
