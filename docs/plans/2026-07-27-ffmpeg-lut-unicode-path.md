# FFmpeg LUT Unicode Path Compatibility Implementation Plan

**Goal:** Ensure LUT preview and processing work on Windows systems where the bundled FFmpeg cannot open LUT files from Unicode installation paths.

**Architecture:** Keep the original packaged LUT files as the source of truth. Add one FFmpeg resource compatibility module that returns original ASCII paths unchanged and materializes only Unicode paths into a content-addressed, ASCII-safe cache with atomic copy and SHA256 verification. Both the dialog preview and batch processor must use this resolver when constructing FFmpeg filter paths, while the QImage fallback continues reading original resources.

**Tech Stack:** Python 3.10, pathlib, hashlib, tempfile, ctypes Win32 path APIs, pytest, bundled FFmpeg.

---

### Task 1: Reproduce and specify the path failure

**Files:**
- Create: `tests/test_ffmpeg_resources.py`

1. Verify an ASCII source path is returned unchanged.
2. Verify a Unicode source is copied to an ASCII cache and retains identical bytes.
3. Verify a damaged cache entry is replaced from the packaged source.
4. Run the bundled FFmpeg against a Unicode LUT path and prove the cached path succeeds.

### Task 2: Implement the compatibility boundary

**Files:**
- Create: `utils/ffmpeg_resources.py`
- Modify: `utils/lut_filters.py`

1. Calculate a content hash for Unicode-path resources.
2. Select a writable ASCII cache root, preferring the user temp directory and falling back to ProgramData.
3. Copy through a unique temporary file, verify its hash, and atomically replace the destination.
4. Expose `resolve_ffmpeg_lut_path()` without changing the existing UI/resource resolver.

### Task 3: Integrate only FFmpeg call sites

**Files:**
- Modify: `processor/batch_params_processor.py`
- Modify: `ui/lut_filter_dialog.py`

1. Use the FFmpeg-safe resolver in video preview and formal processing filter construction.
2. Use the same resolver for FFmpeg-based image preview.
3. Preserve the original resolver for QImage fallback and all non-FFmpeg consumers.

### Task 4: Verify regressions

**Files:**
- Modify: `tests/test_lut_filters.py`
- Modify: `tests/test_batch_params_processor.py`

1. Run focused LUT and resource tests.
2. Run the full pytest suite.
3. Compile all Python modules.
4. Build an installer stage and verify LUT resources remain packaged.
