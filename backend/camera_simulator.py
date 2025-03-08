from flask import Flask, Response, jsonify, request
from flask_cors import CORS
import cv2
import time
import requests
import numpy as np
from io import BytesIO
import json
import threading

app = Flask(__name__)
CORS(app)  # Allow frontend connections

# Configuration
SIMULATION_VIDEO = 'public/videos/parking-simulation.mp4'
RASPBERRY_PI_API = "http://192.168.137.135:5000/api"  # Update with your Pi's IP

# Global flag to control the generator
stop_event = threading.Event()

def generate_frames():
    cap = cv2.VideoCapture(SIMULATION_VIDEO)
    frame_interval = 0.5  # Process every 0.5 seconds
    last_process = 0
    
    try:
        while cap.isOpened() and not stop_event.is_set():
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
    finally:
        cap.release()  # Ensure video capture is released when stopping

@app.route('/video_feed')
def video_feed():
    # Reset stop event when a new client connects
    stop_event.clear()
    
    def stream_with_cleanup():
        try:
            yield from generate_frames()
        except GeneratorExit:
            # Client disconnected
            stop_event.set()
        except Exception as e:
            print(f"Stream error: {e}")
            stop_event.set()
        finally:
            stop_event.set()  # Ensure stop_event is set on any exit

    response = Response(stream_with_cleanup(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    # Optional: Add a finalizer to ensure cleanup (though GeneratorExit should handle it)
    @response.call_on_close
    def on_close():
        stop_event.set()
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)