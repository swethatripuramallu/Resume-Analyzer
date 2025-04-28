import os
import fitz  # PyMuPDF
from docx import Document
from werkzeug.utils import secure_filename
import plotly.express as px
import pandas as pd
from dateutil import parser
import plotly.express as px

def handle_file_upload(file, upload_folder):
    """Save the uploaded file and return its filename and full file path."""
    filename = secure_filename(file.filename)
    filepath = os.path.join(upload_folder, filename)
    file.save(filepath)
    return filename, filepath

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using PyMuPDF."""
    doc = fitz.open(pdf_path)
    text = "".join([page.get_text() for page in doc])
    return text

def extract_text_from_docx(docx_path):
    """Extract text from DOCX using python-docx."""
    doc = Document(docx_path)
    full_text = [para.text for para in doc.paragraphs]
    return '\n'.join(full_text)

def parse_date_safe(date_str):
    try:
        if not date_str or date_str.strip().upper() == "N/A":
            return None
        if "present" in date_str.lower():
            return pd.to_datetime("today")
        return parser.parse(date_str, fuzzy=True)
    except Exception:
        return None

def generate_timeline(events):
    """
    Generate an interactive Plotly timeline for the user's complete resume.
    """
    timeline_data = []

    for event in events:
        start = parse_date_safe(event.get("start", ""))
        end = parse_date_safe(event.get("end", ""))
        if start and end:
            timeline_data.append({
                "Event": f"{event['title']} @ {event['company']}",
                "Start": start,
                "End": end,
                "Category": event.get("category", "Other")
            })

    df = pd.DataFrame(timeline_data)
    if df.empty:
        return None

    fig = px.timeline (
        df,
        x_start="Start",
        x_end="End",
        y="Event",
        color="Category",
        title="Complete Resume Timeline",
        color_discrete_map = {
            "Work": "#ff80ab",
            "Education": "#f48fb1",
            "Project": "#ffb6c1",
            "Other": "#ffc0cb"
        }
    )

    fig.update_yaxes(autorange="reversed")
    fig.update_layout(
        height=400,
        width=4000,  # Wider timeline
        margin=dict(l=30, r=30, t=60, b=100),
        bargap=0.6,  # Optional: adds spacing between bars
        xaxis=dict(
            tickformat="%b %Y",
            dtick="M2",  # Show tick every 2 months
            tickangle=45,
            tickfont=dict(size=12),
            title="Time"
        ),
        yaxis=dict(
            tickfont=dict(size=10)
        ),
        title_font_size=22
    )

    # Optional: add current date as a vertical line
    fig.add_vline(
        x=pd.Timestamp.today(), 
        line_width=2, 
        line_dash="dash", 
        line_color="gray"
    )

    output_path = "static/timeline.html"
    fig.write_html(output_path)
    return "timeline.html"

