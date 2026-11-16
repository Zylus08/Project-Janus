import torch
import torch.nn as nn
import torch.nn.functional as F

class HalfKPNNUE(nn.Module):
    """
    Candidate N1: HalfKP-40960 -> 128x2 -> 32 -> 1
    Shared Feature Transformer weights across White and Black perspectives.
    Clipped ReLU activations: clamp(0.0, 1.0).
    Input:
      w_indices: 1D Tensor of active White perspective feature indices [0, 40959]
      w_offsets: 1D Tensor of offsets for each position in the batch
      b_indices: 1D Tensor of active Black perspective feature indices [0, 40959]
      b_offsets: 1D Tensor of offsets for each position in the batch
      stm: 1D Tensor of side-to-move (1 for White, 0 for Black)
    """
    def __init__(self, feature_count=40960, hidden_dim=128, dense_dim=32):
        super(HalfKPNNUE, self).__init__()
        self.feature_count = feature_count
        self.hidden_dim = hidden_dim
        self.dense_dim = dense_dim
        
        # Shared Feature Transformer
        self.ft_weights = nn.Parameter(torch.randn(feature_count, hidden_dim) * 0.01)
        self.ft_biases = nn.Parameter(torch.zeros(hidden_dim))
        
        # Dense Layer 1: 256 -> 32
        self.fc1 = nn.Linear(hidden_dim * 2, dense_dim, bias=True)
        # Dense Layer 2: 32 -> 1
        self.fc2 = nn.Linear(dense_dim, 1, bias=True)
        
        # Weight initialization
        nn.init.kaiming_normal_(self.fc1.weight, nonlinearity='relu')
        nn.init.zeros_(self.fc1.bias)
        nn.init.normal_(self.fc2.weight, std=0.01)
        nn.init.zeros_(self.fc2.bias)

    def forward_accumulators(self, w_indices, w_offsets, b_indices, b_offsets):
        # Sparse embedding bag: sum active feature vectors
        acc_w = F.embedding_bag(w_indices, self.ft_weights, w_offsets, mode='sum') + self.ft_biases
        acc_b = F.embedding_bag(b_indices, self.ft_weights, b_offsets, mode='sum') + self.ft_biases
        return acc_w, acc_b

    def forward(self, w_indices, w_offsets, b_indices, b_offsets, stm):
        acc_w, acc_b = self.forward_accumulators(w_indices, w_offsets, b_indices, b_offsets)
        
        # Clipped ReLU activation [0.0, 1.0]
        h_w = torch.clamp(acc_w, 0.0, 1.0)
        h_b = torch.clamp(acc_b, 0.0, 1.0)
        
        # Order by Side-To-Move: (friendly, enemy)
        # stm is 1 for White, 0 for Black
        stm_expanded = stm.unsqueeze(1) # [B, 1]
        friendly = torch.where(stm_expanded == 1, h_w, h_b)
        enemy = torch.where(stm_expanded == 1, h_b, h_w)
        
        cat = torch.cat([friendly, enemy], dim=1) # [B, 256]
        
        # Dense layers
        x = torch.clamp(self.fc1(cat), 0.0, 1.0)
        logit = self.fc2(x) # [B, 1]
        
        return logit

    def evaluate_centipawns(self, w_indices, w_offsets, b_indices, b_offsets, stm, tau=400.0):
        with torch.no_grad():
            logit = self.forward(w_indices, w_offsets, b_indices, b_offsets, stm)
            return logit * tau
