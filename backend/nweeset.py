import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision import transforms
from PIL import Image
import cv2
import matplotlib.pyplot as plt
import os
import sys

# Model setup
num_classes = 3
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=False)
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
# model.roi_heads.detections_per_img = 500

# Load model weights (update path as needed)
model.load_state_dict(torch.load("./final_model.pth", map_location=torch.device('cpu')))
model.eval()

# Image transform
transform = transforms.Compose([
    transforms.ToTensor(),
])

folder_path = sys.argv[1]
output_file = sys.argv[2]

def predict(image_path):
    """Make predictions on the input image"""
    predictions = []
    image = Image.open(image_path).convert('RGB')
    image_tensor = transform(image).unsqueeze(0)

    with torch.no_grad():
        prediction = model(image_tensor)

    boxes = prediction[0]['boxes']
    labels = prediction[0]['labels']
    scores = prediction[0]['scores']

    for i, box in enumerate(boxes):
        predictions.append({
            "box": box,
            "label": int(labels[i]),
            "confidence": float(scores[i])
        })
    
    return predictions

    """
def crop(image_path, predictions):
    # Crop image if predictions exceed 100, based on highest box
    highest = 640
    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"].tolist())
        if y_max < highest:
            highest = y_max

    image = Image.open(image_path)
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    output_dir = os.path.dirname(image_path)
    cropped_path = os.path.join(output_dir, f"{base_name}_c.jpg")

    crop = image.crop((0, 0, 640, highest + 10))
    crop.save(cropped_path)
    return cropped_path
    """

def compile_data(image_path, predictions):
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    f = open(output_file, "a")
    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"].tolist())
        f.write(f'{base_name}.jpg {prediction["label"]} {prediction["confidence"]} {x_min} {y_min} {x_max} {y_max}\n') 
    f.close()

def display_image(image_path, predictions):
    """Display image with bounding boxes and labels"""
    image = cv2.imread(image_path)
    
    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"].tolist())
        label = str(prediction["label"])
        confidence = prediction["confidence"]
        
        # Green for label 1, Red for others
        color = (0, 255, 0) if label == "1" else (255, 0, 0)
        
        # Draw rectangle and label
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, 2)
        display_text = f"{label} ({confidence:.2f})"
        cv2.putText(image, display_text, (x_min, y_min - 5), 
                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, color, 1, cv2.LINE_AA)
    
    # Convert BGR to RGB for matplotlib
    image_rgb = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
    plt.figure(figsize=(10, 10))
    plt.imshow(image_rgb)
    plt.axis("off")
    plt.show()

def main():
    # Specify your image path here
    for image_path in os.listdir(folder_path):
        image_path = f"{folder_path}\\{image_path}"
    
        # Make initial predictions on full image
        all_predictions = predict(image_path)
    
        # Check if predictions exceed 100 and crop if necessary
        """
        if len(all_predictions) >= 100:
            cropped_path = crop(image_path, all_predictions)
            # Get predictions from cropped image
            cropped_predictions = predict(cropped_path)
            # Combine all predictions
            all_predictions.extend(cropped_predictions)

        if os.path.exists(cropped_path):
            os.remove(cropped_path)
        """
    
        # Append all predictions to text file
        compile_data(image_path, all_predictions)
    
        # Display original image with all predictions
        # display_image(image_path, all_predictions)

if __name__ == "__main__":
    main()