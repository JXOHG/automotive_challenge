from flask import Flask, request, jsonify, send_from_directory
import os
import numpy as np
import cv2
import time
from datetime import datetime
import json
from werkzeug.utils import secure_filename
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
import logging
import torch
import base64
from io import BytesIO

from parking_spot_overlay import ParkingSpotOverlay
from newer import predict, crop, compile_data

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app, resources={
    r"/api/*": {
        "origins": ["http://localhost:5173", "http://172.30.179.110:5173"]
    }
})

UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
DETECTION_LOG = 'detections.txt'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'final_model.pth')
INFO_PATH = os.path.join(BASE_DIR, 'info.txt')

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_detection_to_file(image_name, detections):
    with open(os.path.join(RESULTS_FOLDER, DETECTION_LOG), 'a') as f:
        for detection in detections:
            f.write(f"{image_name} {detection['class_id']} {detection['confidence']:.4f} "
                   f"{detection['bbox'][0]} {detection['bbox'][1]} {detection['bbox'][2]} {detection['bbox'][3]}\n")

def save_image_temp(file_data, temp_path):
    nparr = np.frombuffer(file_data, np.uint8)
    image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    cv2.imwrite(temp_path, image)
    return temp_path

def get_parking_info_from_file(image_name):
    """Read parking spot info from info.txt for the most recent entry of a given image name"""
    if not os.path.exists(INFO_PATH):
        return None
    
    # Group detections by image name and timestamp
    detections_by_timestamp = {}
    with open(INFO_PATH, 'r') as f:
        lines = [line.strip() for line in f.readlines()]
        base_name = os.path.splitext(image_name)[0]
        relevant_lines = [line for line in lines if line.startswith(base_name)]
        
        for line in relevant_lines:
            parts = line.split()
            if len(parts) >= 8:  # Now includes timestamp
                img_name, timestamp, confidence, class_id, x_min, y_min, x_max, y_max = parts[:8]
                key = (img_name, timestamp)
                if key not in detections_by_timestamp:
                    detections_by_timestamp[key] = []
                detections_by_timestamp[key].append({
                    'image_name': img_name,
                    'timestamp': timestamp,
                    'confidence': float(confidence),
                    'class_id': int(class_id),
                    'bbox': [int(x_min), int(y_min), int(x_max), int(y_max)]
                })
    
    if not detections_by_timestamp:
        return None

    # Find the most recent timestamp for this image name
    latest_key = max(detections_by_timestamp.keys(), key=lambda x: x[1])  # Sort by timestamp
    detections = detections_by_timestamp[latest_key]

    # Calculate parking stats
    total_spots = len(detections)
    filled_spots = sum(1 for d in detections if d['class_id'] == 2)
    empty_spots = sum(1 for d in detections if d['class_id'] == 1)
    
    spots_status = []
    for i, detection in enumerate(detections):
        status = 'filled' if detection['class_id'] == 2 else 'empty'
        spots_status.append({'id': i + 1, 'status': status})

    return {
        'total_spots': total_spots,
        'filled_spots': filled_spots,
        'empty_spots': empty_spots,
        'occupancy_rate': float((filled_spots / total_spots * 100) if total_spots > 0 else 0),
        'spots_status': spots_status,
        'detections': detections,
        'timestamp': latest_key[1]  # Use the timestamp from the file
    }

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per minute", "1000 per hour"]
)

overlay_handler = ParkingSpotOverlay()

@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    logger.error(f"Internal server error: {str(error)}")
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    logger.warning(f"Rate limit exceeded: {e.description}")
    return jsonify({'error': f'Rate limit exceeded: {e.description}'}), 429

@app.route('/api/simulation', methods=['GET'])
def get_simulation_samples():
    return jsonify({
        'count': 5,
        'samples': [f'/samples/parking{i+1}.jpg' for i in range(5)]
    })

@app.route('/api/analyze_video', methods=['POST'])
@limiter.limit("2 per minute")
def analyze_video():
    if 'file' not in request.files:
        return jsonify({'error': 'No video file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No video selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid video format'}), 400

    try:
        filename = secure_filename(file.filename)
        file_data = file.read()
        nparr = np.frombuffer(file_data, np.uint8)
        results = process_video(nparr, filename)
        
        for i, frame_result in enumerate(results):
            if 'frame_data' in frame_result and 'detections' in frame_result:
                overlay_image = overlay_handler.create_overlay_image(
                    frame_result['frame_data'],
                    frame_result['detections'],
                    confidence_threshold=0.5
                )
                frame_result['overlay_image'] = base64.b64encode(overlay_image).decode('utf-8')
                
        return jsonify({
            'total_frames': len(results),
            'results': results,
            'average_occupancy': sum(r['occupancy_rate'] for r in results) / len(results) if results else 0
        })
    except Exception as e:
        logger.error(f'Video processing error: {str(e)}')
        return jsonify({'error': 'Failed to process video'}), 500

