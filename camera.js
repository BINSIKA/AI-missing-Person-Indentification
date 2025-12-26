const video = document.getElementById('video');
const startBtn = document.getElementById('startBtn');
const stopBtn = document.getElementById('stopBtn');
const statusText = document.getElementById('status');
const resultsContainer = document.getElementById('results');
const alertSound = document.getElementById('alertSound');

let stream = null;
let detectionInterval = null;

// ----------------------
// Start Camera
// ----------------------
async function startCamera() {
    try {
        // Request access to the user's webcam
        stream = await navigator.mediaDevices.getUserMedia({ video: true });
        video.srcObject = stream;
        statusText.textContent = "🟢 Detection started...";
        console.log("Camera started successfully!");
    } catch (err) {
        console.error("Error accessing camera:", err);
        alert("❌ Unable to access camera.\n\n➡ Try using http://localhost:5000 instead of 127.0.0.1 and allow camera permission.\n\nIf still not working, Windows Camera app will open automatically.");

        // Fallback: open Windows Camera app
        try {
            window.location.href = "microsoft.windows.camera:"; // 🚀 Launch native Windows Camera
        } catch (fallbackErr) {
            console.error("Failed to open Windows Camera:", fallbackErr);
            alert("⚠ Could not open Windows Camera app. Please open it manually from Start Menu.");
        }
    }
}

// ----------------------
// Stop Camera
// ----------------------
function stopCamera() {
    if (stream) {
        let tracks = stream.getTracks();
        tracks.forEach(track => track.stop());
        stream = null;
        console.log("Camera stopped.");
    }
    if (detectionInterval) {
        clearInterval(detectionInterval);
        detectionInterval = null;
    }
    statusText.textContent = "🔴 Detection stopped.";
}

// ----------------------
// Send Frames to Server for Recognition
// ----------------------
async function detectFace() {
    const canvas = document.createElement('canvas');
    canvas.width = video.videoWidth;
    canvas.height = video.videoHeight;

    const ctx = canvas.getContext('2d');
    ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
    const imageData = canvas.toDataURL('image/jpeg');

    try {
        const response = await fetch('/process_frame', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ image: imageData })
        });

        const data = await response.json();
        renderResults(data);
    } catch (error) {
        console.error("Error sending frame:", error);
    }
}

// ----------------------
// Display Results
// ----------------------
function renderResults(data) {
    resultsContainer.innerHTML = '';

    if (data.status === 'match_found' && data.matches.length > 0) {
        // Play alert sound once when a match is found
        alertSound.play().catch(err => console.warn("Sound play issue:", err));

        resultsContainer.innerHTML = `
            <p class="text-xl font-bold text-green-700">✅ Matches Found! (${data.matches.length} candidates)</p>
        `;

        data.matches.forEach(match => {
            const personCard = document.createElement('div');
            personCard.classList.add('match-card');
            personCard.innerHTML = `
                <div class="p-2 border rounded-lg shadow-md mt-2 bg-white">
                    <img src="${match.image_url}" alt="Matched Face" class="rounded-md w-32 h-32 object-cover"/>
                    <p><strong>Name:</strong> ${match.name}</p>
                    <p><strong>Location:</strong> ${match.location}</p>
                    <p><strong>Age:</strong> ${match.age}</p>
                </div>
            `;
            resultsContainer.appendChild(personCard);
        });
    } else {
        resultsContainer.innerHTML = `<p class="text-gray-600">No matches detected yet...</p>`;
    }
}

// ----------------------
// Event Listeners
// ----------------------
startBtn.addEventListener('click', async () => {
    await startCamera();
    detectionInterval = setInterval(detectFace, 3000); // every 3 seconds
});

stopBtn.addEventListener('click', () => {
    stopCamera();
});
