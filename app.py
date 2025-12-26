from flask import Flask, render_template, request, redirect, url_for, jsonify
import os, re, base64, numpy as np
from io import BytesIO
from PIL import Image
import face_recognition
from werkzeug.utils import secure_filename
from twilio.rest import Client
import database as db_manager 
import logging

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = 'static/uploads/'
app.config['SIGHTINGS_FOLDER'] = 'static/sightings/'
app.config['MAX_CONTENT_LENGTH'] = 500 * 1024 * 1024
FACIAL_TOLERANCE = 0.6

logging.basicConfig(level=logging.INFO)

# Twilio credentials from environment variables
ACCOUNT_SID = os.environ.get("TWILIO_ACCOUNT_SID")
AUTH_TOKEN = os.environ.get("TWILIO_AUTH_TOKEN")
TWILIO_PHONE_NUMBER = os.environ.get("TWILIO_PHONE_NUMBER")

TWILIO_CLIENT = None
try:
    TWILIO_CLIENT = Client(ACCOUNT_SID, AUTH_TOKEN)
    logging.info("✅ Twilio Client Initialized.")
except Exception as e:
    logging.warning(f"⚠️ Twilio init error: {e}")
    TWILIO_CLIENT = None

db_manager.init_db()
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
os.makedirs(app.config['SIGHTINGS_FOLDER'], exist_ok=True)

def get_face_encoding(image_path):
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        return encodings[0].tolist() if encodings else None
    except Exception as e:
        logging.error(f"Encoding error: {e}")
        return None

def get_all_face_encodings(image_path):
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        return [e.tolist() for e in encodings]
    except Exception as e:
        logging.error(f"Encoding error: {e}")
        return []

def send_alert_sms(person_data, match_score, latitude=None, longitude=None):
    if TWILIO_CLIENT is None:
        logging.warning("⚠️ SMS Alert skipped: Twilio client not configured.")
        return "SMS Alert skipped: Twilio client not configured." # Return status
    
    # Using the correct Google Maps URL format (corrected typo from template)
    location_url = (
        f"https://maps.google.com/?q={latitude},{longitude}"
        if latitude and longitude else "Location unavailable"
    )
    
    name = person_data.get('name', 'Unknown')
    phone = person_data.get('phone')

    # Basic check to avoid sending to own number or empty number
    if not phone or phone == TWILIO_PHONE_NUMBER:
        logging.warning(f"⚠️ Invalid recipient number for {name}. SMS skipped.")
        return "SMS Alert skipped: Invalid recipient phone number." # Return status

    body = (
        f"🚨 ALERT: Missing person located! 🚨\n"
        f"Name: {name}\n"
        f"Match Confidence: {match_score}\n"
        f"Last Seen Location: {location_url}"
    )

    try:
        TWILIO_CLIENT.messages.create(
            body=body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone
        )
        logging.info(f"📱 Alert sent to {phone}")
        return "SMS Notification Sent successfully." # Return success status
    except Exception as e:
        logging.error(f"❌ Twilio send failed: {e}")
        return f"SMS Send Failed: {str(e)}" # Return error status


@app.route('/')
def index():
    # Assuming 'index.html' exists
    return render_template('index.html')

@app.route('/upload', methods=['GET', 'POST'])
def upload_person():
    if request.method == 'POST':
        name = request.form.get('name', '').strip()
        age = request.form.get('age', '').strip()
        gender = request.form.get('gender', '').strip()
        height = request.form.get('height', '').strip()
        weight = request.form.get('weight', '').strip()
        phone = request.form.get('phone', '').strip()
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')

        image = request.files.get('image')
        if not image:
            # Assuming 'upload.html' is the form page
            return redirect(url_for('upload_person')) 

        filename = secure_filename(image.filename)
        upload_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(upload_path)

        face_encoding = get_face_encoding(upload_path)
        if face_encoding is None:
            os.remove(upload_path)
            # Assuming 'result_notfound.html' exists
            return render_template('result_notfound.html') 

        db_manager.add_person(name, age, gender, height, weight, filename, face_encoding, phone, latitude, longitude)
        return redirect(url_for('view_all')) # Assuming 'view_all' is defined

    return render_template('upload.html')

# Assuming view_all route exists
@app.route('/view')
def view_all():
    persons = db_manager.get_all_persons()
    return render_template('view_all.html', persons=persons)

