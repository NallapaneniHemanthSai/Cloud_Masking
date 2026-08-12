"""Shared segmentation building blocks (Milestone 10 refactor).

Common, torch-guarded building blocks reused by the U-Net (M6) and the improved Attention U-Net (M10),
so model infrastructure is **not duplicated**. Importing this module never requires torch. No
training/optimisation/loss code.
"""

from __future__ import annotations

from app.models._torch import TORCH_AVAILABLE, nn
from app.models.config import Activation, ModelConfig, Normalization

if TORCH_AVAILABLE:

    def activation(name: str):
        """Return a fresh activation module for the configured name."""
        return {
            Activation.RELU.value: lambda: nn.ReLU(inplace=True),
            Activation.LEAKY_RELU.value: lambda: nn.LeakyReLU(0.01, inplace=True),
            Activation.GELU.value: nn.GELU,
            Activation.ELU.value: lambda: nn.ELU(inplace=True),
        }[name]()

    def normalization(name: str, channels: int, groups: int):
        """Return a normalization module for the configured name."""
        if name == Normalization.BATCH.value:
            return nn.BatchNorm2d(channels)
        if name == Normalization.GROUP.value:
            return nn.GroupNorm(min(groups, channels), channels)
        if name == Normalization.INSTANCE.value:
            return nn.InstanceNorm2d(channels)
        return nn.Identity()

    def cat(x, skip):
        """Concatenate two feature maps along the channel dimension."""
        import torch  # local import; torch guaranteed available here
        return torch.cat([x, skip], dim=1)

    class ConvBlock(nn.Module):
        """Two (conv → norm → activation) layers, with optional dropout."""

        def __init__(self, in_ch: int, out_ch: int, config: ModelConfig) -> None:
            super().__init__()
            layers = [
                nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
                normalization(config.normalization, out_ch, config.group_norm_groups),
                activation(config.activation),
                nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
                normalization(config.normalization, out_ch, config.group_norm_groups),
                activation(config.activation),
            ]
            if config.dropout > 0:
                layers.append(nn.Dropout2d(config.dropout))
            self.block = nn.Sequential(*layers)

        def forward(self, x):
            return self.block(x)

    class Encoder(nn.Module):
        """Stem + downsampling stages; returns bottleneck and skip features (shallow → deep)."""

        def __init__(self, config: ModelConfig) -> None:
            super().__init__()
            full = config.encoder_channels() + [config.bottleneck_channels()]
            self.stem = ConvBlock(config.in_channels, full[0], config)
            self.pool = nn.MaxPool2d(2)
            self.stages = nn.ModuleList(
                ConvBlock(full[i], full[i + 1], config) for i in range(config.encoder_depth)
            )

        def forward(self, x):
            skips = [self.stem(x)]
            for stage in self.stages:
                skips.append(stage(self.pool(skips[-1])))
            return skips[-1], skips[:-1]

    class SegmentationHead(nn.Module):
        """1x1 convolution mapping features to per-class logits."""

        def __init__(self, in_ch: int, num_classes: int) -> None:
            super().__init__()
            self.head = nn.Conv2d(in_ch, num_classes, kernel_size=1)

        def forward(self, x):
            return self.head(x)
