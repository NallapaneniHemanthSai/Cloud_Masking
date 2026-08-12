"""Attention U-Net — improved segmentation architecture (Milestone 10).

U-Net with **additive attention gates** on the skip connections (Oktay et al., 2018). The gate re-weights
each skip feature by relevance to the decoder's current scale — the mechanism hypothesised to help thin
cloud / bright-surface discrimination (ADR-0010). It **reuses** the shared encoder / conv block / head
(:mod:`app.models.blocks`) and the same :class:`ModelConfig` as U-Net; only the decoder differs. All ops
(conv, sigmoid, interpolate) are **CPU/MPS compatible** — no CUDA-specific operations. PyTorch is guarded.

**Performance vs U-Net is NOT claimed here — NOT YET MEASURED.** This milestone provides the architecture
and comparison infrastructure only.
"""

from __future__ import annotations

from app.core.exceptions import ModelError
from app.models._torch import TORCH_AVAILABLE, nn, require_torch
from app.models.base import BaseSegmentationModel
from app.models.config import ModelConfig

if TORCH_AVAILABLE:

    from app.models.blocks import ConvBlock, Encoder, SegmentationHead, cat

    class AttentionGate(nn.Module):
        """Additive attention gate: re-weights skip features ``x`` using the gating signal ``g``.

        Shapes: ``g`` has ``f_g`` channels (from the decoder), ``x`` has ``f_l`` channels (the skip);
        both are projected to ``f_int`` channels, combined, and reduced to a per-pixel [0,1] attention map
        that scales ``x``. Uses only conv/relu/sigmoid/interpolate (MPS-compatible).
        """

        def __init__(self, f_g: int, f_l: int, f_int: int) -> None:
            super().__init__()
            self.w_g = nn.Sequential(nn.Conv2d(f_g, f_int, kernel_size=1, bias=True),
                                     nn.BatchNorm2d(f_int))
            self.w_x = nn.Sequential(nn.Conv2d(f_l, f_int, kernel_size=1, bias=True),
                                     nn.BatchNorm2d(f_int))
            self.psi = nn.Sequential(nn.Conv2d(f_int, 1, kernel_size=1, bias=True),
                                     nn.BatchNorm2d(1), nn.Sigmoid())
            self.relu = nn.ReLU(inplace=True)

        def forward(self, g, x):
            if g.shape[-2:] != x.shape[-2:]:
                g = nn.functional.interpolate(g, size=x.shape[-2:], mode="nearest")
            attention = self.psi(self.relu(self.w_g(g) + self.w_x(x)))
            return x * attention

    class AttentionDecoderStage(nn.Module):
        """Up-conv, attention-gate the skip, concatenate, then a conv block."""

        def __init__(self, in_ch: int, out_ch: int, config: ModelConfig) -> None:
            super().__init__()
            self.up = nn.ConvTranspose2d(in_ch, out_ch, kernel_size=2, stride=2)
            self.gate = AttentionGate(f_g=out_ch, f_l=out_ch, f_int=max(out_ch // 2, 1))
            self.block = ConvBlock(out_ch * 2, out_ch, config)

        def forward(self, x, skip):
            x = self.up(x)
            if x.shape[-2:] != skip.shape[-2:]:
                x = nn.functional.interpolate(x, size=skip.shape[-2:], mode="nearest")
            attended_skip = self.gate(x, skip)
            return self.block(cat(x, attended_skip))

    class AttentionUNet(BaseSegmentationModel):
        """Attention U-Net: encoder → attention decoder → head. Output logits (B, C, H, W)."""

        architecture_name = "attention_unet"

        def __init__(self, config: ModelConfig) -> None:
            super().__init__(config)
            full = config.encoder_channels() + [config.bottleneck_channels()]
            self.encoder = Encoder(config)
            self.decoder = nn.ModuleList(
                AttentionDecoderStage(full[config.encoder_depth - i],
                                      full[config.encoder_depth - i - 1], config)
                for i in range(config.encoder_depth)
            )
            self.head = SegmentationHead(full[0], config.num_classes)

        def forward(self, x):
            bottleneck, skips = self.encoder(x)
            x = bottleneck
            for stage, skip in zip(self.decoder, reversed(skips)):
                x = stage(x, skip)
            return self.head(x)

    def build_attention_unet(config: ModelConfig) -> AttentionUNet:
        """Construct an Attention U-Net from a :class:`ModelConfig`."""
        if config.name != "attention_unet":
            raise ModelError(
                f"build_attention_unet received config.name={config.name!r}; expected 'attention_unet'.")
        return AttentionUNet(config)

else:  # pragma: no cover - exercised only without torch

    AttentionUNet = None  # type: ignore[assignment]

    def build_attention_unet(config: ModelConfig):  # type: ignore[misc]
        require_torch()
