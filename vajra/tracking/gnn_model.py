import torch
import torch.nn as nn
from torch_geometric.nn import GATv2Conv
from typing import Dict

class WeatherGNN(nn.Module):
    """
    Spatio-Temporal Graph Neural Network operating on an icosahedral spherical mesh.
    Combines spatial GATv2 message passing with recurrent GRU temporal aggregation.
    """

    def __init__(
        self,
        in_channels: int = 8,
        hidden_dim: int = 128,
        num_heads: int = 4,
        edge_dim: int = 3,
        num_classes: int = 3,
        dropout: float = 0.1
    ):
        super().__init__()
        self.in_channels = in_channels
        self.hidden_dim = hidden_dim

        self.input_proj = nn.Sequential(
            nn.Linear(in_channels, hidden_dim),
            nn.LayerNorm(hidden_dim),
            nn.GELU()
        )

        # Spatial multi-head graph attention layers
        self.gat1 = GATv2Conv(
            in_channels=hidden_dim,
            out_channels=hidden_dim // num_heads,
            heads=num_heads,
            edge_dim=edge_dim,
            dropout=dropout
        )
        self.gat2 = GATv2Conv(
            in_channels=hidden_dim,
            out_channels=hidden_dim // num_heads,
            heads=num_heads,
            edge_dim=edge_dim,
            dropout=dropout
        )

        self.norm1 = nn.LayerNorm(hidden_dim)
        self.norm2 = nn.LayerNorm(hidden_dim)

        # Temporal model across lead time sequence
        self.temporal_gru = nn.GRU(
            input_size=hidden_dim,
            hidden_size=hidden_dim,
            batch_first=True
        )

        # Multitask prediction heads
        self.event_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        self.severity_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 1),
            nn.Sigmoid()
        )
        self.type_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, num_classes) # Cyclone, Heatwave, Coldwave
        )
        self.centroid_delta_head = nn.Sequential(
            nn.Linear(hidden_dim, 64),
            nn.ReLU(),
            nn.Linear(64, 2) # [delta_lat, delta_lon] in degrees
        )

    def forward(
        self,
        x_seq: torch.Tensor,
        edge_index: torch.Tensor,
        edge_attr: torch.Tensor
    ) -> Dict[str, torch.Tensor]:
        """
        x_seq: [Time_Steps, Num_Nodes, In_Channels]
        edge_index: [2, Num_Edges]
        edge_attr: [Num_Edges, Edge_Dim]
        """
        timesteps, num_nodes, _ = x_seq.shape
        node_embeddings = []

        # 1. Spatial Message Passing per timestep
        for t in range(timesteps):
            x_t = self.input_proj(x_seq[t])
            # Residual GAT block 1
            h1 = self.gat1(x_t, edge_index, edge_attr)
            x_t = self.norm1(x_t + h1)
            # Residual GAT block 2
            h2 = self.gat2(x_t, edge_index, edge_attr)
            x_t = self.norm2(x_t + h2)
            node_embeddings.append(x_t)

        # [Num_Nodes, Timesteps, Hidden_Dim]
        temporal_stack = torch.stack(node_embeddings, dim=1)

        # 2. Temporal Aggregation
        gru_out, _ = self.temporal_gru(temporal_stack)
        # Latent representations at final forecast horizon
        h_final = gru_out[:, -1, :] # [Num_Nodes, Hidden_Dim]

        # 3. Predict Anomaly Attributes
        p_event = self.event_head(h_final)
        severity = self.severity_head(h_final)
        event_logits = self.type_head(h_final)
        centroid_delta = self.centroid_delta_head(h_final)

        return {
            "node_event_prob": p_event,
            "node_severity": severity,
            "event_type_logits": event_logits,
            "centroid_delta": centroid_delta,
            "temporal_features": gru_out
        }
