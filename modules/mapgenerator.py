import pandas as pd
import plotly.express as px
from geopy.geocoders import Nominatim
import time
import os
from geopy.extra.rate_limiter import RateLimiter
from geopy.geocoders import Nominatim
from collections import defaultdict

def generate_location_map(resume_data, output_path="static/location_map.html"):
    geolocator = Nominatim(user_agent="resume_app")
    location_groups = defaultdict(list)

    for resume in resume_data:
        location = resume.get('location', '')
        print('location map rendered')
        name = resume.get('Name', 'Unknown')

        if location and location.lower() != 'n/a':
            location_groups[location.strip()].append(name)

    data = []

    for loc_name, names in location_groups.items():
        try:
            time.sleep(1)  # avoid rate-limiting
            geo = geolocator.geocode(loc_name)
            if geo:
                data.append({
                    'Location': loc_name,
                    'Names': ", ".join(names),
                    'Lat': geo.latitude,
                    'Lon': geo.longitude
                })
        except Exception as e:
            print(f"Geocoding failed for {loc_name}: {e}")

    if not data:
        return None

    df = pd.DataFrame(data)

    fig = px.scatter_mapbox(
        df,
        lat="Lat",
        lon="Lon",
        hover_name="Names",
        mapbox_style='open-street-map',
        zoom=2,
        height=600
    )

    fig.update_traces(
        marker=dict(size=10, color="red", opacity=0.7),
        hovertemplate="<b>%{hovertext}</b><extra></extra>",
        showlegend=False
    )

    fig.update_layout(
        margin=dict(l=0, r=0, t=30, b=0),
        title="📍 Candidate Location Map",
        mapbox=dict(pitch=0, bearing=0)
    )

    # ✅ Create static directory if it doesn't exist
    os.makedirs(os.path.dirname(output_path), exist_ok=True)

    fig.write_html(output_path)
    return os.path.basename(output_path)