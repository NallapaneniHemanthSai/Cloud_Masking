"""Baseline U-Net segmentation architecture (Milestone 6).

A clean, configurable U-Net with separated **encoder / decoder / head** modules and clean boundaries.
Configurable input channels, output classes, encoder depth, base channels, activation, and normalization.
PyTorch is guarded — importing this module never requires torch; building a model does (with a clear
error otherwise). No training/optimisation/loss code.
"""

from __future__ import annotations

from app.core.exceptions import ModelError
from app.models._torch import TORCH_AVAILABLE, nn, require_torch
from app.models.base import BaseSegmentationModel
from app.models.config import Activation, ModelConfig, Normalization

if TORCH_AVAILABLE:

    def _activation(name: str):
        return {
            Activation.RELU.value: lambda: nn.ReLU(inplace=True),
            Activation.LEAKY_RELU.value: lambda: nn.LeakyReLU(0.01, inplace=True),
            Activation.GELU.value: nn.GELU,
            Activation.ELU.value: lambda: nn.ELU(inplace=True),
        }[name]()

    def _normalization(name: str, channels: int, groups: int):
        if name == Normalization.BATCH.value:
            return nn.BatchNorm2d(channels)
        if name == Normalization.GROUP.value:
            return nn.GroupNorm(min(groups, channels), channels)
        if name == Normalization.INSTANCE.value:
            return nn.InstanceNorm2d(channels)
        return nn.Identity()

    class ConvBlock(nn.Module):
        """Two (conv → norm → activation) layers, with optional dropout."""

        def __init__(self, in_ch: int, out_ch: int, config: ModelConfig) -> None:
            super().__init__()
            layers = [
                nn.Conv2d(in_ch, out_ch, kernel_size=3, padding=1, bias=False),
                _normalization(config.normalization, out_ch, config.group_norm_groups),
                _activation(config.activation),
                nn.Conv2d(out_ch, out_ch, kernel_size=3, padding=1, bias=False),
                _normalization(config.normalization, out_ch, config.group_norm_groups),
                _activation(config.activation),
            ]
            if config.dropout > 0:
                layers.append(nn.Dropout2d(config.dropout))
            self.block = nn.Sequential(*layers)

        def forward(self, x):
            return self.block(x)

    class Encoder(nn.Module):
        """Stem + downsampling stages; returns bottleneck and skip features."""

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
            return skips[-1], skips[:-1]  # bottleneck, skip features (shallow -> deep)

    class DecoderStage(nn.Module):
        """Up-conv, concatenate the matching skip, then a conv block."""

        def __init__(self, in_ch: int, out_ch: int, config: ModelConfig) -> None:
            super().__init__()
            self.up = nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2)
            self.block = ConvBlock(out_ch * 2, out_ch, config)

        def forward(self, x, skip):
            x = self.up(x)
            if x.shape[-2:] != skip.shape[-2:]:  # guard against odd input sizes
                x = nn.functional.interpolate(x, size=skip.shape[-2:], mode="nearest")
            return self.block(_cat(x, skip))

    class SegmentationHead(nn.Module):
        """1x1 convolution mapping features to class logits."""

        def __init__(self, in_ch: int, num_classes: int) -> None:
            super().__init__()
            self.head = nn.Conv2d(in_ch, num_classes, kernel_size=1)

        def forward(self, x):
            return self.head(x)

    def _cat(x, skip):
        import torch  # local import; torch guaranteed available here
        return torch.cat([x, skip], dim=1)

    class UNet(BaseSegmentationModel):
        """Baseline U-Net: encoder → decoder → head. Output is per-class logits (B, C, H, W)."""

        architecture_name = "unet"

        def __init__(self, config: ModelConfig) -> None:
            super().__init__(config)
            full = config.encoder_channels() + [config.bottleneck_channels()]
            self.encoder = Encoder(config)
            self.decoder = nn.ModuleList(
                DecoderStage(full[config.encoder_depth - i], full[config.encoder_depth - i - 1], config)
                for i in range(config.encoder_depth)
            )
            self.head = SegmentationHead(full[0], config.num_classes)

        def forward(self, x):
            bottleneck, skips = self.encoder(x)
            x = bottleneck
            for stage, skip in zip(self.decoder, reversed(skips)):
                x = stage(x, skip)
            return self.head(x)

    def build_unet(config: ModelConfig) -> UNet:
        """Construct a baseline U-Net from a :class:`ModelConfig`."""
        if config.name != "unet":
            raise ModelError(f"build_unet received config.name={config.name!r}; expected 'unet'.")
        return UNet(config)

else:  # pragma: no cover - exercised only without torch

    UNet = None  # type: ignore[assignment]

    def build_unet(config: ModelConfig):  # type: ignore[misc]
        require_torch()
