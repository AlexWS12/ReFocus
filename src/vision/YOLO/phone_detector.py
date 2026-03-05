from ultralytics import YOLO
 
#template extracted from https://www.ultralytics.com/glossary/object-detection

# Load the latest YOLO26n model (nano version for speed)
model = YOLO("yolo26n.pt")

# Run inference on an image from a URL
results = model("https://ultralytics.com/images/bus.jpg") #we should add a second parameter to specify the object we'll be recognizing

# Display the results with bounding boxes
results[0].show()