import os
from flask import Flask, flash, redirect, render_template, request, session, url_for, send_from_directory
from config import Config
from modules.file_handler import handle_file_upload, extract_text_from_pdf, extract_text_from_docx, generate_timeline
from modules.openai_handler import extract_information_with_gpt, generate_summary, get_match_score, extract_all_skills, process_all_resumes_together, get_predicted_career_path, detect_red_flags, recommendations
import json
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from modules.mapgenerator import generate_location_map
import shutil
import asyncio


# Initialize Flask app
app = Flask(__name__)

# Configure the upload folder and allowed extensions
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'pdf', 'docx'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB upload limit
app.config['SECRET_KEY'] = Config.SECRET_KEY  # Secret key for session management
DATABASE_FILE = os.path.join(app.config['UPLOAD_FOLDER'], 'resume_database.json')

# Helper function to check allowed file types
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/upload')
def upload():
    """Render the upload page."""
    return render_template('upload.html')

@app.route('/uploads/<filename>')
def view_resume(filename):
    return send_from_directory(app.config['UPLOAD_FOLDER'], filename)

@app.route('/delete_resume/<filename>', methods=['POST'])
def delete_resume(filename):
    database = load_database()
    database = [entry for entry in database if entry['filename'] != filename]

    # Delete the file itself
    filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
    if os.path.exists(filepath):
        os.remove(filepath)

    save_database(database)
    flash(f"Deleted {filename} successfully.")
    return redirect(url_for('view_dashboard'))

@app.route('/extract_info', methods=['POST'])
def extract_info():
    filename = request.form.get('filename')
    filepath  = f'uploads/{filename}'
    # Extract text from the uploaded file
    try:
        if filename.endswith('.pdf'):
            text = extract_text_from_pdf(filepath)
        elif filename.endswith('.docx'):
            text = extract_text_from_docx(filepath)
        else:
            flash('Unsupported file format.')
            print("Error: Unsupported file format.")
            return redirect(url_for('view_dashboard'))
    except Exception as e:
        flash(f"Error extracting text: {e}")
        print(f"Error extracting text from file: {e}")
        print('here1')
        return redirect(url_for('view_dashboard'))

    # Extract information using GPT
    try:
        extracted_info = extract_information_with_gpt(text)
        print(f"Extracted Info: {extracted_info}")
    except Exception as e:
        flash(f"Error extracting information: {e}")
        print(f"Error extracting information: {e}")
        print('here2')
        if os.path.exists(filepath):
            os.remove(filepath)
        return redirect(url_for('view_dashboard'))

    # Parse GPT's structured response
    parsed_data = parse_gpt_response(extracted_info)
    store_extracted_info_in_session(parsed_data)

    # Redirect to the extracted information page for review
    # have to change it so it does it according to the button the user picked on the cards
    feature = request.form.get('feature')
    if feature == 'summary':
        return render_template('extracted_info_summary.html', **session)
    if feature == 'jobmatch':
         return render_template('extracted_info_match.html', **session)
    if feature == 'career':
         return render_template('extracted_info_career.html', **session)
    if feature == 'timeline':
         return render_template('extracted_info_timeline.html', **session)
    if feature == 'recommendations':
        return render_template('extracted_info_recommendations.html', **session)
    if feature == 'redflags':
        red_flags = detect_red_flags(text)
        session['red_flags'] = red_flags
        if 'red_flags' not in session:
            session['red_flags'] = "No red flags analysis available."
        return render_template('red_flags.html')


