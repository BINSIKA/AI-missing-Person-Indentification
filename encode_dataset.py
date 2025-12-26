import os
import face_recognition
import json
import database as db_manager

# Define the path to the uploads folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'static', 'uploads')

def get_face_encoding(image_path):
    """
    Loads an image, finds a face, and returns its 128-dimension encoding as a list.
    """
    try:
        image = face_recognition.load_image_file(image_path)
        encodings = face_recognition.face_encodings(image)
        if encodings:
            return encodings[0].tolist()
        return None
    except Exception as e:
        print(f"Error processing image {image_path}: {e}")
        return None

def rebuild_encodings():
    """
    Fetches all persons from the database, recalculates their face encodings,
    and updates the database records.
    """
    db_manager.init_db()
    persons = db_manager.get_all_persons()
    
    conn = db_manager.get_db_connection()
    c = conn.cursor()

    print(f"Starting encoding rebuild for {len(persons)} records...")

    for p in persons:
        image_filename = p.get('image_filename')
        person_id = p.get('id')
        
        if not image_filename:
            continue
        
        img_path = os.path.join(UPLOAD_FOLDER, image_filename)
        if os.path.exists(img_path):
            face_encoding_list = get_face_encoding(img_path)
            if face_encoding_list:
                encoding_json = json.dumps(face_encoding_list)
                c.execute("UPDATE persons SET encoding_json = ? WHERE id = ?", 
                          (encoding_json, person_id))
                print(f"Updated encoding for ID {person_id}: {p.get('name')}")
            else:
                c.execute("UPDATE persons SET encoding_json = NULL WHERE id = ?", (person_id,))
                print(f"No face found in image for ID {person_id}: {p.get('name')}. Encoding cleared.")
        else:
            print(f"Image file not found for ID {person_id}: {p.get('name')} at {img_path}")

    conn.commit()
    conn.close()
    print("Encoding rebuild complete.")

if __name__ == '__main__':
    rebuild_encodings()
