from flask import Flask, Response
from flask_cors import CORS
import cv2
import time
import requests
import numpy as np
from io import BytesIO
import json
import threading
import logging
import os

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__)
CORS(app)

# Configuration
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
SIMULATION_VIDEO = os.path.join(BASE_DIR, 'public', 'videos', 'parking-simulation.mp4')
RASPBERRY_PI_API = "http://192.168.137.135:5000/api"

# Global flag to control the generator
stop_event = threading.Event()

def generate_frames():
    if not os.path.exists(SIMULATION_VIDEO):
        logger.error(f"Video file not found at: {SIMULATION_VIDEO}")
        return
    
    cap = cv2.VideoCapture(SIMULATION_VIDEO)
    if not cap.isOpened():
        logger.error(f"Failed to open video file: {SIMULATION_VIDEO}. Check file format or codec.")
        return
    
    logger.info(f"Successfully opened video file: {SIMULATION_VIDEO}")
    frame_interval = 10.0  # Analyze every 10 seconds after initial frame
    last_process = None  # Track last analysis time, None means first frame
    
    try:
        while not stop_event.is_set():
            success, frame = cap.read()
            if not success:
                logger.info("Video ended, restarting from beginning")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            current_time = time.time()
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame_bytes = jpeg.tobytes()
            
            # Analyze immediately for the first frame, then periodically
            results = None
            if last_process is None or (current_time - last_process >= frame_interval):
                frame_buffer = BytesIO(frame_bytes)
                try:
                    start_time = time.time()
                    response = requests.post(
                        f"{RASPBERRY_PI_API}/analyze",
                        files={'file': ('frame.jpg', frame_buffer, 'image/jpeg')},
                        timeout=15
                    )
                    response.raise_for_status()
                    results = response.json()
                    logger.info(f"Frame analyzed in {time.time() - start_time:.2f} seconds")
                    last_process = current_time if last_process is not None else current_time
                except requests.exceptions.RequestException as e:
                    logger.error(f"Failed to analyze frame: {str(e)}")
                    results = {'error': str(e)}
                    last_process = current_time if last_process is not None else current_time
            
            # Yield frame and results (if available)
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n'
                   b'data: ' + json.dumps(results if results else {}).encode() + b'\r\n\r\n')
            
            time.sleep(0.033)  # ~30 FPS for raw video display
    finally:
        cap.release()
        logger.info("Video capture released")

@app.route('/video_feed')
def video_feed():
    stop_event.clear()
    
    def stream_with_cleanup():
        try:
            yield from generate_frames()
        except GeneratorExit:
            logger.info("Client disconnected")
            stop_event.set()
        except Exception as e:
            logger.error(f"Stream error: {str(e)}")
            stop_event.set()
        finally:
            stop_event.set()

    response = Response(stream_with_cleanup(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @response.call_on_close
    def on_close():
        stop_event.set()
    
    return response

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)