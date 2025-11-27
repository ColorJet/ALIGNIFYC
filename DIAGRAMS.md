# Alinify System Diagrams

## System Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                          ALINIFY REGISTRATION SYSTEM                         │
└─────────────────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────────────────┐
│                              HARDWARE LAYER                                  │
├─────────────────────────┬────────────────────────┬──────────────────────────┤
│  4K Line Scan Camera    │   CameraLink Frame     │   Print Head             │
│  @ 10 kHz               │   Grabber (Gidel)      │   (via DLL)              │
│  42mm FOV               │   GenTL Producer       │                          │
└───────┬─────────────────┴───────┬────────────────┴───────┬──────────────────┘
        │                         │                        ▲
        │ Raw lines (4096x1)      │                        │ RGB Image
        ▼                         │                        │
┌────────────────────────────────────────────────────────────────────────────┐
│                           ACQUISITION LAYER (C++)                           │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  GidelCamera Module                                                   │  │
│  │  • Multi-buffer management (30 buffers x 20MB)                       │  │
│  │  • Hardware trigger control (auto/external/encoder)                  │  │
│  │  • Asynchronous callback processing                                  │  │
│  │  • Statistics tracking (FPS, drops)                                  │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │ ScanStrip queue
                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          STITCHING LAYER (C++)                              │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  StripStitcher Module                                                 │  │
│  │  • Bidirectional support (L→R, R→L)                                  │  │
│  │  • Phase correlation alignment (sub-pixel)                           │  │
│  │  • 100px overlap blending                                            │  │
│  │  • Mechanical error compensation                                     │  │
│  │  • Quality validation (correlation > 0.7)                            │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │ Stitched grayscale image (4096 x N)
                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                        PREPROCESSING LAYER (C++/ITK)                        │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ImageProcessor Module                                                │  │
│  │  • Gaussian/Bilateral/Median filtering                               │  │
│  │  • Histogram equalization/matching                                   │  │
│  │  • Normalization (0-255)                                             │  │
│  │  • Unsharp masking                                                   │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │ Preprocessed image
                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                      REGISTRATION LAYER (C++/Elastix)                       │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  ElastixWrapper Module                                                │  │
│  │  • Multi-resolution pyramid (5 levels)                               │  │
│  │  • B-spline transformation (grid spacing: 50mm)                      │  │
│  │  • Multiple optimizers (LBFGS, SGD, Adam)                           │  │
│  │  • Multiple metrics (MI, NCC, MSE)                                   │  │
│  │  • Deformation field output                                          │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │ Deformation field (dx, dy)
                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                       GPU WARPING LAYER (C++/CUDA)                          │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  CudaWarper Module                                                    │  │
│  │  • LibTorch CUDA implementation                                      │  │
│  │  • Memory-efficient tiling (4096x4096 tiles)                         │  │
│  │  • Handles 1000+ megapixel images                                    │  │
│  │  • Bilinear/bicubic interpolation                                    │  │
│  │  • RTX 5090 optimization                                             │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │ Warped RGB image (1000MP)
                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                         PRINTER LAYER (C++/DLL)                             │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  PrinterInterface Module                                              │  │
│  │  • DLL abstraction layer                                             │  │
│  │  • TCP/UDP communication                                             │  │
│  │  • Format conversion (RGB/CMYK)                                      │  │
│  │  • Buffer management                                                 │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘

┌────────────────────────────────────────────────────────────────────────────┐
│                       PYTHON INTEGRATION LAYER                              │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  pybind11 Bindings                                                    │  │
│  │  • Zero-overhead C++ → Python bridge                                 │  │
│  │  • NumPy array integration                                           │  │
│  │  • All module APIs exposed                                           │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Pipeline API                                                         │  │
│  │  • High-level orchestration                                          │  │
│  │  • YAML configuration loading                                        │  │
│  │  • Simplified interface for GUI                                      │  │
│  └────────────────────┬─────────────────────────────────────────────────┘  │
└───────────────────────┼────────────────────────────────────────────────────┘
                        │
                        ▼
