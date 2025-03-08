import cv2
import torch
import matplotlib.pyplot as plt
import os


image_path = "test_data/test_images/2012-09-11_15_36_32.jpg" #THIS NEEDS TO CHANGE DYNAMICALLY
image = cv2.imread(image_path)
label_file = "test_data/test_labels.txt" #THIS NEEDS TO CHANGE DYNAMICALLY

def load_predictions(label_file, image_name):
    predictions = []
    
    with open(label_file, "r") as f:
        for line in f:
            parts = line.strip().split()
            filename, label, x_min, y_min, x_max, y_max = parts[0], int(parts[2]), float(parts[3]), float(parts[4]), float(parts[5]), float(parts[6])

#Image_name class_id confidence_score x_min y_min x_max y_max

            if filename == image_name:
                predictions.append({
                    "Box": [x_min, y_min, x_max, y_max], 
                    "Label": label
                })

    return predictions

image_filename = image_path.split("/")[-1]  

predictions = load_predictions(label_file, image_filename)

# Draw bounding boxes
for prediction in predictions:
    x_min, y_min, x_max, y_max = map(int, prediction["Box"])
    label = str(prediction["Label"])

    if label == "1":
        color = (0, 255, 0)  
    else:
        color = (255, 0, 0)

    cv2.rectangle(image, (x_min, y_min), (x_max, y_max), color, 2)
    cv2.putText(image, label, (x_min, y_min - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, color, 1, cv2.LINE_AA)

output_dir = "test_data/annotated_images" #CHANGE TO WANTED PATH
os.makedirs(output_dir, exist_ok=True) 

output_path = os.path.join(output_dir, f"{image_filename}_annotated.jpg")
cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))


