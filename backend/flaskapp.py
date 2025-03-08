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
import torch
import torchvision
from torchvision.models.detection import fasterrcnn_resnet50_fpn
from torchvision.transforms import functional as F
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "http://172.30.179.110:5173"}})  # Updated to allow simulator’s frontend

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
DETECTION_LOG = 'detections.txt'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
MODEL_PATH = os.path.join(BASE_DIR, 'final_model.pth')

app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Load the R-CNN model
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = fasterrcnn_resnet50_fpn(pretrained=False, num_classes=3)
model.load_state_dict(torch.load(MODEL_PATH, map_location=device, weights_only=True))
model.eval()
model.to(device)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_detection_to_file(image_name, detections):
    with open(os.path.join(RESULTS_FOLDER, DETECTION_LOG), 'a') as f:
        for detection in detections:
            f.write(f"{image_name} {detection['class_id']} {detection['confidence']:.4f} "
                   f"{detection['bbox'][0]} {detection['bbox'][1]} {detection['bbox'][2]} {detection['bbox'][3]}\n")

def preprocess_image(image):
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    tensor = F.to_tensor(image_rgb).unsqueeze(0).to(device)
    return tensor

# Rate limiting
limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per minute", "1000 per hour"]
)

# Error handlers
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

# API Routes
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
        file_data = file.read()
        nparr = np.frombuffer(file_data, np.uint8)
        results = process_video(nparr)
        return jsonify({
            'total_frames': len(results),
            'results': results,
            'average_occupancy': sum(r['occupancy_rate'] for r in results) / len(results) if results else 0
        })
    except Exception as e:
        logger.error(f'Video processing error: {str(e)}')
        return jsonify({'error': 'Failed to process video'}), 500

def process_video(video_data):
    results = []
    cap = cv2.VideoCapture(video_data)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * 15)  # Process every 15 seconds

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            if cap.get(cv2.CAP_PROP_POS_FRAMES) % 15 == 0:
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = buffer.tobytes()
                frame_result = analyze_parking_image(frame_data)
                results.append(frame_result)
            
    finally:
        cap.release()
        
    return results

def analyze_parking_image(file_data):
    try:
        start_time = time.time()
        nparr = np.frombuffer(file_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Failed to decode image")

        input_tensor = preprocess_image(image)
        with torch.no_grad():
            predictions = model(input_tensor)[0]

        boxes = predictions['boxes'].cpu().numpy()
        labels = predictions['labels'].cpu().numpy()
        scores = predictions['scores'].cpu().numpy()

        confidence_threshold = 0.5
        valid_indices = scores >= confidence_threshold
        boxes = boxes[valid_indices]
        labels = labels[valid_indices]
        scores = scores[valid_indices]

        total_spots = len(boxes)
        filled_spots = np.sum(labels == 1)  # Assuming 1 is "filled"
        empty_spots = total_spots - filled_spots

        spots_status = []
        detections = []
        for i, (box, label, score) in enumerate(zip(boxes, labels, scores)):
            status = 'filled' if label == 1 else 'empty'
            spots_status.append({'id': i + 1, 'status': status})
            detections.append({
                'class_id': int(label),
                'confidence': float(score),
                'bbox': [int(x) for x in box]
            })

        log_detection_to_file('current_image', detections)

        result = {
            'total_spots': int(total_spots),
            'filled_spots': int(filled_spots),
            'empty_spots': int(empty_spots),
            'occupancy_rate': float((filled_spots / total_spots * 100) if total_spots > 0 else 0),
            'spots_status': spots_status,
            'detections': detections,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        logger.info(f"Image processed in {time.time() - start_time:.2f} seconds")
        return result
    except Exception as e:
        logger.error(f'Image analysis error: {str(e)}')
        raise

@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(os.path.join(app.static_folder, 'videos'), filename)

@app.route('/api/health', methods=['GET'])
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

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
        file_data = file.read()
        results = analyze_parking_image(file_data)
        return jsonify(results)
    except Exception as e:
        logger.error(f'Error processing image: {str(e)}')
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    location_id = request.args.get('location_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not location_id:
        return jsonify({'error': 'location_id parameter is required'}), 400
    
    stats = {
        'location_id': location_id,
        'period': {
            'start': start_date or 'all time',
            'end': end_date or 'current date'
        },
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