@app.route('/recommendation', methods=['POST'])
def generate_recommendation():
    """Generate a professional summary based on the reviewed/corrected information."""
    # Retrieve corrected information from the form submission
    name = request.form.get('name', 'N/A')

    # Job 1 Information
    job1 = {
        "organization": request.form.get('job1', 'N/A'),
        "job_title": request.form.get('job1_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities1', '').split(',')
    }
    job1_timeline = request.form.get('job1_timeline', 'N/A')
    if " - " in job1_timeline:
        job1["start_date"], job1["end_date"] = job1_timeline.split(" - ", 1)

    # Job 2 Information
    job2 = {
        "organization": request.form.get('job2', 'N/A'),
        "job_title": request.form.get('job2_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities2', '').split(',')
    }
    job2_timeline = request.form.get('job2_timeline', 'N/A')
    if " - " in job2_timeline:
        job2["start_date"], job2["end_date"] = job2_timeline.split(" - ", 1)

    # Other extracted information
    education = request.form.get('education', '').split(',')
    hard_skills = request.form.get('hard_skills', '').split(',')
    soft_skills = request.form.get('soft_skills', '').split(',')
    tools = request.form.get('tools', '').split(',')
    projects = request.form.get('projects', '').split(',')
    other_info = request.form.get('other_info', 'N/A')
    
    raw_output = recommendations(
         name,
        job1,
        job2,
        education,
        hard_skills,
        soft_skills,
        tools,
        projects,
        other_info
    )

    try:
        parsed = parse_gpt_recommendation(raw_output)
    except Exception as e:
        flash(f"Error generating recommendation: {e}")
        return redirect(url_for('view_dashboard'))

    return render_template(
        'recommendation.html',
        candidate_name=name,
        job_titles=parsed['job_titles'],
        companies=parsed['companies'],
        technical_questions=parsed['technical_questions'],
        behavioral_questions=parsed['behavioral_questions']
    )

def parse_gpt_recommendation(output):
    lines = output.strip().split('\n')
    parsed = {
        'job_titles': [],
        'companies': [],
        'technical_questions': [],
        'behavioral_questions': []
    }

    section = None
    for line in lines:
        line = line.strip()
        if not line:
            continue
        if "job title" in line.lower():
            section = 'job_titles'
        elif "compan" in line.lower():
            section = 'companies'
        elif "technical" in line.lower():
            section = 'technical_questions'
        elif "behavioral" in line.lower():
            section = 'behavioral_questions'
        elif line[0].isdigit() or line.startswith("- "):
            clean_line = line[line.find('.')+1:].strip() if '.' in line else line[2:].strip()
            if section and clean_line:
                parsed[section].append(clean_line)

    return parsed

@app.route('/generate_summary', methods=['POST'])
def generate_summary_route():
    """Generate a professional summary based on the reviewed/corrected information."""
    # Retrieve corrected information from the form submission
    name = request.form.get('name', 'N/A')
    location = request.form.get('location', 'N/A')
    nationality = request.form.get('nationality', 'N/A')
    useful_links = request.form.get('useful_links', '').split(',')

    # Job 1 Information
    job1 = {
        "organization": request.form.get('job1', 'N/A'),
        "job_title": request.form.get('job1_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities1', '').split(',')
    }
    job1_timeline = request.form.get('job1_timeline', 'N/A')
    if " - " in job1_timeline:
        job1["start_date"], job1["end_date"] = job1_timeline.split(" - ", 1)

    # Job 2 Information
    job2 = {
        "organization": request.form.get('job2', 'N/A'),
        "job_title": request.form.get('job2_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities2', '').split(',')
    }
    job2_timeline = request.form.get('job2_timeline', 'N/A')
    if " - " in job2_timeline:
        job2["start_date"], job2["end_date"] = job2_timeline.split(" - ", 1)

    # Other extracted information
    education = request.form.get('education', '').split(',')
    hard_skills = request.form.get('hard_skills', '').split(',')
    soft_skills = request.form.get('soft_skills', '').split(',')
    tools = request.form.get('tools', '').split(',')
    projects = request.form.get('projects', '').split(',')
    other_info = request.form.get('other_info', 'N/A')

    # Use the summarizer to generate a summary
    summary_text = generate_summary(
        name,
        job1,
        job2,
        education,
        hard_skills,
        soft_skills,
        tools,
        projects,
        other_info
    )

    # Render the summary template with the generated summary
    return render_template('generate_summary.html', summary=summary_text)