def process_video(video_data, original_filename):
    results = []
    cap = cv2.VideoCapture(video_data)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * 15)

    try:
        frame_count = 0
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if frame_count % frame_interval == 0:
                base_name = os.path.splitext(original_filename)[0]
                temp_path = os.path.join(UPLOAD_FOLDER, f'{base_name}_frame_{frame_count}.jpg')
                cv2.imwrite(temp_path, frame)
                
                all_predictions = predict(temp_path)
                if len(all_predictions) >= 100:
                    cropped_path = crop(temp_path, all_predictions)
                    cropped_predictions = predict(cropped_path)
                    all_predictions.extend(cropped_predictions)
                
                detections = [{'class_id': pred['label'], 'confidence': pred['confidence'], 'bbox': [int(x) for x in pred['box'].tolist()]} for pred in all_predictions]
                
                total_spots = len(detections)
                filled_spots = sum(1 for d in detections if d['class_id'] == 2)
                empty_spots = sum(1 for d in detections if d['class_id'] == 1)

                spots_status = [{'id': i + 1, 'status': 'filled' if d['class_id'] == 2 else 'empty'} for i, d in enumerate(detections)]

                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = buffer.tobytes()
                frame_result = {
                    'total_spots': total_spots,
                    'filled_spots': filled_spots,
                    'empty_spots': empty_spots,
                    'occupancy_rate': float((filled_spots / total_spots * 100) if total_spots > 0 else 0),
                    'spots_status': spots_status,
                    'detections': detections,
                    'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
                    'frame_data': frame_data
                }
                results.append(frame_result)
                
                frame_name = f"{base_name}_frame_{frame_count}"
                log_detection_to_file(frame_name, detections)
                compile_data(temp_path, all_predictions)
                
                if os.path.exists(temp_path):
                    os.remove(temp_path)
            
            frame_count += 1
            
    finally:
        cap.release()
        
    return results

def analyze_parking_image(file_data, original_filename):
    try:
        start_time = time.time()
        
        base_name = os.path.splitext(original_filename)[0]
        temp_path = os.path.join(UPLOAD_FOLDER, f'{base_name}.jpg')
        save_image_temp(file_data, temp_path)
        
        all_predictions = predict(temp_path)
        if len(all_predictions) >= 100:
            cropped_path = crop(temp_path, all_predictions)
            cropped_predictions = predict(cropped_path)
            all_predictions.extend(cropped_predictions)
        
        detections = [{'class_id': pred['label'], 'confidence': pred['confidence'], 'bbox': [int(x) for x in pred['box'].tolist()]} for pred in all_predictions]
        
        total_spots = len(detections)
        filled_spots = sum(1 for d in detections if d['class_id'] == 2)
        empty_spots = sum(1 for d in detections if d['class_id'] == 1)

        spots_status = [{'id': i + 1, 'status': 'filled' if d['class_id'] == 2 else 'empty'} for i, d in enumerate(detections)]

        log_detection_to_file(base_name, detections)
        compile_data(temp_path, all_predictions)

        result = {
            'total_spots': total_spots,
            'filled_spots': filled_spots,
            'empty_spots': empty_spots,
            'occupancy_rate': float((filled_spots / total_spots * 100) if total_spots > 0 else 0),
            'spots_status': spots_status,
            'detections': detections,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
        nparr = np.frombuffer(file_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        overlay_image = overlay_handler.create_overlay_image(file_data, detections, confidence_threshold=0.5)
        result['overlay_image'] = base64.b64encode(overlay_image).decode('utf-8')
        
        logger.info(f"Image processed in {time.time() - start_time:.2f} seconds with {total_spots} spots")
        
        if os.path.exists(temp_path):
            os.remove(temp_path)
        
        return result
    except Exception as e:
        logger.error(f'Image analysis error: {str(e)}')
        raise

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({'status': 'healthy', 'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')})

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("10 per second")
def analyze_parking():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        filename = secure_filename(file.filename)
        file_data = file.read()
        
        # Process the image and save to info.txt
        analyze_parking_image(file_data, filename)
        
        # Read the results from info.txt
        results = get_parking_info_from_file(filename)
        if not results:
            return jsonify({'error': f'No data found in info.txt for {filename}'}), 404
        
        # Generate overlay image
        nparr = np.frombuffer(file_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        overlay_image = overlay_handler.create_overlay_image(file_data, results['detections'], confidence_threshold=0.5)
        results['overlay_image'] = base64.b64encode(overlay_image).decode('utf-8')
        
        return jsonify(results)
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}')
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(os.path.join(app.static_folder, 'videos'), filename)

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    location_id = request.args.get('location_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not location_id:
        return jsonify({'error': 'location_id parameter is required'}), 400
    
    stats = {
        'location_id': location_id,
        'period': {'start': start_date or 'all time', 'end': end_date or 'current date'},
        'average_occupancy': 65.3,
        'peak_hours': ['08:00-09:00', '17:00-18:00'],
        'lowest_occupancy_hours': ['03:00-04:00', '22:00-23:00'],
        'total_records': 287
    }
    return jsonify(stats)

@app.route('/api/parking_status', methods=['GET'])
def get_current_status():
    location_id = request.args.get('location_id')
    if not location_id:
        return jsonify({'error': 'location_id parameter is required'}), 400
    
    status = {
        'location_id': location_id,
        'total_spots': 10,
        'filled_spots': 6,
        'empty_spots': 4,
        'occupancy_rate': 60.0,
        'last_updated': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    return jsonify(status)

@app.route('/api/detections', methods=['GET'])
def get_detections():
    try:
        limit = int(request.args.get('limit', 100))
        if not os.path.exists(os.path.join(RESULTS_FOLDER, DETECTION_LOG)):
            return jsonify({'error': 'No detections recorded yet'}), 404
        
        detections = []
        with open(os.path.join(RESULTS_FOLDER, DETECTION_LOG), 'r') as f:
            lines = f.readlines()[-limit:]
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 8:
                    detection = {
                        'image_name': parts[0],
                        'class_id': int(parts[1]),
                        'confidence': float(parts[2]),
                        'bbox': [int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6])]
                    }
                    detections.append(detection)
        
        return jsonify({'detections': detections, 'count': len(detections)})
    except Exception as e:
        logger.error(f'Failed to retrieve detections: {str(e)}')
        return jsonify({'error': f'Failed to retrieve detections: {str(e)}'}), 500

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True, threaded=True)