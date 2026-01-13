import { apiClient } from './client'
import { OptimizationRequest, AnalysisResult, OptimizationResult, Recommendation } from '@/types/optimization'

// Backend response structure - keywords can be strings or objects
interface KeywordItem {
  keyword: string
  category?: string
  priority?: string
}

interface BackendAnalysisResponse {
  ats_score?: number
  keyword_analysis?: {
    matched_keywords?: Array<KeywordItem | string>
    missing_critical?: Array<KeywordItem | string>
  }
  recommendations?: string[]
  summary?: string
}

interface BackendOptimizationResponse {
  resume_id?: string
  resumeId?: string
  improvements?: string[]
  optimizedResumeUrl?: string
  coverLetterUrl?: string
  cover_letter?: string
  coverLetter?: string
  ats_score?: number
  matching_skills?: string[]
  missing_skills?: string[]
  analysisResult?: AnalysisResult
  analysis?: Record<string, unknown>
  optimized_resume?: string
}

// Helper to extract keyword string from various formats
function extractKeyword(item: KeywordItem | string): string {
  if (typeof item === 'string') return item
  if (item && typeof item === 'object' && 'keyword' in item) return item.keyword
  return String(item)
}

// Helper to get CV text from request
async function getCvText(request: OptimizationRequest): Promise<string> {
  if (request.sourceType === 'upload' && request.uploadedFile) {
    return new Promise((resolve, reject) => {
      const reader = new FileReader()
      reader.onload = (e) => resolve(e.target?.result as string)
      reader.onerror = reject
      reader.readAsText(request.uploadedFile as File)
    })
  } else if (request.sourceType === 'master_cv' && request.sourceId) {
    const { data } = await apiClient.get(`/resume/master-cv/${request.sourceId}`)
    return data.master_content || ''
  }
  throw new Error('Invalid request: missing CV source')
}

// Transform backend response to frontend format
function transformAnalysisResponse(data: BackendAnalysisResponse): AnalysisResult {
  const matchedKeywords = data.keyword_analysis?.matched_keywords || []
  const missingKeywords = data.keyword_analysis?.missing_critical || []
  const rawRecommendations = data.recommendations || []

  // Transform recommendations to proper format
  const recommendations: Recommendation[] = rawRecommendations.map((rec, index) => {
    let severity: 'high' | 'medium' | 'low' = 'low'
    if (index === 0) severity = 'high'
    else if (index < 3) severity = 'medium'

    return {
      category: 'skills' as const,
      severity,
      message: typeof rec === 'string' ? rec : String(rec),
      suggestion: ''
    }
  })

  return {
    atsScore: data.ats_score || 0,
    matchedSkills: matchedKeywords.map(extractKeyword),
    missingSkills: missingKeywords.map(extractKeyword),
    recommendations
  }
}

// Transform backend optimization response to frontend format
function transformOptimizationResponse(data: BackendOptimizationResponse): OptimizationResult {
  return {
    resumeId: data.resume_id || data.resumeId,
    improvements: data.improvements || (data.optimized_resume ? ['Resume optimized successfully'] : []),
    optimizedResumeUrl: data.optimizedResumeUrl || '',
    coverLetterUrl: data.coverLetterUrl,
    coverLetter: data.cover_letter || data.coverLetter || '',
    ats_score: data.ats_score,
    matching_skills: data.matching_skills,
    missing_skills: data.missing_skills,
    analysisResult: data.analysisResult,
    analysis: data.analysis,
    optimizedResume: data.optimized_resume || ''
  }
}

export const optimizationAPI = {
  analyze: async (request: OptimizationRequest) => {
    const cvText = await getCvText(request)

    const analysisPayload = {
      job_description: request.jobDescription,
      resume_text: cvText
    }
    const { data } = await apiClient.post<BackendAnalysisResponse>(
      '/comprehensive/analyze/ats',
      analysisPayload
    )
    return transformAnalysisResponse(data)
  },

  optimize: async (request: OptimizationRequest) => {
    const cvText = await getCvText(request)

    const optimizePayload = {
      target_role: request.position || 'Professional',
      job_description: request.jobDescription,
      resume_text: cvText,
      target_company: request.company || '',
      focus_area: 'backend/data/DevOps/leadership'
    }
    const { data } = await apiClient.post(
      '/comprehensive/optimize/master',
      optimizePayload
    )
    return transformOptimizationResponse(data)
  },

  getComprehensiveOptimization: async (request: OptimizationRequest) => {
    const cvText = await getCvText(request)

    const compPayload = {
      target_role: request.position || 'Professional',
      job_description: request.jobDescription,
      resume_text: cvText,
      target_company: request.company || '',
      focus_area: 'backend/data/DevOps/leadership'
    }
    const { data } = await apiClient.post<Record<string, unknown>>(
      '/comprehensive/optimize/master',
      compPayload
    )
    return data
  },
}