@app.route('/timeline', methods=['POST'])
def timeline_dashboard():
    # load timeline plot
    # Job 1 Information
    job1 = {
        "organization": request.form.get('job1', 'N/A'),
        "job_title": request.form.get('job1_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities1', '').split(',')
    }
    job1_timeline = request.form.get('job1_timeline', 'N/A')
    if " - " in job1_timeline:
        job1["start_date"], job1["end_date"] = job1_timeline.split(" - ", 1)

    # Job 2 Information
    job2 = {
        "organization": request.form.get('job2', 'N/A'),
        "job_title": request.form.get('job2_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities2', '').split(',')
    }
    job2_timeline = request.form.get('job2_timeline', 'N/A')
    if " - " in job2_timeline:
        job2["start_date"], job2["end_date"] = job2_timeline.split(" - ", 1)
    
    
    education = request.form.get('education', '').split(',')
    projects = request.form.get('projects', '').split(',')
    
    # Combine all events into one timeline
    all_events = []

    # Work Experience
    for job in [job1, job2]:
        if job["organization"] != "N/A":
            all_events.append({
                "title": job["job_title"],
                "company": job["organization"],
                "start": job["start_date"],
                "end": job["end_date"],
                "category": "Work"
            })

    # Grouped Education
    if any(edu.strip() for edu in education):
        all_events.append({
            "title": "Education",
            "company": ", ".join([e.strip() for e in education if e.strip()]),
            "start": "August 2020",  # You can change this to parsed dates if available
            "end": "May 2025",
            "category": "Education"
        })

    # Projects
    for project in projects:
        if project.strip():
            all_events.append({
                "title": "Project",
                "company": project.strip(),
                "start": "January 2023",
                "end": "December 2023",
                "category": "Project"
            })

    timeline_file = generate_timeline(all_events)
    
    return render_template('timeline.html')


@app.route('/match_job_description', methods=['POST', 'GET'])
def match_job_description():
    if request.method == 'GET':
        return render_template('match_job_description.html')

    job_description = request.form.get('job_description', '')

    # Reconstruct resume data from form
    name = request.form.get('name', 'N/A')
    job1 = {
        "organization": request.form.get('job1', 'N/A'),
        "job_title": request.form.get('job1_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities1', '').split(',')
    }
    job1_timeline = request.form.get('job1_timeline', 'N/A')
    if " - " in job1_timeline:
        job1["start_date"], job1["end_date"] = job1_timeline.split(" - ", 1)

    job2 = {
        "organization": request.form.get('job2', 'N/A'),
        "job_title": request.form.get('job2_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities2', '').split(',')
    }
    job2_timeline = request.form.get('job2_timeline', 'N/A')
    if " - " in job2_timeline:
        job2["start_date"], job2["end_date"] = job2_timeline.split(" - ", 1)

    education = request.form.get('education', '').split(',')
    hard_skills = request.form.get('hard_skills', '').split(',')
    soft_skills = request.form.get('soft_skills', '').split(',')
    tools = request.form.get('tools', '').split(',')
    projects = request.form.get('projects', '').split(',')
    other_info = request.form.get('other_info', 'N/A')

    # Call GPT for match evaluation
    result = get_match_score(
        name,
        job1,
        job2,
        education,
        hard_skills,
        soft_skills,
        tools,
        projects,
        other_info,
        job_description
    )

    # Parse the response
    lines = result.split('\n')
    score = None
    strengths = []
    improvements = []

    section = None
    for line in lines:
        line = line.strip()
        if line.startswith("Score:"):
            score = line.replace("Score:", "").strip()
        elif line.startswith("Strengths:"):
            section = 'strengths'
        elif line.startswith("Improvements:"):
            section = 'improvements'
        elif line.startswith("- "):
            if section == 'strengths':
                strengths.append(line[2:])
            elif section == 'improvements':
                improvements.append(line[2:])

    return render_template(
        'match_job_description.html',
        candidate_name=name,
        score=score,
        strengths=strengths,
        improvements=improvements
    )
