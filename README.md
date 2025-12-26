# AI-missing-Person-Indentification

AI Missing Person Identification System
**Overview**
       The AI Missing Person Identification System is a mission-driven technical solution designed to reunite families by leveraging modern technology for public safety. Built during my mini project, this full-stack application automates the search for missing individuals using real-time facial recognition. By combining a high-performance Python backend with a responsive, user-friendly interface, the system acts as a digital watchman that can be deployed on any camera-enabled device.
       
**Why This Matters**
Traditional search methods can be slow and fragmented. This system bridges that gap by providing:
Instant Recognition: Instead of relying on manual photo comparisons, the AI scans and matches faces against a database in seconds
.Precise Location Tracking: By capturing GPS coordinates (Latitude and Longitude) at the exact moment of a sighting, it gives families and authorities a concrete place to start their search.
Immediate Alerts: Using the Twilio API, the system bypasses delays by sending an automated SMS to guardians the moment a high-confidence match is detected

**Key Features & Tech StackFeatureImplementation**
Real-Time ScanningUses OpenCV to process live video feeds every 2 seconds.
Smart MatchingEmploys the face_recognition library to compare 128-D facial signatures with a 0.6 tolerance for high accuracy.
Dynamic DatabaseManaged by SQLite, storing everything from physical descriptions to historical sighting logs.
Cloud CommunicationIntegrated with Twilio to deliver real-time emergency notifications.
Mapping IntegrationGenerates a Google Maps link in alerts to pinpoint the last seen location.

**How the System WorksReporting:**
A user registers a missing person by uploading their photo and physical details, which are converted into a unique facial encoding and stored in SQLite.
Detection: When "Camera Search" is active, the browser's Geolocation API tracks the device's movement while the webcam looks for faces.
Verification: The server receives image data via Base64, calculates the "distance" between the live face and the database, and identifies a match if the similarity is high enough.
Action: Once a match is confirmed, the system saves the sighting image, logs the location, and sends an immediate SMS alert to the registered contact number.
