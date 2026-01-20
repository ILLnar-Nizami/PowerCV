import { apiClient } from './client'
import { Resume, DashboardFilters } from '@/types/resume'
import { PaginatedResponse } from '@/types/api'

export const resumesAPI = {
  getResumes: async (_filters: DashboardFilters, page = 1, pageSize = 20) => {
    const { data } = await apiClient.get<PaginatedResponse<Resume>>('/v1/resumes/user/local-user', {
      params: { page, pageSize },
    })
    return data
  },

  getResume: async (id: string) => {
    const { data } = await apiClient.get<Resume>(`/v1/resumes/${id}`)
    return data
  },

  updateStatus: async (id: string, status: string) => {
    const { data } = await apiClient.patch<Record<string, unknown>>(
      `/v1/resumes/${id}/status`,
      { application_status: status }
    )
    return data
  },

  deleteResume: async (id: string) => {
    await apiClient.delete(`/v1/resumes/${id}`)
  },

  downloadResume: async (id: string, template?: string) => {
    const response = await apiClient.get<Blob>(`/v1/resumes/${id}/download`, {
      params: { template },
      responseType: 'blob',
    })
    return response // Return full response to access headers
  },

  downloadOriginalResume: async (id: string) => {
    const { data } = await apiClient.get<Blob>(`/v1/resumes/${id}/download-original`, {
      responseType: 'blob',
    })
    return data
  },

  downloadCoverLetter: async (id: string) => {
    const { data } = await apiClient.get<Blob>(`/v1/resumes/${id}/cover-letter`, {
      responseType: 'blob',
    })
    return data
  },

  createResume: async (formData: FormData) => {
    const { data } = await apiClient.post<Record<string, string>>('/v1/resumes', formData, {
      headers: {
        'Content-Type': 'multipart/form-data',
      },
    })
    return data
  },

  optimizeResume: async (id: string, jobDescription: string, targetCompany?: string, targetRole?: string) => {
    const { data } = await apiClient.post<Record<string, unknown>>(`/v1/resumes/${id}/optimize`, {
      job_description: jobDescription,
      target_company: targetCompany,
      target_role: targetRole,
    })
    return data
  },

  scoreResume: async (id: string, jobDescription: string) => {
    const { data } = await apiClient.post<Record<string, unknown>>(`/v1/resumes/${id}/score`, {
      job_description: jobDescription,
    })
    return data
  },

  getTemplates: async () => {
    const { data } = await apiClient.get<Array<Record<string, unknown>>>('/v1/resumes/templates')
    return data
  },
}
