# Copyright (c) Meta Platforms, Inc. and affiliates.
# All rights reserved.
#
# This source code is licensed under the BSD-style license found in the
# LICENSE file in the root directory of this source tree.

# pyre-ignore-all-errors[16]: Undefined attribute of metric states.

import warnings
from typing import Iterable, Optional, TypeVar

import torch

try:
    from skimage.metrics import structural_similarity

    _SKIMAGE_AVAILABLE = True
except ImportError:
    _SKIMAGE_AVAILABLE = False

from torcheval.metrics.metric import Metric


TStructuralSimilarity = TypeVar("TStructuralSimilarity")


def _validate_skimage_available() -> None:
    if not _SKIMAGE_AVAILABLE:
        raise RuntimeError(
            "scikit-image is required. Please make sure ``scikit-image`` is installed."
        )


class StructuralSimilarity(Metric[torch.Tensor]):
    """
    Compute the structural similarity index (SSIM) between two sets of images.

    Args:
    device (torch.device): The device where the computations will be performed.
        If None, the default device will be used.
    """

    def __init__(
        self: TStructuralSimilarity,
        device: Optional[torch.device] = None,
    ) -> None:
        _validate_skimage_available()

        super().__init__(device=device)

        self._add_state("mssim_sum", torch.tensor(0, device=device, dtype=torch.float))
        self._add_state("num_images", torch.tensor(0, device=device, dtype=torch.long))

    @torch.inference_mode()
    # pyre-ignore[14]: `update` overrides method defined in `Metric` inconsistently.
    def update(
        self: TStructuralSimilarity,
        images_1: torch.Tensor,
        images_2: torch.Tensor,
    ) -> TStructuralSimilarity:
        """
        Update the metric state with new input.
        Ensure that the two sets of images have the same value range (ex. [-1, 1], [0, 1]).

        Args:
            images_1 (Tensor): A batch of the first set of images of shape [N, C, H, W].
            images_2 (Tensor): A batch of the second set of images of shape [N, C, H, W].

        """
        if images_1.shape != images_2.shape:
            raise RuntimeError("The two sets of images must have the same shape.")

        batch_size = images_1.shape[0]

        for idx in range(batch_size):
            mssim = structural_similarity(
                images_1[idx].permute(1, 2, 0).detach().cpu().numpy(),
                images_2[idx].permute(1, 2, 0).detach().cpu().numpy(),
                multichannel=True,
            )
            self.mssim_sum += mssim

        self.num_images += batch_size

        return self

    @torch.inference_mode()
    def compute(self: TStructuralSimilarity) -> torch.Tensor:
        """
        Compute the mean of the mssim across all comparisons.

        Returns:
            tensor: computed metric.
        """

        if self.num_images == 0:
            warnings.warn(
                "The number of images must be greater than 0.",
                RuntimeWarning,
                stacklevel=2,
            )

        mssim_mean = self.mssim_sum / self.num_images

        return mssim_mean

    @torch.inference_mode()
    def merge_state(
        self: TStructuralSimilarity, metrics: Iterable[TStructuralSimilarity]
    ) -> TStructuralSimilarity:
        """
        Merge the metric state with its counterparts from other metric instances.

        Args:
            metrics (Iterable[Metric]): metric instances whose states are to be merged.
        """
        for metric in metrics:
            self.mssim_sum += metric.mssim_sum.to(self.device)
            self.num_images += metric.num_images.to(self.device)

        return self
