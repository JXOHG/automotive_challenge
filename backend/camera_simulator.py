from flask import Flask, Response, jsonify
from flask_cors import CORS
import cv2
import time
import requests
import numpy as np
from io import BytesIO

app = Flask(__name__)
CORS(app)  # Allow frontend connections

# Configuration
SIMULATION_VIDEO = 'public/videos/parking-simulation.mp4'
RASPBERRY_PI_API = 'http://raspberrypi.local:5000/api'  # Update with your Pi's IP

def generate_frames():
    cap = cv2.VideoCapture(SIMULATION_VIDEO)
    frame_interval = 0.5  # Process every 0.5 seconds
    last_process = 0
    
    while cap.isOpened():
        success, frame = cap.read()
        if not success:
            cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
            continue
            
        current_time = time.time()
        if current_time - last_process >= frame_interval:
            # Process frame with Raspberry Pi
            _, buffer = cv2.imencode('.jpg', frame)
            frame_bytes = BytesIO(buffer.tobytes())
            
            try:
                response = requests.post(
                    f"{RASPBERRY_PI_API}/analyze",
                    files={'file': ('frame.jpg', frame_bytes, 'image/jpeg')},
                    timeout=2
                )
                results = response.json()
            except Exception as e:
                results = {'error': str(e)}
            
            last_process = current_time
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame_bytes = jpeg.tobytes()
            
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                   b'data: ' + json.dumps(results).encode() + b'\r\n\r\n')

        time.sleep(0.01)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True)