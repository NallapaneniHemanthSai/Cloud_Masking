"""Baseline U-Net segmentation architecture (Milestone 6; refactored to shared blocks in M10).

A clean, configurable U-Net with separated **encoder / decoder / head** modules. Configurable input
channels, output classes, encoder depth, base channels, activation, and normalization. Building blocks are
shared via :mod:`app.models.blocks` (no duplication with the Attention U-Net). PyTorch is guarded — importing
this module never requires torch; building a model does. No training/optimisation/loss code.
"""

from __future__ import annotations

from app.core.exceptions import ModelError
from app.models._torch import TORCH_AVAILABLE, nn, require_torch
from app.models.base import BaseSegmentationModel
from app.models.config import ModelConfig

if TORCH_AVAILABLE:

    from app.models.blocks import ConvBlock, Encoder, SegmentationHead, cat

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
            return self.block(cat(x, skip))

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
