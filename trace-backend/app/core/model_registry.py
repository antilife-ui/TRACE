import os
import torch
import joblib
from app.models.gru_world_model import GRUWorldModel


class ModelRegistry:
    def __init__(self):
        self.loaded = False
        self.model = None
        self.scaler = None
        self.config = {}

    def load(self, checkpoint_path="checkpoints/world_model.pt", scaler_path="checkpoints/scaler.pkl"):
        if not os.path.exists(checkpoint_path):
            self.loaded = False
            return
        ckpt = torch.load(checkpoint_path, map_location="cpu")
        model = GRUWorldModel(ckpt["input_size"], ckpt["hidden_size"], ckpt["num_layers"])
        model.load_state_dict(ckpt["model_state_dict"])
        model.eval()
        self.model = model
        self.scaler = joblib.load(scaler_path) if os.path.exists(scaler_path) else None
        self.config = ckpt
        self.loaded = True


registry = ModelRegistry()
