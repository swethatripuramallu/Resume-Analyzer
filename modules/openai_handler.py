import openai
from config import Config
import os
from modules.file_handler import handle_file_upload, extract_text_from_pdf, extract_text_from_docx



# Initialize the OpenAI client
# client = OpenAI(api_key=Config.OPENAI_API_KEY)
client = openai.AzureOpenAI(
    api_key=Config.OPENAI_API_KEY,
    api_version="2024-08-01-preview",
    azure_endpoint="https://siskind-openai.openai.azure.com/",
)


def extract_information_with_gpt(text):
    """
    Use OpenAI GPT to extract structured information like name, location, nationality, organization, 
    education, skills, projects, tools, and other relevant info.
    This version also extracts the last two jobs, their timelines, and responsibilities.
    """
    prompt = (
        "You are a resume parser. Extract the following information from the resume text: "
        "1. The full name of the person. "
        "2. Their current location and nationality. "
        "3. Any useful links (LinkedIn, personal website, GitHub, etc.). "
        "4. The two most recent jobs, including the organization, organization location, job title, timeline (start and end dates)"
        "5. Their education details (schools, degrees, and dates if available). "
        "6. A list of hard skills. "
        "7. A list of soft skills. "
        "8. Tools and technologies they are familiar with. "
        "9. A list of their major projects. "
        "10. Any other relevant details (certifications, awards, etc.). "
        "Return the results in the following structured format:\n\n"
        "Name: <person's name>\n"
        "Location: <City, State>\n"
        "Nationality: <nationality>\n"
        "Useful Links: <useful links>\n"
        "Job 1: <organization>, <job title>, <start date> - <end date>\n"
        "Responsibilities 1: <list of responsibilities for job 1>\n"
        "Job 2: <organization>, <job title>, <start date> - <end date>\n"
        "Responsibilities 2: <list of responsibilities for job 2>\n"
        "Education: <education details>\n"
        "Hard Skills: <list of hard skills>\n"
        "Soft Skills: <list of soft skills>\n"
        "Tools: <list of tools>\n"
        "Projects: <list of projects>\n"
        "Other Relevant Info: <certifications, awards, etc.>\n\n"
        f"Resume Text: {text}"
    )

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=2000,
        temperature=0.5
    
    )
    
    print(response.choices[0].message.content.strip())

    return response.choices[0].message.content.strip()

def generate_summary(name, job1, job2, education, hard_skills, soft_skills, tools, projects, other_info):
    """
    Use OpenAI GPT to generate a professional summary based on extracted details, including the last two jobs.
    """
    prompt = (
        f"Generate a professional summary based on the following details:\n"
        f"Name: {name}\n"
        f"Most Recent Job: {job1['organization']}, {job1['job_title']}, {job1['start_date']} - {job1['end_date']}\n"
        f"Responsibilities: {', '.join(job1['responsibilities'])}\n"
        f"Second Most Recent Job: {job2['organization']}, {job2['job_title']}, {job2['start_date']} - {job2['end_date']}\n"
        f"Responsibilities: {', '.join(job2['responsibilities'])}\n"
        f"Education: {', '.join(education)}\n"
        f"Hard Skills: {', '.join(hard_skills)}\n"
        f"Soft Skills: {', '.join(soft_skills)}\n"
        f"Tools: {', '.join(tools)}\n"
        f"Projects: {', '.join(projects)}\n"
        f"Other Info: {other_info}"
    )

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=700,
        temperature=0.5
    )
    
    return response.choices[0].message.content.strip()
   
def recommendations(name, job1, job2, education, hard_skills, soft_skills, tools, projects, other_info):
    """
    Based on the following resume summary, recommend 3 job titles and 3 companies the candidate may be a good fit for. Then generate 5 technical and 3 behavioral interview questions tailored to the resume.
    """
    prompt = (
        f"You are a career recommendation assistant. Use only the information provided below.\n\n"

        f"--- CANDIDATE INFO ---\n"
        f"Name: {name}\n\n"

        f"Most Recent Job:\n"
        f"Organization: {job1['organization']}\n"
        f"Title: {job1['job_title']}\n"
        f"Dates: {job1['start_date']} - {job1['end_date']}\n"
        f"Responsibilities: {', '.join(job1['responsibilities'])}\n\n"

        f"Second Most Recent Job:\n"
        f"Organization: {job2['organization']}\n"
        f"Title: {job2['job_title']}\n"
        f"Dates: {job2['start_date']} - {job2['end_date']}\n"
        f"Responsibilities: {', '.join(job2['responsibilities'])}\n\n"

        f"Education: {', '.join(education)}\n"
        f"Hard Skills: {', '.join(hard_skills)}\n"
        f"Soft Skills: {', '.join(soft_skills)}\n"
        f"Tools: {', '.join(tools)}\n"
        f"Projects: {', '.join(projects)}\n"
        f"Other Info: {other_info}\n\n"

        f"--- TASKS ---\n"
        # f"1. Recommend 3 specific job titles that align with this candidate’s background.\n"
        # f"2. Suggest 3 real-world companies (well-known or industry-specific) where this candidate could be a strong fit.\n"
        f"3. Write 5 technical interview questions that test the candidate’s skillset as described.\n"
        f"4. Write 3 behavioral interview questions tailored to the candidate’s experience.\n\n"

        f"Only use the data above. Do not fabricate any information or assume unlisted qualifications. Be concise and accurate." 
    )

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=700,
        temperature=0.5
    )
    print(response.choices[0].message.content.strip())
    return response.choices[0].message.content.strip()

