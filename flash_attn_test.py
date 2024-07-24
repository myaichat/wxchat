import torch

def has_flash_attention():
    try:
        # Checking if the Flash Attention module is available
        from torch.nn import functional as F
        if hasattr(F, 'scaled_dot_product_attention'):
            return True
        else:
            return False
    except ImportError:
        return False

if __name__ == "__main__":
    if has_flash_attention():
        print("Flash Attention is available in your PyTorch installation.")
    else:
        print("Flash Attention is NOT available in your PyTorch installation.")
