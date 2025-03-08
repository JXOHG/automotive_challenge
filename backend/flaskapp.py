from flask import Flask, request, jsonify
import os
import numpy as np
import cv2
import time
from datetime import datetime
import json

# Import your CNN model implementation
# from model import ParkingSpotModel
from flask_cors import CORS
app = Flask(__name__)
CORS(app, resources={r"/api/*": {"origins": "http://localhost:5173"}})  # Explicit origin



# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
DETECTION_LOG = 'detections.txt'  # Text file to log all detections
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

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

def analyze_parking_image(image_path, filename):
    """
    Process the image with your CNN model to detect empty and filled parking spots
    Replace this with your actual model implementation
    """
    # Load and preprocess the image
    image = cv2.imread(image_path)
    # Resize if needed
    # image = cv2.resize(image, (required_width, required_height))
    
    # Here you would use your CNN model to analyze the image
    # model = ParkingSpotModel()
    # results = model.predict(image)
    
    # Mock results for demonstration
    # In production, replace with actual model prediction
    total_spots = 10
    filled_spots = 7
    empty_spots = 3
    
    # Generate mock detection results for each spot
    # In a real implementation, these would come from your CNN model
    spots_status = []
    detections = []
    
    for i in range(1, total_spots + 1):
        # Mock status for demonstration
        status = 'filled' if i <= filled_spots else 'empty'
        spots_status.append({'id': i, 'status': status})
        
        # Create mock bounding box coordinates and confidence
        # In a real implementation, these would come from your model
        if status == 'filled':
            class_id = 1  # 1 for filled spot
            confidence = 0.85 + (np.random.random() * 0.1)  # Random confidence between 0.85 and 0.95
        else:
            class_id = 0  # 0 for empty spot
            confidence = 0.80 + (np.random.random() * 0.15)  # Random confidence between 0.80 and 0.95
            
        # Mock bounding box - in real implementation these would be actual coordinates
        x_min = 100 + (i * 50)
        y_min = 150
        x_max = x_min + 45
        y_max = y_min + 90
        
        # Add to detections list for text file logging
        detections.append({
            'class_id': class_id,
            'confidence': confidence,
            'bbox': [x_min, y_min, x_max, y_max]
        })
    
    # Log detections to text file
    log_detection_to_file(filename, detections)
    
    results = {
        'total_spots': total_spots,
        'filled_spots': filled_spots,
        'empty_spots': empty_spots,
        'occupancy_rate': (filled_spots / total_spots) * 100,
        'spots_status': spots_status,
        'detections': detections,  # Include raw detection data in the JSON response
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    }
    
    return results

# API Routes
@app.route('/api/health', methods=['GET'])
def health_check():
    """API health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    })

@app.route('/api/analyze', methods=['POST'])
def analyze_parking():
    """
    Analyze a parking lot image to identify empty and filled spots
    
    Expects:
    - A 'file' part containing the image
    - Optional 'location_id' parameter to identify the parking lot
    
    Returns:
    - JSON with parking spot analysis results
    """
    # Check if the post request has the file part
    if 'file' not in request.files:
        return jsonify({'error': 'No file provided'}), 400
    
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No file selected'}), 400
    
    if file and allowed_file(file.filename):
        # Create a unique filename
        timestamp = int(time.time())
        location_id = request.form.get('location_id', 'unknown')
        filename = f"{location_id}_{timestamp}_{file.filename}"
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        
        # Save the file
        file.save(file_path)
        
        # Process the image
        results = analyze_parking_image(file_path, filename)
        
        # Save results for historical tracking
        result_filename = f"{location_id}_{timestamp}_results.json"
        result_path = os.path.join(RESULTS_FOLDER, result_filename)
        with open(result_path, 'w') as f:
            json.dump(results, f)
        
        return jsonify(results)
    
    return jsonify({'error': 'Invalid file type'}), 400

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