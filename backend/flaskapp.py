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

# Import your CNN model implementation
# from model import ParkingSpotModel
from flask_cors import CORS
app = Flask(__name__, static_folder='public', static_url_path='')
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})  # Explicit origin




# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
DETECTION_LOG = 'detections.txt'  # Text file to log all detections
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'mp4', 'avi', 'mov'}
MAX_CONTENT_LENGTH = 100 * 1024 * 1024  # 100MB


app.config['MAX_CONTENT_LENGTH'] = MAX_CONTENT_LENGTH

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def log_detection_to_file(image_name, detections):
    """
    Log detection results to a text file in the format:
    Image_name class_id confidence_score x_min y_min x_max y_max
    
    Args:
        image_name: Name of the processed image
        detections: List of dictionaries with detection results
    """
    with open(os.path.join(RESULTS_FOLDER, DETECTION_LOG), 'a') as f:
        for detection in detections:
            # Format: image_name class_id confidence x_min y_min x_max y_max
            f.write(f"{image_name} {detection['class_id']} {detection['confidence']:.4f} "
                   f"{detection['bbox'][0]} {detection['bbox'][1]} {detection['bbox'][2]} {detection['bbox'][3]}\n")

# Add rate limiting (install flask-limiter)
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

limiter = Limiter(
    app=app,
    key_func=get_remote_address,
    default_limits=["500 per minute", "1000 per hour"]  # Increased limits
)


@limiter.limit("10 per second")  # More realistic for video processing # Adjust based on your hardware
# Error handlers
@app.errorhandler(404)
def not_found(error):
    return jsonify({'error': 'Resource not found'}), 404

@app.errorhandler(500)
def internal_error(error):
    return jsonify({'error': 'Internal server error'}), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return jsonify({'error': f'Rate limit exceeded: {e.description}'}), 429


@app.route('/api/simulation', methods=['GET'])
def get_simulation_samples():
    return jsonify({
        'count': 5,  # Match number of sample images
        'samples': [f'/samples/parking{i+1}.jpg' for i in range(5)]
    })
# Add new video analysis endpoint
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
       # Process video from memory
        file_data = file.read()
        nparr = np.frombuffer(file_data, np.uint8)
        results = process_video(nparr)
        
        return jsonify({
            'total_frames': len(results),
            'results': results,
            'average_occupancy': sum(r['occupancy_rate'] for r in results)/len(results)
        })
        
    except Exception as e:
        app.logger.error(f'Video processing error: {str(e)}')
        return jsonify({'error': 'Failed to process video'}), 500
    finally:
        if os.path.exists(video_path):
            os.remove(video_path)
def process_video(video_path):
    results = []
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    frame_interval = int(fps * 15)  # 15 seconds interval
    frame_count = 0

    try:
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
                
            # Process every 15th frame
            if cap.get(cv2.CAP_PROP_POS_FRAMES) % 15 == 0:
                # Process frame directly
                _, buffer = cv2.imencode('.jpg', frame)
                frame_data = buffer.tobytes()
                frame_result = analyze_parking_image(frame_data)
                results.append(frame_result)
            
    finally:
        cap.release()
        
    return results


def analyze_parking_image(file_data):
    try:
        # Read image directly from memory
        nparr = np.frombuffer(file_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        if image is None:
            raise ValueError("Failed to decode image")

        # Mock CNN model implementation (unchanged)
        total_spots = 10
        filled_spots = np.random.randint(3, 8)
        empty_spots = total_spots - filled_spots
        
        spots_status = []
        detections = []
        
        for i in range(1, total_spots + 1):
            status = 'filled' if i <= filled_spots else 'empty'
            spots_status.append({'id': i, 'status': status})
            
            class_id = 1 if status == 'filled' else 0
            confidence = np.random.uniform(0.8, 0.95)
            
            x_min = 100 + (i * 50)
            y_min = 150
            x_max = x_min + 45
            y_max = y_min + 90
            
            detections.append({
                'class_id': class_id,
                'confidence': confidence,
                'bbox': [x_min, y_min, x_max, y_max]
            })
        
        return {
            'total_spots': total_spots,
            'filled_spots': filled_spots,
            'empty_spots': empty_spots,
            'occupancy_rate': (filled_spots / total_spots) * 100,
            'spots_status': spots_status,
            'detections': detections,
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        }
        
    except Exception as e:
        app.logger.error(f'Image analysis error: {str(e)}')
        raise
    
# API Routes
@app.route('/videos/<path:filename>')
def serve_video(filename):
    return send_from_directory(os.path.join(app.static_folder, 'videos'), filename)
@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/analyze', methods=['POST'])
@limiter.limit("5 per second")  # More realistic for video processing
def analyze_parking():
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400

    if not allowed_file(file.filename):
        return jsonify({'error': 'Invalid file type'}), 400

    try:
        # Process file directly from memory
        file_data = file.read()
        results = analyze_parking_image(file_data)
        return jsonify(results)
    
    except Exception as e:
        app.logger.error(f'Error processing image: {str(e)}')
        return jsonify({'error': 'Failed to process image'}), 500

@app.route('/api/statistics', methods=['GET'])
def get_statistics():
    """
    Get historical statistics for a specific parking location
    
    Query parameters:
    - location_id: ID of the parking lot
    - start_date: Optional start date for statistics (YYYY-MM-DD)
    - end_date: Optional end date for statistics (YYYY-MM-DD)
    
    Returns:
    - JSON with historical statistics
    """
    location_id = request.args.get('location_id')
    start_date = request.args.get('start_date')
    end_date = request.args.get('end_date')
    
    if not location_id:
        return jsonify({'error': 'location_id parameter is required'}), 400
    
    # Here you would query your stored results based on the parameters
    # For demonstration, we'll return mock data
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
    """
    Get the most recent parking status for a specific location
    
    Query parameters:
    - location_id: ID of the parking lot
    
    Returns:
    - JSON with the most recent parking analysis results
    """
    location_id = request.args.get('location_id')
    
    if not location_id:
        return jsonify({'error': 'location_id parameter is required'}), 400
    
    # Here you would find the most recent result for the specified location
    # For demonstration, we'll return mock data
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
    """
    Get all detection records from the text file
    
    Query parameters:
    - limit: Optional limit on number of records to return (default: 100)
    
    Returns:
    - JSON with detection records
    """
    try:
        limit = int(request.args.get('limit', 100))
        
        if not os.path.exists(os.path.join(RESULTS_FOLDER, DETECTION_LOG)):
            return jsonify({'error': 'No detections recorded yet'}), 404
        
        detections = []
        with open(os.path.join(RESULTS_FOLDER, DETECTION_LOG), 'r') as f:
            lines = f.readlines()[-limit:]  # Get the last 'limit' lines
            
            for line in lines:
                parts = line.strip().split()
                if len(parts) >= 8:  # Make sure we have all required fields
                    detection = {
                        'image_name': parts[0],
                        'class_id': int(parts[1]),
                        'confidence': float(parts[2]),
                        'bbox': [int(parts[3]), int(parts[4]), int(parts[5]), int(parts[6])]
                    }
                    detections.append(detection)
        
        return jsonify({'detections': detections, 'count': len(detections)})
    
    except Exception as e:
        return jsonify({'error': f'Failed to retrieve detections: {str(e)}'}), 500

# Main function to run the app
if __name__ == '__main__':
    # For production, you would use a proper WSGI server
    # and not run with debug=True
    app.run(host='0.0.0.0', port=5000, debug=True)