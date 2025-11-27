import numpy as np
import sys
from pathlib import Path

# Ensure project python modules are importable when running from repo root
PROJECT_ROOT = Path(__file__).resolve().parents[1]
PYTHON_DIR = PROJECT_ROOT / "python"
sys.path.insert(0, str(PYTHON_DIR))

from registration_backend import RegistrationBackend  # noqa: E402

METHODS = [
    "clahe",
    "histogram_eq",
    "edge_enhance",
    "normalize",
    "bilateral",
    "combo",
    "emboss_gradient",
    "texture_enhance",
    "gabor",
    "frangi",
    "structure_tensor",
]


def main() -> None:
    rb = RegistrationBackend.__new__(RegistrationBackend)
    # Ensure attributes expected by cleanup routines exist
    rb.temp_dir = None
    rb.moving_rgb_path = None
    rb.fixed_path = None
    rb.moving_path = None
    img = (np.random.rand(128, 128) * 255).astype("uint8")
    for method in METHODS:
        out = RegistrationBackend.preprocess_image(rb, img, method=method)
        assert out.shape == img.shape, method
        assert out.dtype == np.uint8, method
    print(f"preprocess smoke test OK for {len(METHODS)} methods")


if __name__ == "__main__":
    main()
