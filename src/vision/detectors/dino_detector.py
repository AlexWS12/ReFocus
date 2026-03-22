"""Grounding DINO zero-shot phone detector.

Wraps IDEA-Research/grounding-dino-tiny from HuggingFace Transformers.
The model is downloaded and initialised on the first call to detect() or
when the ``available`` property is accessed — subsequent calls reuse the
cached weights.

Typical latency:
    ~80–200 ms on CUDA GPU
    ~300–800 ms on CPU
"""

import cv2
import numpy as np

_MODEL_ID = "IDEA-Research/grounding-dino-tiny"
_PHONE_PROMPT = "cell phone."  # Grounding DINO expects a period-terminated noun phrase


class DinoDetector:
    """Lazy-loading Grounding DINO detector for phone detection.

    Usage::

        dino = DinoDetector()
        if dino.available:          # triggers model download on first call
            boxes = dino.detect(bgr_frame, conf_threshold=0.25)
            # boxes → [(x1, y1, x2, y2, score), ...]
    """

    def __init__(self) -> None:
        self._processor = None
        self._model = None
        self._device: str = "cpu"
        self._available: bool | None = None  # None = not yet attempted; False = failed; True = ready

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _load(self) -> bool:
        """Download / initialise model weights exactly once per process."""
        # Guard so repeated calls never re-attempt a failed or completed load.
        if self._available is not None:
            return self._available
        try:
            import torch
            from transformers import AutoProcessor, AutoModelForZeroShotObjectDetection

            # DINO is a transformer and runs too slowly on CPU for real-time use,
            # so we intentionally disable it unless a CUDA GPU is present.
            if not torch.cuda.is_available():
                raise RuntimeError("No CUDA device — DINO is disabled on CPU to keep the app lightweight.")

            self._device = "cuda"
            self._processor = AutoProcessor.from_pretrained(_MODEL_ID)
            self._model = (
                AutoModelForZeroShotObjectDetection.from_pretrained(_MODEL_ID)
                .to(self._device)
                .eval()  # Disable dropout / batch-norm training mode for deterministic inference.
            )
            self._available = True
            print(f"[DinoDetector] Loaded {_MODEL_ID} on {self._device}")
        except Exception as exc:  # noqa: BLE001
            print(f"[DinoDetector] Could not load model: {exc}")
            self._available = False
        return bool(self._available)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    @property
    def available(self) -> bool:
        """True once the model has loaded successfully."""
        return self._load()

    def detect(self, frame_bgr: np.ndarray, conf_threshold: float = 0.25) -> list:
        """Detect phones in a BGR frame.

        Args:
            frame_bgr: OpenCV BGR image as a NumPy array.
            conf_threshold: Minimum score for a box to be returned.

        Returns:
            List of ``(x1, y1, x2, y2, score)`` tuples (ints / float).
            Returns an empty list if the model is unavailable or inference fails.
        """
        if not self._load():
            return []
        try:
            import torch
            from PIL import Image

            # OpenCV uses BGR; PIL and the HuggingFace processor expect RGB.
            image = Image.fromarray(cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB))
            h, w = frame_bgr.shape[:2]

            inputs = self._processor(
                images=image,
                text=_PHONE_PROMPT,
                return_tensors="pt",  # Return PyTorch tensors, not numpy arrays.
            ).to(self._device)

            with torch.no_grad():  # No gradient tracking needed; saves memory and speeds up inference.
                outputs = self._model(**inputs)

            # Convert raw model logits into pixel-space bounding boxes filtered by both
            # visual and text confidence scores. Using the same value for both thresholds
            # keeps the two gates consistent (if the visual score passes, the text must too).
            results = self._processor.post_process_grounded_object_detection(
                outputs,
                inputs.input_ids,
                box_threshold=conf_threshold,   # Minimum visual grounding score to keep a box.
                text_threshold=conf_threshold,   # Minimum text-alignment score to keep a box.
                target_sizes=[(h, w)],           # Rescale normalised DINO boxes back to pixel coords.
            )

            out = []
            for score, box in zip(results[0]["scores"], results[0]["boxes"]):
                x1, y1, x2, y2 = box.tolist()
                # Clamp to frame boundaries so callers never receive out-of-bounds coordinates.
                out.append((
                    max(0, int(x1)), max(0, int(y1)),
                    min(w, int(x2)), min(h, int(y2)),
                    float(score),
                ))
            return out
        except Exception as exc:  # noqa: BLE001
            print(f"[DinoDetector] Inference error: {exc}")
            return []
