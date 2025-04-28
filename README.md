# Resume Analyzer 🧠📄
### Resume Analyzer is an AI-powered web application designed for employers and recruiters to efficiently manage and evaluate a database of candidate resumes.
### Built using Flask, Azure OpenAI (GPT-4), and Plotly, this platform enables dynamic resume parsing, candidate evaluation, and skill visualization — all through a seamless, interactive dashboard.

## ✨ Key Features:
### - Resume Parsing: Automatically extract structured information (skills, education, work history, projects) from PDF and DOCX resumes.
### - Candidate Evaluation:
###   - Generate technical and behavioral interview questions tailored to each candidate.
###   - Predict likely future career paths based on experience and skills.
###   - Visualize resume timelines with interactive Plotly charts.
###   - Detect potential resume red flags (employment gaps, job hopping, inconsistencies).
### - Database-Level Insights:
###   - Generate skill heatmaps across all uploaded candidates.
###   - Match a database of resumes to a job description and identify top 5 candidates.
### - Optimized Batch Processing:
###   - Smart large-prompt batching to comply with Azure OpenAI rate limits and minimize API overhead.
###   - Secure file upload handling with scalable multi-resume ingestion pipelines.

## 🛠 Tech Stack:
### - Backend: Flask, Python
### - AI Integration: Azure OpenAI (GPT-4 API)
### - Text Extraction: PyMuPDF (for PDFs), python-docx (for DOCX)
### - Visualization: Plotly Express, Pandas
### - Deployment Ready: Environment variable management for secure API key handling