┌────────────────────────────────────────────────────────────────────────────┐
│                          GUI LAYER (Python/Qt)                              │
├────────────────────────────────────────────────────────────────────────────┤
│  ┌──────────────────────────────────────────────────────────────────────┐  │
│  │  Main Window (PySide6)                                                │  │
│  │  ├─ Image Viewers (Camera, Design, Registered, Comparison)           │  │
│  │  ├─ Deformation Field Visualizer                                     │  │
│  │  ├─ Control Point Editor (manual B-spline correction)                │  │
│  │  ├─ Parameter Controls (pyramid, optimizer, metric)                  │  │
│  │  ├─ Performance Monitor (FPS, latency, memory)                       │  │
│  │  └─ Log Viewer                                                        │  │
│  └──────────────────────────────────────────────────────────────────────┘  │
└────────────────────────────────────────────────────────────────────────────┘
```

## Data Flow Timing Diagram

```
Time (ms)   0────100──200──300──400──500──600──700──800──900──1000
            │
Camera      ████████████████████████████████████████████████████████
10kHz       │ Continuous acquisition @ 10,000 lines/sec
            │
Stitching   │    ██         ██         ██         ██
            │    └─ <10ms per strip
            │
Registration│                           ████████████████
            │                           └─ ~500ms (every 10 strips)
            │
GPU Warp    │                                         ███████
            │                                         └─ ~200ms
            │
Printer     │                                                 ████
            │                                                 └─ Send
            │
Total       ╞═════════════════════════════════════════════════════╡
Latency     │                    < 1 second                       │
```

## Memory Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                         SYSTEM MEMORY (64-128 GB)                │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ Camera Buffers     │  │ Stitched Image     │                │
│  │ 30 x 20MB = 600MB  │  │ ~500MB (max)       │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ Design Image       │  │ Working Buffers    │                │
│  │ 1000MP x 3 = 3GB   │  │ ~2GB               │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ ITK/Elastix Working Memory                              │   │
│  │ ~10GB (pyramid levels, transforms)                      │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│                         GPU MEMORY (16 GB)                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ Input Tile         │  │ Deformation Grid   │                │
│  │ 4096x4096x3 = 48MB │  │ 4096x4096x2 = 32MB │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌────────────────────┐  ┌────────────────────┐                │
│  │ Output Tile        │  │ Intermediate       │                │
│  │ 48MB               │  │ Buffers = 100MB    │                │
│  └────────────────────┘  └────────────────────┘                │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ LibTorch CUDA Runtime                                   │   │
│  │ ~2GB (kernels, streams, pools)                          │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐   │
│  │ Free for batch processing                               │   │
│  │ ~13GB available                                         │   │
│  └─────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
```

## Threading Model

```
┌──────────────────────────────────────────────────────────────────┐
│                          MAIN THREAD                              │
│  • Initialization                                                │
│  • Configuration loading                                         │
│  • Module setup                                                  │
└───────────────────────────┬──────────────────────────────────────┘
                            │
                            ├─────────────────────────────────────┐
                            │                                     │
┌───────────────────────────▼─── ┐         ┌──────────────────────▼ ───┐
│      CAMERA CALLBACK THREAD    │         │    PROCESSING THREAD      │
│  • Triggered by frame grabber  │         │  • Dequeues scan strips   │
│  • Minimal processing          │         │  • Stitching              │
│  • Queue scan strip            │         │  • Preprocessing          │
│  • Re-queue buffer             │───── ──▶│  • Registration           │
└────────────────────────────────┘         │  • GPU warping            │
                                           │  • Printer submission     │
                                           └───────────────────────────┘
                                                        │
                            ┌───────────────────────────┴───┐
                            │                               │
            ┌───────────────▼─────────┐     ┌──────────────▼──────────┐
            │   GUI UPDATE THREAD     │     │   CUDA STREAMS          │
            │  • 30 FPS display       │     │  • 4 async streams      │
            │  • User interactions    │     │  • Parallel tile proc   │
            │  • Performance metrics  │     │  • Non-blocking copy    │
            └─────────────────────────┘     └─────────────────────────┘
```

## Configuration Flow

```
system_config.yaml
        │
        ├─► camera:
        │   └─► CameraConfig (C++)
        │       └─► GidelCamera::initialize()
        │
        ├─► scanning:
        │   └─► ScanningParams (C++)
        │       └─► StripStitcher::initialize()
        │
        ├─► preprocessing:
        │   └─► PreprocessingConfig (C++)
        │       └─► ImageProcessor::applyPipeline()
        │
        ├─► registration:
        │   └─► RegistrationParams (C++)
        │       └─► ElastixWrapper::initialize()
        │
        ├─► gpu_warp:
        │   └─► GPUConfig (C++)
        │       └─► CudaWarper::initialize()
        │
        ├─► printer:
        │   └─► PrinterConfig (C++)
        │       └─► PrinterInterface::initialize()
        │
        └─► gui:
            └─► GUI configuration
                └─► Main window initialization
```

## Error Handling Flow

