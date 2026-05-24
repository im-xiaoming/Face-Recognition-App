from pathlib import Path

import numpy as np
import torch
from django.conf import settings
from PIL import Image
from torchvision import transforms
from xiaoying.utils import get_model, load_weight

_cache = {}


def _to_pil(item):
    if isinstance(item, Image.Image):
        return item.convert('RGB') if item.mode != 'RGB' else item
    if isinstance(item, np.ndarray):
        # Expect RGB uint8 HxWxC
        return Image.fromarray(item)
    image = Image.open(item).convert('RGB')
    image.load()
    return image


def _get_embedding_model():
    if _cache:
        return _cache['model'], _cache['transform'], _cache['device']

    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    checkpoint = Path(settings.BASE_DIR) / 'checkpoints' / 'ir_50.pth'
    if not checkpoint.exists():
        raise FileNotFoundError(
            f"Missing embedding checkpoint: {checkpoint}. "
            "Add ir_50.pth before using recognition."
        )

    transform = transforms.Compose([
        transforms.ToTensor(),
        transforms.Normalize([0.5, 0.5, 0.5], [0.5, 0.5, 0.5]),
    ])

    model = get_model('ir_50', device)
    load_weight(model, checkpoint)
    model.to(device)
    model.eval()

    _cache['model'] = model
    _cache['transform'] = transform
    _cache['device'] = device

    return model, transform, device


def inference(items):
    """Items may be file paths, PIL images, or RGB numpy arrays."""
    model, transform, device = _get_embedding_model()
    batch = torch.stack([transform(_to_pil(item)) for item in items]).to(device)

    with torch.no_grad():
        embeddings, _ = model(batch)

    return embeddings.detach().cpu()
