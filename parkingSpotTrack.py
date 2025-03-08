import torch
import torchvision
from torchvision.models.detection import FasterRCNN
from torchvision.models.detection.faster_rcnn import FastRCNNPredictor
import torch.optim as optim
from torchvision import transforms
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os


bounding_boxes_by_image = {}

with open('train_labels.txt', 'r') as f:
    for line in f:
        parts = line.split()
        filename = parts[0]
        classification = parts[1]
        box_top_left_x = float(parts[2])  
        box_top_left_y = float(parts[3])  
        box_bottom_right_x = float(parts[4])  
        box_bottom_right_y = float(parts[5])  

        bounding_box = (classification, (box_top_left_x, box_top_left_y, box_bottom_right_x, box_bottom_right_y))

        if filename not in bounding_boxes_by_image:
            bounding_boxes_by_image[filename] = []

        bounding_boxes_by_image[filename].append(bounding_box)


class ParkingSpaceDataset(Dataset):
    def __init__(self, bounding_boxes_by_image, transform=None):
        self.image_folder = "./train_images" 
        self.bounding_boxes_by_image = bounding_boxes_by_image
        self.transform = transform
        self.image_files = list(bounding_boxes_by_image.keys()) 
    
    def __len__(self):
        return len(self.image_files)
    
    def __getitem__(self, idx):
        image_file = self.image_files[idx]
        image_path = os.path.join(self.image_folder, image_file)

        image = Image.open(image_path).convert('RGB')
        bounding_boxes = self.bounding_boxes_by_image[image_file]
        boxes = torch.tensor([box[1] for box in bounding_boxes], dtype=torch.float32)
        labels = torch.tensor([1 if box[0] == '1' else 2 for box in bounding_boxes], dtype=torch.long)
        
        areas = torch.tensor([((box[1][2] - box[1][0]) * (box[1][3] - box[1][1])) for box in bounding_boxes], dtype=torch.float32)
        iscrowd = torch.zeros_like(labels)  

        target = {
            'boxes': boxes,
            'labels': labels,
            'area': areas,
            'iscrowd': iscrowd
        }
        
        if self.transform:
            image = self.transform(image)
        
        return image, target

    

# Faster R-CNN model, ResNet50 backbone
model = torchvision.models.detection.fasterrcnn_resnet50_fpn(pretrained=True)

# Number of classes 
num_classes = 3  
in_features = model.roi_heads.box_predictor.cls_score.in_features
model.roi_heads.box_predictor = FastRCNNPredictor(in_features, num_classes)


device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
model.to(device)


transform = transforms.Compose([
    transforms.Resize((800, 800)), 
    transforms.ToTensor(),
])


dataset = ParkingSpaceDataset(bounding_boxes_by_image, transform=transform)
dataloader = DataLoader(dataset, batch_size=4, shuffle=True, collate_fn=lambda x: tuple(zip(*x)))


model.train()


optimizer = optim.SGD(model.parameters(), lr=0.005, momentum=0.9, weight_decay=0.0005)


num_epochs = 10
for epoch in range(num_epochs):
    total_loss = 0
    for images, targets in dataloader:
        images = [image.to(device) for image in images]
        targets = [{k: v.to(device) for k, v in t.items()} for t in targets]

        optimizer.zero_grad()
        loss_dict = model(images, targets)
        losses = sum(loss for loss in loss_dict.values())
        losses.backward()
        optimizer.step()

        total_loss += losses.item()

    print(f"Epoch {epoch+1}/{num_epochs}, Loss: {total_loss/len(dataloader)}")



model.eval()  
image_path = './test_data/test_images/2012-09-11_15_36_32.jpg'
image = Image.open(image_path).convert('RGB')
image_tensor = transform(image).unsqueeze(0).to(device)

with torch.no_grad():
    prediction = model(image_tensor)


boxes = prediction[0]['boxes']
labels = prediction[0]['labels']
scores = prediction[0]['scores']  


for i, box in enumerate(boxes):
    print(f"Predicted box: {box}, Label: {labels[i]}, Confidence: {scores[i]}")