```
                    ┌──────────────────┐
                    │  Operation Start │
                    └────────┬─────────┘
                             │
                    ┌────────▼─────────┐
                    │  Try Operation   │
                    └────────┬─────────┘
                             │
                   ┌─────────▼──────────┐
                   │   Success?         │
                   └─┬───────────────┬──┘
                     │ Yes           │ No
         ┌───────────▼──┐       ┌───▼────────────────┐
         │ Return       │       │ Log Error          │
         │ StatusCode   │       │ (logger.h)         │
         │ ::SUCCESS    │       └───┬────────────────┘
         └──────────────┘           │
                                ┌───▼────────────────┐
                                │ Set error message  │
                                │ in result struct   │
                                └───┬────────────────┘
                                    │
                                ┌───▼────────────────┐
                                │ Call error         │
                                │ callback if set    │
                                └───┬────────────────┘
                                    │
                                ┌───▼────────────────┐
                                │ Return             │
                                │ StatusCode::ERROR  │
                                └────────────────────┘
```

## GUI Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ Alinify - Line Scan Registration System                              │
├──────────────────────────────────────────────────────────────────────┤
│ [Load Camera] [Load Design] │ [Start Camera] [Stop] │ [Register]     │
├─────────────────────────────┴───────────────────────┴────────────── ─┤
│                              │                                       
│  ┌──────────────────────┐    │  ┌──────────────────────────────┐   │
│  │ Image Tabs:          │    │  │ Control Tabs:                │   │
│  ├──────────────────────┤    │  ├──────────────────────────────┤   │
│  │ [Camera]             │    │  │ [Registration]               │   │
│  │ [Design]             │    │  │  • Pyramid Levels: [5]       │   │
│  │ [Registered]         │    │  │  • Grid Spacing: [50]        │   │
│  │ [Comparison]         │    │  │  • Optimizer: [LBFGS ▼]      │   │
│  │ [Deformation Field]  │    │  │  • Metric: [MI ▼]            │   │
│  ├──────────────────────┤    │  │                              │   │
│  │                      │    │  │ [Manual Correction]          │   │
│  │   Image Display      │    │  │  • Control Points Table      │   │
│  │   (1400 x 800)       │    │  │  • [Add] [Remove] [Clear]    │   │
│  │                      │    │  │                              │   │
│  │                      │    │  │ [Performance]                │   │
│  │                      │    │  │  • FPS: 9,987                │   │
│  │                      │    │  │  • Latency: 823 ms           │   │
│  │                      │    │  │  • CPU: 45%  RAM: 28 GB      │   │
│  │                      │    │  │  • GPU: 78%  VRAM: 12 GB     │   │
│  │                      │    │  │                              │   │
│  │                      │    │  │ [Log]                        │   │
│  │                      │    │  │  [12:34:56] Registration...  │   │
│  │                      │    │  │  [12:35:02] Warping...       │   │
│  └──────────────────────┘    │  └──────────────────────────────┘   │
│                              │                                       │
├──────────────────────────────┴───────────────────────────────────────┤
│ Status: Ready │ Camera: Acquiring │ Last registration: 487ms        │
└──────────────────────────────────────────────────────────────────────┘
```

## Module Dependencies Graph

```
                        ┌──────────┐
                        │  Types   │
                        │  Logger  │
                        └────┬─────┘
                             │
            ┌────────────────┼────────────────┐
            │                │                │
      ┌─────▼─────┐    ┌─────▼─────┐   ┌─────▼─────┐
      │  Camera   │    │ Stitching │   │Preprocess │
      │  (Gidel)  │    │ (OpenCV)  │   │(ITK/OpenCV)│
      └─────┬─────┘    └─────┬─────┘   └─────┬─────┘
            │                │                │
            └────────┬───────┴────────┬───────┘
                     │                │
               ┌─────▼─────┐    ┌─────▼─────┐
               │Registration│   │  Printer  │
               │ (Elastix) │    │   (DLL)   │
               └─────┬─────┘    └───────────┘
                     │
               ┌─────▼─────┐
               │ GPU Warp  │
               │ (LibTorch)│
               └─────┬─────┘
                     │
            ┌────────┴────────┐
            │                 │
      ┌─────▼─────┐     ┌─────▼─────┐
      │  Python   │     │    GUI    │
      │ Bindings  │────▶│ (PySide6) │
      │(pybind11) │     │           │
      └───────────┘     └───────────┘
```

---

*These diagrams provide visual representation of the Alinify system architecture, data flow, memory layout, and component interactions.*
