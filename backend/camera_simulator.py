from flask import Flask, Response, jsonify, request
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
import base64

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
latest_analysis_results = {}

def preprocess_frame(frame, max_size=1280):
    """Preprocess frame before sending for analysis."""
    if frame is None:
        return None
        
    height, width = frame.shape[:2]
    if width > max_size or height > max_size:
        scale = max_size / max(width, height)
        frame = cv2.resize(frame, (int(width * scale), int(height * scale)))
    
    encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), 85]
    _, jpeg = cv2.imencode('.jpg', frame, encode_param)
    return jpeg.tobytes()

def send_frame_for_analysis(frame_data, api_url, max_retries=3, backoff_factor=1.5):
    """Send frame for analysis with retry logic."""
    retry_count = 0
    last_error = None
    
    while retry_count < max_retries:
        try:
            frame_buffer = BytesIO(frame_data)
            response = requests.post(
                api_url,
                files={'file': ('frame.jpg', frame_buffer, 'image/jpeg')},
                timeout=15
            )
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            last_error = e
            retry_count += 1
            if retry_count < max_retries:
                sleep_time = backoff_factor ** retry_count
                logger.warning(f"Retry {retry_count}/{max_retries} after {sleep_time:.1f}s. Error: {str(e)}")
                time.sleep(sleep_time)
            else:
                logger.error(f"Failed after {max_retries} retries: {str(e)}")
    
    return {'error': str(last_error)}

def generate_frames(showOverlay=True):
    if not os.path.exists(SIMULATION_VIDEO):
        logger.error(f"Video file not found at: {SIMULATION_VIDEO}")
        return
    
    cap = cv2.VideoCapture(SIMULATION_VIDEO)
    if not cap.isOpened():
        logger.error(f"Failed to open video file: {SIMULATION_VIDEO}")
        return
    
    logger.info(f"Successfully opened video file: {SIMULATION_VIDEO}")
    frame_interval = 10.0  # Analyze every 10 seconds
    last_process = None
    
    try:
        while not stop_event.is_set():
            success, frame = cap.read()
            if not success:
                logger.info("Video ended, restarting from beginning")
                cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
                continue
                
            current_time = time.time()
            
            # Always encode the frame for streaming
            ret, jpeg = cv2.imencode('.jpg', frame)
            frame_bytes = jpeg.tobytes()
            
            results = None
            if last_process is None or (current_time - last_process >= frame_interval):
                processed_frame = preprocess_frame(frame)
                if processed_frame:
                    try:
                        start_time = time.time()
                        results = send_frame_for_analysis(
                            processed_frame, 
                            f"{RASPBERRY_PI_API}/analyze"
                        )
                        logger.info(f"Frame analyzed in {time.time() - start_time:.2f} seconds")
                        last_process = current_time
                        
                        # Use overlay image if available and showOverlay is True
                        if showOverlay and 'overlay_image' in results and results['overlay_image']:
                            try:
                                frame_bytes = base64.b64decode(results['overlay_image'])
                            except Exception as e:
                                logger.error(f"Failed to decode overlay: {str(e)}")
                        
                        # Update the latest analysis results
                        global latest_analysis_results
                        latest_analysis_results = results
                                
                    except Exception as e:
                        logger.error(f"Analysis error: {str(e)}")
                        results = {'error': str(e)}
                        last_process = current_time
            
            # Yield the frame
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + frame_bytes + b'\r\n')
            
            time.sleep(0.033)  # ~30 FPS
    finally:
        cap.release()
        logger.info("Video capture released")

@app.route('/video_feed')
def video_feed():
    # Get showOverlay parameter from query string, default to True
    showOverlay = request.args.get('showOverlay', 'true').lower() == 'true'
    stop_event.clear()
    
    def stream_frames():
        try:
            for frame in generate_frames(showOverlay):
                yield frame
        except Exception as e:
            logger.error(f"Streaming error: {str(e)}")
    
    response = Response(stream_frames(), mimetype='multipart/x-mixed-replace; boundary=frame')
    
    @response.call_on_close
    def on_close():
        stop_event.set()
    
    return response

@app.route('/current_analysis')
def current_analysis():
    global latest_analysis_results
    return jsonify(latest_analysis_results if latest_analysis_results else {})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5001, debug=True, threaded=True)