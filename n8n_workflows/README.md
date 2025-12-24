# PowerCV n8n Integration

This directory contains n8n workflow templates and instructions for integrating PowerCV with n8n automation.

## Quick Start

1. **Access n8n**: Open http://localhost:5678 in your browser
2. **Login**: Use credentials from.env file (admin/secure_n8n_password_123!)
3. **Import Workflow**: Create a new workflow from scratch using the instructions below

## Workflow Setup

### Basic CV Analysis Workflow

1. **Webhook Node**
 - Trigger: Webhook
 - HTTP Method: POST
 - Path: cv-analysis
 - Response Mode: Respond immediately

2. **HTTP Request Node** (Analyze CV)
 - URL: http://powercv-api:8080/api/n8n/analyze
 - Method: POST
 - Authentication: Header Auth
 - Headers:
 - X-API-Key: n8n_sec_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2
 - Content-Type: application/json
 - Body JSON:
 ``json
 {
 "cv_text": "={{ $json.body.cv_text }}",
 "jd_text": "={{ $json.body.jd_text }}",
 "user_id": "={{ $json.body.user_id || 'n8n_workflow' }}"
 }
 `

3. **Respond to Webhook Node**
 - Respond with: JSON
 - Response Body: {{ $node['Analyze CV'].json }}

### Full CV Optimization Workflow

Add these nodes after the analysis:

4. **If Node** (Check Success)
 - Condition: {{ $node['Analyze CV'].json.success }} == true

5. **HTTP Request Node** (Optimize CV)
 - URL: http://powercv-api:8080/api/n8n/optimize
 - Same authentication as analyze
 - Body JSON:
 `json
 {
 "cv_text": "={{ $node['Webhook'].json.body.cv_text }}",
 "jd_text": "={{ $node['Webhook'].json.body.jd_text }}",
 "user_id": "={{ $node['Webhook'].json.body.user_id || 'n8n_workflow' }}",
 "generate_cover_letter": "={{ $node['Webhook'].json.body.generate_cover_letter || true }}"
 }
 `

6. **Respond to Webhook Node** (Success)
 - Response Body: {{ $node['Optimize CV'].json }}

7. **Respond to Webhook Node** (Error)
 - Response Body: 
 `json
 {
 "success": false,
 "error": "CV analysis failed",
 "details": "={{ $node['Analyze CV'].json }}"
 }
 `

## API Endpoints Reference

### PowerCV n8n API

All endpoints require the API key header: X-API-Key: n8n_sec_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2

### API Endpoints Available

- **Health Check**: GET /api/n8n/health
- **Analyze CV**: POST /api/n8n/analyze
- **Optimize CV**: POST /api/n8n/optimize
- **List Providers**: GET /api/n8n/providers (Cerebras only)

### Request/Response Examples

#### Analyze CV Request
`json
{
 "cv_text": "Python Developer with 5 years experience...",
 "jd_text": "Looking for a Senior Python Developer...",
 "user_id": "test_user"
}
`

#### Analyze CV Response
`json
{
 "success": true,
 "ats_score": 90,
 "matched_keywords": [...],
 "missing_keywords": [...],
 "top_recommendations": [...],
 "user_id": "test_user"
}
`

#### Optimize CV Request
`json
{
 "cv_text": "Python Developer with 5 years experience...",
 "jd_text": "Looking for a Senior Python Developer...",
 "user_id": "test_user",
 "generate_cover_letter": true
}
`

## Docker Services

- **PowerCV API**: http://localhost:8080
- **n8n Interface**: http://localhost:5678
- **MongoDB**: mongodb://localhost:27018/powercv

## Environment Variables

Key variables for n8n integration (in.env):
- N8N_API_KEY: API key for authenticating n8n requests
- N8N_USER: n8n admin username
- N8N_PASSWORD: n8n admin password
- AI_PROVIDER: Current AI provider (cerebras)
- MONGODB_URI: MongoDB connection string

## Testing

Use curl to test endpoints directly:

`bash
# Health check
curl -H "X-API-Key: n8n_sec_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2" \
 http://localhost:8080/api/n8n/health

# Analyze CV
curl -X POST -H "Content-Type: application/json" \
 -H "X-API-Key: n8n_sec_a1b2c3d4e5f6g7h8i9j0k1l2m3n4o5p6q7r8s9t0u1v2w3x4y5z6a7b8c9d0e1f2" \
 -d '{"cv_text":"Python Developer...","jd_text":"Looking for...","user_id":"test"}' \
 http://localhost:8080/api/n8n/analyze
``