@app.route('/upload_database', methods=['POST'])
def upload_database():
    """Handle uploading multiple resumes to build a database."""
    if 'resume_files' not in request.files:
        flash('No files selected!')
        return redirect(request.referrer)

    files = request.files.getlist('resume_files')
    existing_files = os.listdir(app.config['UPLOAD_FOLDER'])

    # Exclude database.json from count
    existing_files = [f for f in existing_files if f != 'resume_database.json']

    if len(existing_files) + len(files) > 15:
        flash('Upload limit exceeded. You can only have up to 15 resumes.')
        return redirect(request.referrer)

    database = load_database()

    for file in files:
        if file and allowed_file(file.filename):
            filename = file.filename
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            # Save the uploaded file
            file.save(filepath)
            if filename.endswith('.pdf'):
                    text = extract_text_from_pdf(filepath)
            elif filename.endswith('.docx'):
                    text = extract_text_from_docx(filepath)
            else:
                    continue
            
            try:
                extracted_info = extract_information_with_gpt(text)
                parsed_data = parse_gpt_response(extracted_info)

                # Location Fallback Logic
                location = parsed_data.get("Location", "").strip()
                name = parsed_data.get("Name", "").strip()
            
                # Add to database
                database.append({
                    "filename": filename,
                    "filepath": filepath,
                    "upload_time": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    "location": location if location else "N/A",
                    "Name": name
                })
            
            except Exception as e:
                    print(f"Error processing {filename}: {e}")
                    continue

    save_database(database)

    flash(f'{len(files)} resumes uploaded successfully to your database!')
    return redirect(url_for('view_dashboard'))


@app.route('/')
def view_dashboard():
    database = load_database()
    map_file = generate_location_map(database)  # This ensures the map updates
    return render_template('dashboard.html', database=database, map_html = map_file)

@app.route('/jobinput')
def jobinput():
    return render_template('database.html')


# Updated career path prediction route to use form-based fields like match_job_description
@app.route('/career_path', methods=['POST'])
def career_path():
    # Reconstruct resume data from form (same style as match_job_description)
    name = request.form.get('name', 'N/A')
    job1 = {
        "organization": request.form.get('job1', 'N/A'),
        "job_title": request.form.get('job1_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities1', '').split(',')
    }
    job1_timeline = request.form.get('job1_timeline', 'N/A')
    if " - " in job1_timeline:
        job1["start_date"], job1["end_date"] = job1_timeline.split(" - ", 1)

    job2 = {
        "organization": request.form.get('job2', 'N/A'),
        "job_title": request.form.get('job2_title', 'N/A'),
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": request.form.get('responsibilities2', '').split(',')
    }
    job2_timeline = request.form.get('job2_timeline', 'N/A')
    if " - " in job2_timeline:
        job2["start_date"], job2["end_date"] = job2_timeline.split(" - ", 1)

    education = request.form.get('education', '').split(',')
    hard_skills = request.form.get('hard_skills', '').split(',')
    soft_skills = request.form.get('soft_skills', '').split(',')
    tools = request.form.get('tools', '').split(',')
    projects = request.form.get('projects', '').split(',')
    other_info = request.form.get('other_info', 'N/A')

    # Call GPT-based prediction
    prediction = get_predicted_career_path(
        name,
        job1,
        job2,
        education,
        hard_skills,
        soft_skills,
        tools,
        projects,
        other_info
    )

    return render_template("career_path.html", timeline=prediction)


@app.route('/skill_map')
def skill_map():
    all_skills = []

    try:
        # Get a dict: { filename: [skills] }
        skill_map = extract_all_skills(app.config['UPLOAD_FOLDER'])

        # Flatten all skills from all resumes
        for skills in skill_map.values():
            all_skills.extend(skills)

    except Exception as e:
        print(f"Error processing: {e}")

    # Count frequency of each skill
    from collections import Counter
    skill_counts = Counter(all_skills)

    return render_template(
        'skill_map.html',
        skills=skill_counts
    )


@app.route('/database_match', methods=['POST'])
def database_match():
    job_description = request.form.get('job_description', '')

    try:
        # Use the all-in-one handler to get top 5 candidates
        top_candidates = process_all_resumes_together(app.config['UPLOAD_FOLDER'], job_description)
    except Exception as e:
        print(f"Error during batch resume processing: {e}")
        flash("Something went wrong while processing resumes.")
        return redirect(url_for('view_dashboard'))

    if not top_candidates:
        flash("No valid resumes were processed.")
        return redirect(url_for('view_dashboard'))

    return render_template(
        'job_match_database.html',
        candidates=top_candidates
    )

def load_database():
    """Load the resume database from JSON file."""
    if os.path.exists(DATABASE_FILE):
        with open(DATABASE_FILE, 'r') as f:
            return json.load(f)
    return []

def save_database(data):
    """Save the resume database to JSON file."""
    with open(DATABASE_FILE, 'w') as f:
        json.dump(data, f, indent=4)


