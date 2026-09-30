import torch
import torch.nn as nn


class GRUWorldModel(nn.Module):
    def __init__(self, input_size, hidden_size=128, num_layers=1):
        super().__init__()
        self.input_size = input_size
        self.hidden_size = hidden_size
        self.num_layers = num_layers
        self.gru = nn.GRU(input_size, hidden_size, num_layers=num_layers, batch_first=True)
        self.head = nn.Linear(hidden_size, input_size)

    def forward(self, x):
        # x: [batch, seq_len, input_size]
        out, _ = self.gru(x)
        last = out[:, -1, :]
        return self.head(last)  # predicted S(t+1): [batch, input_size]
