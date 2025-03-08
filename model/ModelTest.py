import torch
import torchvision
import cv2
import numpy as np
import os
import matplotlib.pyplot as plt
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
from torchvision import transforms
from PIL import Image


def split_image_into_thirds(image_path, output_dir):
    """
    Splits an image into three horizontal thirds and saves them.
    """
    os.makedirs(output_dir, exist_ok=True) 
    image = Image.open(image_path)

    width, height = image.size
    half_height = height // 2

    base_name = os.path.splitext(os.path.basename(image_path))[0]
    top_path = os.path.join(output_dir, f"{base_name}_top.jpg")
    #middle_path = os.path.join(output_dir, f"{base_name}_middle.jpg")
    bottom_path = os.path.join(output_dir, f"{base_name}_bottom.jpg")

    top_third = image.crop((0, 0, width, half_height))
    #middle_third = image.crop((0, third_height, width, 2 * third_height))
    bottom_third = image.crop((0, half_height, width, height))

    top_third.save(top_path)
    #middle_third.save(middle_path)
    bottom_third.save(bottom_path)

    return [top_path, bottom_path]


def load_model(model_path, num_classes=3):
    """
    Load the trained Faster R-CNN model.
    """
    model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=False)
    in_features = model.roi_heads.box_predictor.cls_score.in_features
    model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)

    model.load_state_dict(torch.load(model_path, map_location=torch.device('cpu')))
    model.eval()
    return model


def predict_images(model, image_paths):
    """
    Runs predictions on a list of images.
    """
    transform = transforms.Compose([transforms.ToTensor()])
    predictions = {}

    for image_path in image_paths:
        image = Image.open(image_path).convert('RGB')
        image_tensor = transform(image).unsqueeze(0)

        with torch.no_grad():
            prediction = model(image_tensor)

        boxes = prediction[0]['boxes']
        labels = prediction[0]['labels']

        predictions[image_path] = [
            {"box": box.tolist(), "Label": label.item()}  # Fix unnecessary torch.tensor
            for box, label in zip(boxes, labels)
        ]

    return predictions


def draw_predictions(image_path, predictions, output_path):
    """
    Draws bounding boxes on an image based on model predictions.
    """
    image = cv2.imread(image_path)
    image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)  

    for prediction in predictions:
        x_min, y_min, x_max, y_max = map(int, prediction["box"])
        label = str(prediction["Label"])
        if label == "1":
            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (0, 255, 0), 2)
            cv2.putText(image, label, (x_min, y_min - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, (0, 255, 0), 1, cv2.LINE_AA)
        else:
            cv2.rectangle(image, (x_min, y_min), (x_max, y_max), (255, 0, 0), 2)
            cv2.putText(image, label, (x_min, y_min - 5), cv2.FONT_HERSHEY_SIMPLEX, 
                        0.5, (255, 0, 0), 1, cv2.LINE_AA)

    cv2.imwrite(output_path, cv2.cvtColor(image, cv2.COLOR_RGB2BGR))  
    plt.figure(figsize=(8, 8))
    plt.imshow(image)
    plt.axis("off")
    plt.show()


def merge_images(image_paths, output_path):
    """
    Merges three vertically split images back into a single image.
    """
    images = [Image.open(img) for img in image_paths]

    total_height = sum(img.height for img in images)
    width = images[0].width

    merged_image = Image.new("RGB", (width, total_height))
    y_offset = 0
    for img in images:
        merged_image.paste(img, (0, y_offset))
        y_offset += img.height

    merged_image.save(output_path)
    plt.figure(figsize=(10, 10))
    plt.imshow(merged_image)
    plt.axis("off")
    plt.show()


# Main Pipeline
image_path = "test_data/test_images/2012-09-11_15_36_32.jpg"  
output_dir = "Cropped_Images"
model_path = "final_model.pth"


cropped_images = split_image_into_thirds(image_path, output_dir)
model = load_model(model_path)
predictions = predict_images(model, cropped_images)

for img_path in cropped_images:
    base_name, ext = os.path.splitext(img_path)
    annotated_path = f"{base_name}_annotated{ext}"  

    if img_path in predictions and predictions[img_path]:  
        draw_predictions(img_path, predictions[img_path], annotated_path)


annotated_images = [img.replace(".jpg", "_annotated.jpg") for img in cropped_images]
merged_output_path = "Cropped_Images/merged_annotated.jpg"
merge_images(annotated_images, merged_output_path)