def parse_gpt_response(response_text):
    """Parse the structured GPT response and return a dictionary with relevant fields."""
    lines = response_text.split('\n')
    parsed_data = {}
    current_key = None
    current_value = []

    def save_current_key():
        if current_key:
            parsed_data[current_key] = '\n'.join(current_value).strip()

    for line in lines:
        # Clean line
        line = line.strip()
        if not line:
            continue

        # Check if this line is a new field (ends with colon or contains 'Job' or 'Responsibilities')
        if any(line.lower().startswith(prefix) for prefix in ["name:", "location:", "nationality:", "useful links:", "job 1:", "responsibilities 1:", "job 2:", "responsibilities 2:", "education:", "hard skills:", "soft skills:", "tools:", "projects:", "other relevant info:"]):
            # Save the last key-value pair
            save_current_key()

            # Split new key and value
            if ": " in line:
                current_key, value = line.split(": ", 1)
                current_key = current_key.strip()
                current_value = [value.strip()]
            else:
                current_key = line.replace(":", "").strip()
                current_value = []
        else:
            # Continuation of current field
            current_value.append(line)

    # Save the last key-value pair
    save_current_key()
    print(parsed_data)
    return parsed_data

def normalize_timeline(timeline_str):
    return timeline_str.replace('–', '-').replace('—', '-').strip()

def store_extracted_info_in_session(parsed_data):
    """Store extracted information in session for later use."""
    session['name'] = parsed_data.get("Name", "N/A")
    session['location'] = parsed_data.get("Location", "N/A")
    session['nationality'] = parsed_data.get("Nationality", "N/A")
    session['useful_links'] = parsed_data.get("Useful Links", "").split(',') if parsed_data.get("Useful Links") else []

    # Job 1 Information
    session['job1'] = {
        "organization": "N/A",
        "job_title": "N/A",
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": []
    }
    if "Job 1" in parsed_data:
        job1_details = parsed_data["Job 1"].split(', ')
        if len(job1_details) >= 3:
            session['job1']['organization'] = job1_details[0]
            session['job1']['job_title'] = job1_details[1]
            # session['job1']['start_date'], session['job1']['end_date'] = job1_details[2].split(' - ') if ' - ' in job1_details[2] else ("N/A", "N/A")
            timeline1 = normalize_timeline(job1_details[2])
            session['job1']['start_date'], session['job1']['end_date'] = timeline1.split(' - ') if ' - ' in timeline1 else ("N/A", "N/A")

        session['job1']['responsibilities'] = parsed_data.get("Responsibilities 1", "").split(', ')
       

    # Job 2 Information
    session['job2'] = {
        "organization": "N/A",
        "job_title": "N/A",
        "start_date": "N/A",
        "end_date": "N/A",
        "responsibilities": []
    }
    if "Job 2" in parsed_data:
        job2_details = parsed_data["Job 2"].split(', ')
        if len(job2_details) >= 3:
            session['job2']['organization'] = job2_details[0]
            session['job2']['job_title'] = job2_details[1]
            # session['job2']['start_date'], session['job2']['end_date'] = job2_details[2].split(' - ') if ' - ' in job2_details[2] else ("N/A", "N/A")
            timeline1 = normalize_timeline(job1_details[2])
            session['job2']['start_date'], session['job2']['end_date'] = timeline1.split(' - ') if ' - ' in timeline1 else ("N/A", "N/A")

        session['job2']['responsibilities'] = parsed_data.get("Responsibilities 2", "").split(', ')

    session['education'] = parsed_data.get("Education", "").split(', ') if parsed_data.get("Education") else []
    session['hard_skills'] = parsed_data.get("Hard Skills", "").split(', ') if parsed_data.get("Hard Skills") else []
    session['soft_skills'] = parsed_data.get("Soft Skills", "").split(', ') if parsed_data.get("Soft Skills") else []
    session['tools'] = parsed_data.get("Tools", "").split(', ') if parsed_data.get("Tools") else []
    session['projects'] = parsed_data.get("Projects", "").split(', ') if parsed_data.get("Projects") else []
    session['other_info'] = parsed_data.get("Other Relevant Info", "N/A")


if __name__ == "__main__":
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    app.run(debug=True, port=5001)
