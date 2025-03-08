import cv2
import torch
import matplotlib.pyplot as plt

# Sample image
image = cv2.imread("test_data/test_images/2012-09-11_15_36_32.jpg")

#OPEN TEXT FILE AND THEN MAKE A PREDICTIONS LIST OF ALL PREDICTIONS INSTEAD OF MANUAL INPUT


predictions = [
    {"Box": torch.tensor([213.5805,  80.8520, 228.7536, 111.6175]), "Label": 1},
    {"Box": torch.tensor([166.2996, 140.1320, 183.7152, 166.1375]), "Label": 1},
    {"Box": torch.tensor([135.5471, 140.7462, 153.4763, 166.8036]), "Label": 1},
    {"Box": torch.tensor([197.6236, 139.6694, 213.8923, 165.2662]), "Label": 1},
    {"Box": torch.tensor([304.6332, 132.6787, 320.6163, 163.0453]), "Label": 1},
    {"Box": torch.tensor([151.4140, 140.3014, 168.6388, 167.4352]), "Label": 1},
    {"Box": torch.tensor([121.1928, 140.7881, 137.9732, 166.6960]), "Label": 1},
    {"Box": torch.tensor([342.9589,  50.1620, 357.3210,  74.7239]), "Label": 1},
    {"Box": torch.tensor([182.5231, 140.1238, 199.8148, 167.1071]), "Label": 1},
    {"Box": torch.tensor([482.5800,  71.6781, 497.8940, 102.9246]), "Label": 1},
    {"Box": torch.tensor([452.3894,  72.5556, 466.9001, 102.4802]), "Label": 1},
]


# Draw bounding boxes
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

plt.figure(figsize=(10, 10))
plt.imshow(image)
plt.axis("off")
plt.show()