def get_match_score(name, job1, job2, education, hard_skills, soft_skills, tools, projects, other_info, job_description):
    """
    Use OpenAI GPT to generate a professional summary based on extracted details, including the last two jobs.
    """
    prompt = (
        f"Generate a professional summary based on the following details:\n"
        f"Name: {name}\n"
        f"Most Recent Job: {job1['organization']}, {job1['job_title']}, {job1['start_date']} - {job1['end_date']}\n"
        f"Responsibilities: {', '.join(job1['responsibilities'])}\n"
        f"Second Most Recent Job: {job2['organization']}, {job2['job_title']}, {job2['start_date']} - {job2['end_date']}\n"
        f"Responsibilities: {', '.join(job2['responsibilities'])}\n"
        f"Education: {', '.join(education)}\n"
        f"Hard Skills: {', '.join(hard_skills)}\n"
        f"Soft Skills: {', '.join(soft_skills)}\n"
        f"Tools: {', '.join(tools)}\n"
        f"Projects: {', '.join(projects)}\n"
        f"Other Info: {other_info}"
        f"Job Description:\n{job_description}\n\n"
        f"Now, please provide:\n"
        f"1. Overall match score (0-100) as 'Score: <number>'\n"
        f"2. A list of strong matching areas under 'Strengths:'\n"
        f"3. A list of areas for improvement under 'Improvements:'\n"
        f"Format your response exactly like this:\n\n"
        f"Score: <number>\n"
        f"Strengths:\n"
        f"- Point 1\n"
        f"- Point 2\n"
        f"...\n"
        f"Improvements:\n"
        f"- Point 1\n"
        f"- Point 2\n"
    )

    response = client.chat.completions.create(
        model="gpt-4",  # or "gpt-3.5-turbo"
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=700,
        temperature=0.5
    
    )

    return response.choices[0].message.content.strip()

def extract_all_skills(upload_folder):
    """
    Extract all skills from multiple resumes using one API call.
    Returns: dict { filename: [skills] }, and prints each set.
    """
    resume_data = []

    # Load resume text
    for filename in os.listdir(upload_folder):
        if filename.endswith(".pdf") or filename.endswith(".docx"):
            filepath = os.path.join(upload_folder, filename)
            try:
                if filename.endswith(".pdf"):
                    text = extract_text_from_pdf(filepath)
                else:
                    text = extract_text_from_docx(filepath)
                resume_data.append((filename, text))  # Trim to save tokens
            except Exception as e:
                print(f"Error reading {filename}: {e}")
                continue

    if not resume_data:
        return {}

    # Build batched prompt
    prompt = (
        "You are a resume parser. For each resume below, extract all skills (hard skills, soft skills, tools, technologies).\n"
        "Return them in this format:\n"
        "=== Resume: <filename> ===\n"
        "Skills: skill1, skill2, skill3\n\n"
    )

    for filename, text in resume_data:
        prompt += f"=== Resume: {filename} ===\n{text}\n\n"

    # Send one GPT call
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=4000,
        temperature=0.3
    )

    raw_output = response.choices[0].message.content.strip()
    return parse_batch_skills(raw_output)

def parse_batch_skills(raw_output):
    """
    Parses GPT response into { filename: [skills] } format.
    """
    skill_map = {}
    sections = raw_output.split("=== Resume:")
    for section in sections:
        lines = section.strip().split("\n")
        if not lines or "Skills:" not in lines[-1]:
            continue
        try:
            filename = lines[0].strip()
            skills_line = next((line for line in lines if line.startswith("Skills:")), "")
            skills = [s.strip() for s in skills_line.replace("Skills:", "").split(',') if s.strip()]
            skill_map[filename] = skills
            print(f"{filename}: {', '.join(skills)}")
        except Exception as e:
            print(f"Error parsing section: {e}")
            continue
    return skill_map