@app.route('/search', methods=['GET', 'POST'])
def search_person():
    if request.method == 'POST':
        image = request.files['search_image']
        filename = secure_filename(image.filename)
        path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        image.save(path)

        search_encodings = get_all_face_encodings(path)
        os.remove(path)

        if not search_encodings:
            return render_template('result_notfound.html')

        known_persons = db_manager.get_all_persons()
        best_match = None
        best_distance = float('inf')

        for enc in search_encodings:
            enc_np = np.array(enc)
            for person in known_persons:
                if not person.get('face_encoding'):
                    continue
                known_enc = np.array(person['face_encoding'])
                distance = face_recognition.face_distance([known_enc], enc_np)[0]
                if distance < FACIAL_TOLERANCE and distance < best_distance:
                    best_distance = distance
                    best_match = person

        if best_match:
            match_score = int(max(1, 100 * (1 - best_distance / FACIAL_TOLERANCE)))
            return render_template('result-found.html', person=best_match, match_score=f"{match_score}%")
        else:
            return render_template('result_notfound.html')

    return render_template('search.html')

@app.route('/camera_search', methods=['GET', 'POST'])
def camera_search():
    if request.method == 'POST':
        data_url = request.form['image_data']
        latitude = request.form.get('latitude')
        longitude = request.form.get('longitude')
        session_id = request.form.get('session_id')

        # Regex to strip the header and decode the base64 image
        match = re.search(r'base64,(.*)', data_url)
        if not match:
            return jsonify({"status": "error", "message": "Invalid image data format"}), 400

        img_str = match.group(1)
        img_bytes = BytesIO(base64.b64decode(img_str))
        temp_path = os.path.join(app.config['UPLOAD_FOLDER'], f'capture_{session_id}.jpg')

        img = Image.open(img_bytes)
        img.thumbnail((400, 300))
        img.save(temp_path, format='JPEG', quality=70)

        search_encodings = get_all_face_encodings(temp_path)
        os.remove(temp_path)

        if not search_encodings:
            return jsonify({"status": "no_face"})

        known_persons = db_manager.get_all_persons()
        best_match = None
        best_distance = float('inf')

        for enc in search_encodings:
            enc_np = np.array(enc)
            for person in known_persons:
                if not person.get('face_encoding'):
                    continue
                known_enc = np.array(person['face_encoding'])
                distance = face_recognition.face_distance([known_enc], enc_np)[0]
                if distance < FACIAL_TOLERANCE and distance < best_distance:
                    best_distance = distance
                    best_match = person

        if best_match:
            match_score = int(max(1, 100 * (1 - best_distance / FACIAL_TOLERANCE)))
            match_str = f"{match_score}%"

            # 1. Save Sighting Image
            sighting_filename = f"sighting_{best_match['id']}_{int(time.time())}.jpg"
            sighting_path = os.path.join(app.config['SIGHTINGS_FOLDER'], sighting_filename)
            # Re-open image stream to save to sightings folder
            img_bytes_sighting = BytesIO(base64.b64decode(img_str))
            Image.open(img_bytes_sighting).save(sighting_path, format='JPEG', quality=85)

            # 2. Log Sighting and get ID
            sighting_id = db_manager.log_sighting(best_match['id'], sighting_filename, latitude, longitude)
            
            # 3. Send SMS Alert
            send_alert_sms(best_match, match_str, latitude, longitude)

            # 4. Return Redirect URL
            redirect_url = url_for('sighting_result', sighting_id=sighting_id) 

            return jsonify({
                "status": "match_found",
                "name": best_match['name'],
                "match_score": match_str,
                "person_id": best_match['id'],
                "redirect_url": redirect_url # <--- CRITICAL FOR FRONTEND REDIRECT
            })
        else:
            return jsonify({"status": "no_match"})

    return render_template('camera_search.html')


@app.route('/sighting_result/<int:sighting_id>')
def sighting_result(sighting_id):
    """
    Renders the detailed result-found.html page for a specific sighting.
    This replaces the client-side temporary match box.
    """
    sighting = db_manager.get_sighting_by_id(sighting_id)

    if sighting:
        person = db_manager.get_person_by_id(sighting['person_id'])
        
        # NOTE: Match score and SMS status are not stored in the sighting log. 
        # For a full result page, we retrieve the person and display the sighting details.
        
        # Simulating the SMS status and score as we don't store them per sighting (optional)
        # You can add columns to the sightings table to store match_score and sms_status
        dummy_match_score = "N/A" # Ideally stored in db_manager.log_sighting
        dummy_sms_status = "SMS Notification Attempted."
        
        # We must re-send the alert to get the actual status if we didn't store it. 
        # For simplicity, we'll use a placeholder.

        return render_template('result-found.html', 
                               person=person,
                               match_score=dummy_match_score, # Use actual score if stored
                               sighting_id=sighting_id,
                               latitude=sighting['latitude'],
                               longitude=sighting['longitude'],
                               sighting_image=sighting['image_filename'],
                               sms_status=dummy_sms_status)
    
    return "Sighting not found", 404


@app.route('/update_location', methods=['POST'])
def update_location():
    # This route is currently just for logging client-side location updates (as per client code)
    data = request.get_json()
    logging.info(f"📍 Location update: {data}")
    return jsonify({"status": "ok"})


if __name__ == '__main__':
    # Add time module import
    import time
    app.run(host='0.0.0.0', port=5000, debug=True)