"""
Multicore image processing utilities
Uses multiprocessing for CPU-bound operations
"""

import multiprocessing as mp
import numpy as np
from functools import partial


class MultiCoreProcessor:
    """Multicore image processing manager"""
    
    def __init__(self, n_workers=None):
        self.n_workers = n_workers or max(1, mp.cpu_count() - 1)
        self.pool = None
        print(f"✓ MultiCore processor initialized with {self.n_workers} workers")
    
    def __enter__(self):
        self.pool = mp.Pool(self.n_workers)
        return self
    
    def __exit__(self, *args):
        if self.pool:
            self.pool.close()
            self.pool.join()
    
    def process_chunks(self, image, func, chunk_size=1000):
        """Process image in parallel chunks"""
        if self.pool is None:
            self.pool = mp.Pool(self.n_workers)
        
        height, width = image.shape[:2]
        
        # Split image into chunks
        chunks = []
        chunk_indices = []
        for i in range(0, height, chunk_size):
            end_i = min(i + chunk_size, height)
            chunk = image[i:end_i]
            chunks.append(chunk)
            chunk_indices.append((i, end_i))
        
        # Process chunks in parallel
        results = self.pool.map(func, chunks)
        
        # Reassemble
        output = np.zeros_like(image)
        for (i, end_i), result in zip(chunk_indices, results):
            output[i:end_i] = result
        
        return output
    
    def parallel_resize(self, image, target_size):
        """Resize image using multiple cores"""
        import cv2
        
        def resize_chunk(chunk):
            chunk_h, orig_w = chunk.shape[:2]
            target_w, target_h = target_size
            scale_h = target_h / image.shape[0]
            chunk_target_h = int(chunk_h * scale_h)
            return cv2.resize(chunk, (target_w, chunk_target_h), interpolation=cv2.INTER_LINEAR)
        
        return self.process_chunks(image, resize_chunk)


def parallel_downsample(image, scale=0.5, n_workers=None):
    """Quick parallel image downsampling"""
    import cv2
    
    n_workers = n_workers or max(1, mp.cpu_count() - 1)
    
    height, width = image.shape[:2]
    new_height = int(height * scale)
    new_width = int(width * scale)
    
    # For small images, just use OpenCV directly
    if height < 2000:
        return cv2.resize(image, (new_width, new_height), interpolation=cv2.INTER_LINEAR)
    
    # For large images, split into horizontal chunks
    chunk_size = height // n_workers
    chunks = []
    for i in range(0, height, chunk_size):
        end = min(i + chunk_size, height)
        chunks.append(image[i:end])
    
    def resize_chunk(chunk):
        chunk_h = chunk.shape[0]
        chunk_new_h = int(chunk_h * scale)
        return cv2.resize(chunk, (new_width, chunk_new_h), interpolation=cv2.INTER_LINEAR)
    
    with mp.Pool(n_workers) as pool:
        resized_chunks = pool.map(resize_chunk, chunks)
    
    return np.vstack(resized_chunks)


if __name__ == "__main__":
    # Test multicore processing
    print(f"CPU cores available: {mp.cpu_count()}")
    print(f"Workers: {max(1, mp.cpu_count() - 1)}")