def process_all_resumes_together(upload_folder, job_description):
    resume_data = []

    # Step 1: Read all resume text files
    for filename in os.listdir(upload_folder):
        if filename.endswith(".pdf") or filename.endswith(".docx"):
            filepath = os.path.join(upload_folder, filename)
            try:
                if filename.endswith(".pdf"):
                    text = extract_text_from_pdf(filepath)
                else:
                    text = extract_text_from_docx(filepath)
                resume_data.append((filename, text))
            except Exception as e:
                print(f"Error reading {filename}: {e}")

    if not resume_data:
        return []

    # Step 2: Build single prompt with all resumes
    prompt = (
        f"You are a hiring assistant. You will receive multiple resumes and a job description: {job_description}\n"
        "For each resume, extract:\n"
        "- Name\n"
        "- All jobs\n"
        "- Responsibilities\n"
        "- Education\n"
        "- Hard Skills, Soft Skills, Tools, Projects, Certifications\n"
        "Then evaluate the resume against the job description and return:\n"
        "- Match Score (0–100)\n"
        "- Top Skill: (A skill that they are a master in based on overall job experience)\n\n"
        "Format for each resume:\n"
        "=== Resume: <filename> ===\n"
        "Name: ...\n"
        "Score: <number>\n"
        "Top Skill: ...\n\n"
        
    )

    for filename, text in resume_data:
        prompt += f"=== Resume: {filename} ===\n{text}\n\n"

    # Step 3: Make the GPT call
    try:
        response = client.chat.completions.create(
            model="gpt-4",  # Replace with your actual deployment name
            messages=[
                {"role": "system", "content": "You are a helpful assistant."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=3000,
            temperature=0.5
        )
    except Exception as e:
        print("OpenAI call failed:", e)
        return []

    output = response.choices[0].message.content.strip()
    print(output)
    return parse_batch_response(output)

def parse_batch_response(response_text):
    """
    Splits GPT's output into individual candidate objects.
    """
    candidates = []
    sections = response_text.split("=== Resume:")
    for section in sections:
        if not section.strip():
            continue
        try:
            lines = section.strip().split("\n")
            filename = lines[0].replace("===", "").strip()
            data = "\n".join(lines[1:])
            candidate = {"filename": filename, "raw": data}

            # Extract Score
            for line in lines:
                if line.startswith("Score:"):
                    candidate['score'] = int(line.split(":")[1].strip())
                elif line.startswith("Top Skill:"):
                    candidate['skill_badge'] = line.split(":")[1].strip()
                elif line.startswith("Name:"):
                    candidate['name'] = line.split(":")[1].strip()

            candidates.append(candidate)
        except Exception as e:
            print(f"Error parsing candidate section: {e}")
            continue

    # Sort by score and return top 5
    candidates.sort(key=lambda x: x.get("score", 0), reverse=True)
    return candidates[:5]


def get_predicted_career_path(name, job1, job2, education, hard_skills, soft_skills, tools, projects, other_info):
    """
    Use GPT to generate a predicted career timeline with short roles and optional descriptions.
    """
    prompt = (
        f"Based on the following resume details, predict the candidate’s likely future career path. "
        f"List realistic job titles and estimated years, based on experience, skills, and background.\n\n"
        f"Name: {name}\n"
        f"Most Recent Job: {job1['organization']}, {job1['job_title']}, {job1['start_date']} - {job1['end_date']}\n"
        f"Responsibilities: {', '.join(job1['responsibilities'])}\n"
        f"Second Most Recent Job: {job2['organization']}, {job2['job_title']}, {job2['start_date']} - {job2['end_date']}\n"
        f"Responsibilities: {', '.join(job2['responsibilities'])}\n"
        f"Education: {', '.join(education)}\n"
        f"Hard Skills: {', '.join(hard_skills)}\n"
        f"Soft Skills: {', '.join(soft_skills)}\n"
        f"Tools: {', '.join(tools)}\n"
        f"Projects: {', '.join(projects)}\n"
        f"Other Info: {other_info}\n\n"
        f"Return the output in this format:\n"
        f"- 2024: Junior AI/ML Engineer | Description here...\n"
        f"- 2026: AI/ML Software Engineer | Description here...\n"
        f"- 2029: Senior AI/ML Engineer | Description here...\n"
        f"- 2033: AI/ML Architect | Description here...\n"
        f"(Only one line per role, separated by a '|'. Keep each description under 30 words.)"
    )

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=1000,
        temperature=0.5
    )

    return response.choices[0].message.content.strip()

def detect_red_flags(text):
    """Analyze the resume for potential red flags."""
    prompt = ("""Analyze this resume for potential red flags that employers should be aware of. Consider:
    1. Employment gaps
    2. Job hopping
    3. Inconsistent career progression
    4. Vague or generic descriptions
    5. Mismatched skills and experience
    6. Lack of quantifiable achievements
    7. Formatting and attention to detail issues
    8. Overuse of buzzwords
    9. Misaligned dates or timelines
    10. Education-experience mismatches

    Format the response as:
    Red Flags Found: Yes/No
    Concerns:
    - [List each concern with brief explanation]
    """)
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "You are a professional HR analyst skilled at resume screening."},
                {"role": "user", "content": prompt + text}
            ],
            temperature=0.7
        )
        return response.choices[0].message.content
    except Exception as e:
        print(f"Error in red flags detection: {e}")
    return "Error analyzing red flags."