import importlib
import inspect
import torch
from torchvision import transforms
from PIL import Image

# Dynamically import model.py
model_module = importlib.import_module("model")

# Find first class inheriting from nn.Module
ModelClass = None
for name, obj in inspect.getmembers(model_module):
    if inspect.isclass(obj) and issubclass(obj, torch.nn.Module) and obj.__module__ == model_module.__name__:
        ModelClass = obj
        break

if ModelClass is None:
    raise ImportError("❌ Could not find any nn.Module subclass in model.py")

def load_model():
    model = ModelClass()
    model.load_state_dict(torch.load("model.pt", map_location="cpu"))
    model.eval()
    return model

def predict(image_file):
    image = Image.open(image_file).convert("RGB")
    transform = transforms.Compose([
        transforms.Resize((64, 64)),
        transforms.ToTensor(),
    ])
    x = transform(image).unsqueeze(0)
    model = load_model()
    with torch.no_grad():
        output = model(x)
        if len(output.shape) > 1 and output.shape[1] > 1:
            return torch.argmax(output, dim=1).item()
        return output.item()
