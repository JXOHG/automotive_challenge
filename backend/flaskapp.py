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
CORS(app)

# Configuration
UPLOAD_FOLDER = 'uploads'
RESULTS_FOLDER = 'results'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}

# Create folders if they don't exist
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(RESULTS_FOLDER, exist_ok=True)

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def analyze_parking_image(image_path):
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
    results = {
        'total_spots': 10,
        'filled_spots': 7,
        'empty_spots': 3,
        'occupancy_rate': 70.0,
        'spots_status': [
            {'id': 1, 'status': 'filled'},
            {'id': 2, 'status': 'filled'},
            {'id': 3, 'status': 'empty'},
            {'id': 4, 'status': 'filled'},
            {'id': 5, 'status': 'filled'},
            {'id': 6, 'status': 'empty'},
            {'id': 7, 'status': 'filled'},
            {'id': 8, 'status': 'filled'},
            {'id': 9, 'status': 'filled'},
            {'id': 10, 'status': 'empty'}
        ],
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
        results = analyze_parking_image(file_path)
        
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

# Main function to run the app
if __name__ == '__main__':
    # For production, you would use a proper WSGI server
    # and not run with debug=True
    app.run(host='0.0.0.0', port=5000, debug=True)