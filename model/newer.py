import torch
import torchvision
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision import transforms
from PIL import Image
import cv2
import matplotlib.pyplot as plt
import numpy as np
import os

num_classes = 3
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=False)

in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)
model.roi_heads.detections_per_img = 500

model.load_state_dict(torch.load("C:\\Users\\rayta\\Documents\\AIC\\final_model.pth", map_location=torch.device('cpu')))
model.eval() 

transform = transforms.Compose([
    transforms.ToTensor(),
])

predictions = []

def predict(image_path):
    image = Image.open(image_path).convert('RGB')
    image_tensor = transform(image).unsqueeze(0) 

    with torch.no_grad():
        prediction = model(image_tensor)

    boxes = prediction[0]['boxes']
    labels = prediction[0]['labels']
    scores = prediction[0]['scores']

    image = cv2.imread(image_path)
    for i, box in enumerate(boxes):
        # print(f'Predicted box: {box}, Label: {labels[i]}, Confidence: {scores[i]}')
        predictions.append({"box": box, "label": int(labels[i]), "confidence": scores[i]})

def crop(image_path):
    highest = 640
    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"].tolist())
        if y_max < highest:
            highest = y_max

    image = Image.open(image_path)

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    # Need to make directory and stuff
    path = os.path.join("C:\\Users\\rayta\\Documents\\AIC\\parking_dataset\\Cropped_Images", f"{base_name}_c.jpg")

    crop = image.crop((0, 0, 640, highest + 10))
    crop.save(path)
    return path

def display_image(image_path):
    image = cv2.imread(image_path)
    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"].tolist())
        label = str(prediction["label"])
        cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
        cv2.putText(image, label, (x_min, y_min - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                0.5, (0, 255, 0), 1, cv2.LINE_AA)
    
    plt.figure(figsize=(10, 10))
    plt.imshow(image)
    plt.axis("off")
    plt.show()

def compile_data(image_path):
    base_name = os.path.splitext(os.path.basename(image_path))[0]
    f = open("info.txt", "w")
    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"].tolist())
        f.write(f'{base_name} {prediction["confidence"]} {prediction["label"]} {x_min} {y_min} {x_max} {y_max}\n') 
    f.close()   
    
image_path = "C:\\Users\\rayta\\Documents\\AIC\\parking_test_data\\test_data\\test_images\\2012-09-11_15_36_32.jpg"
predict(image_path)
if len(predictions) >= 100:
    cropped_path = crop(image_path)
    predict(cropped_path)
compile_data(image_path)
display_image(image_path)