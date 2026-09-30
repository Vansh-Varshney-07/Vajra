import math
import torch
import torch.nn as nn
from typing import List

class SinusoidalTimeEmbedding(nn.Module):
    """Embeds diffusion timestep t into frequency components."""
    def __init__(self, dim: int):
        super().__init__()
        self.dim = dim

    def forward(self, time_steps: torch.Tensor) -> torch.Tensor:
        half_dim = self.dim // 2
        embeddings = math.log(10000) / (half_dim - 1)
        embeddings = torch.exp(torch.arange(half_dim, device=time_steps.device) * -embeddings)
        embeddings = time_steps[:, None].float() * embeddings[None, :]
        embeddings = torch.cat([embeddings.sin(), embeddings.cos()], dim=-1)
        return embeddings

class ResidualBlock(nn.Module):
    """Conv block with residual skip connection and time embedding injection."""
    def __init__(self, in_channels: int, out_channels: int, time_emb_dim: int):
        super().__init__()
        self.time_mlp = nn.Sequential(
            nn.SiLU(),
            nn.Linear(time_emb_dim, out_channels)
        )
        self.conv1 = nn.Conv2d(in_channels, out_channels, kernel_size=3, padding=1)
        self.norm1 = nn.GroupNorm(8, out_channels)
        self.act1 = nn.SiLU()

        self.conv2 = nn.Conv2d(out_channels, out_channels, kernel_size=3, padding=1)
        self.norm2 = nn.GroupNorm(8, out_channels)
        self.act2 = nn.SiLU()

        self.shortcut = (
            nn.Conv2d(in_channels, out_channels, kernel_size=1)
            if in_channels != out_channels
            else nn.Identity()
        )

    def forward(self, x: torch.Tensor, t_emb: torch.Tensor) -> torch.Tensor:
        h = self.act1(self.norm1(self.conv1(x)))
        h = h + self.time_mlp(t_emb)[:, :, None, None]
        h = self.act2(self.norm2(self.conv2(h)))
        return h + self.shortcut(x)

class ConditionalUNet(nn.Module):
    """
    Conditional UNet backbone for diffusion downscaling.
    Concatenates coarse 12km conditioning + DEM topography with the noisy target state.
    """

    def __init__(
        self,
        in_channels: int = 4,          # Noisy state channels (u, v, q, precip)
        out_channels: int = 4,         # Predicted noise / target state
        condition_channels: int = 8,   # Coarse 12km (4) + DEM topography (4)
        base_channels: int = 64,
        channel_mults: List[int] = [1, 2, 4],
        time_emb_dim: int = 128
    ):
        super().__init__()
        self.time_embed = nn.Sequential(
            SinusoidalTimeEmbedding(time_emb_dim),
            nn.Linear(time_emb_dim, time_emb_dim),
            nn.SiLU()
        )

        total_in = in_channels + condition_channels
        self.init_conv = nn.Conv2d(total_in, base_channels, kernel_size=3, padding=1)

        # Downsampling blocks
        self.downs = nn.ModuleList()
        curr_ch = base_channels
        for mult in channel_mults:
            out_ch = base_channels * mult
            self.downs.append(nn.ModuleList([
                ResidualBlock(curr_ch, out_ch, time_emb_dim),
                ResidualBlock(out_ch, out_ch, time_emb_dim),
                nn.Conv2d(out_ch, out_ch, kernel_size=4, stride=2, padding=1) # Downsample
            ]))
            curr_ch = out_ch

        # Mid block
        self.mid1 = ResidualBlock(curr_ch, curr_ch, time_emb_dim)
        self.mid2 = ResidualBlock(curr_ch, curr_ch, time_emb_dim)

        # Upsampling blocks
        self.ups = nn.ModuleList()
        for mult in reversed(channel_mults):
            out_ch = base_channels * mult
            self.ups.append(nn.ModuleList([
                nn.ConvTranspose2d(curr_ch, out_ch, kernel_size=4, stride=2, padding=1), # Upsample
                ResidualBlock(out_ch * 2, out_ch, time_emb_dim),
                ResidualBlock(out_ch, out_ch, time_emb_dim)
            ]))
            curr_ch = out_ch

        self.final_norm = nn.GroupNorm(8, base_channels)
        self.final_act = nn.SiLU()
        self.final_conv = nn.Conv2d(base_channels, out_channels, kernel_size=3, padding=1)

    def forward(
        self,
        x_noisy: torch.Tensor,
        timesteps: torch.Tensor,
        condition: torch.Tensor
    ) -> torch.Tensor:
        """
        x_noisy: [Batch, In_Channels, H, W]
        timesteps: [Batch]
        condition: [Batch, Condition_Channels, H, W] (upsampled coarse 12km + DEM)
        """
        t_emb = self.time_embed(timesteps)
        x = torch.cat([x_noisy, condition], dim=1)
        x = self.init_conv(x)

        skip_connections = []
        for res1, res2, down in self.downs:
            x = res1(x, t_emb)
            x = res2(x, t_emb)
            skip_connections.append(x)
            x = down(x)

        x = self.mid1(x, t_emb)
        x = self.mid2(x, t_emb)

        for up, res1, res2 in self.ups:
            x = up(x)
            skip = skip_connections.pop()
            x = torch.cat([x, skip], dim=1)
            x = res1(x, t_emb)
            x = res2(x, t_emb)

        x = self.final_act(self.final_norm(x))
        out = self.final_conv(x)
        return out
