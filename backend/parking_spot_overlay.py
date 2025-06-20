import cv2
import numpy as np
from io import BytesIO
import logging

logger = logging.getLogger(__name__)

class ParkingSpotOverlay:
    def __init__(self):
        # Colors in BGR format - Swapped colors for 1 and 2
        self.colors = {
            1: (0, 255, 0),    # Empty spot (Green)
            2: (0, 0, 255),    # Filled spot (Red)
            3: (255, 165, 0)   # Other/Unknown (Blue)
        }
        self.default_color = (255, 255, 0)  # Default color for unknown classes (Yellow)
        
    def draw_detections(self, image, detections, confidence_threshold=0.5):
        try:
            annotated_image = image.copy()
            
            for detection in detections:
                if detection['confidence'] < confidence_threshold:
                    continue
                    
                x_min, y_min, x_max, y_max = detection['bbox']
                class_id = detection['class_id']
                color = self.colors.get(class_id, self.default_color)
                
                cv2.rectangle(annotated_image, (x_min, y_min), (x_max, y_max), color, 2)
                
                # Updated label logic: 2 is filled, 1 is empty
                label = f"{'Filled' if class_id == 2 else 'Empty'}: {detection['confidence']:.2f}"
                
                text_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
                cv2.rectangle(
                    annotated_image, 
                    (x_min, y_min - text_size[1] - 10), 
                    (x_min + text_size[0], y_min), 
                    color, 
                    -1
                )
                cv2.putText(
                    annotated_image, 
                    label, 
                    (x_min, y_min - 5), 
                    cv2.FONT_HERSHEY_SIMPLEX, 
                    0.5, 
                    (255, 255, 255), 
                    1, 
                    cv2.LINE_AA
                )
                
            # Updated stats logic
            total_spots = len([d for d in detections if d['confidence'] >= confidence_threshold])
            filled_spots = len([d for d in detections if d['class_id'] == 2 and d['confidence'] >= confidence_threshold])
            empty_spots = len([d for d in detections if d['class_id'] == 1 and d['confidence'] >= confidence_threshold])
            
            summary_text = f"Total: {total_spots} | Filled: {filled_spots} | Empty: {empty_spots}"
            cv2.putText(
                annotated_image,
                summary_text,
                (10, annotated_image.shape[0] - 10),
                cv2.FONT_HERSHEY_SIMPLEX,
                0.7,
                (255, 255, 255),
                2,
                cv2.LINE_AA
            )
            
            return annotated_image
            
        except Exception as e:
            logger.error(f"Error drawing detections: {str(e)}")
            return image
    def create_overlay_image(self, image_data, detections, confidence_threshold=0.5):
        try:
            nparr = np.frombuffer(image_data, np.uint8)
            image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
            if image is None:
                raise ValueError("Failed to decode image")
            annotated_image = self.draw_detections(image, detections, confidence_threshold)
            _, buffer = cv2.imencode('.jpg', annotated_image)
            return buffer.tobytes()
        except Exception as e:
            logger.error(f"Error creating overlay: {str(e)}")
            return image_data