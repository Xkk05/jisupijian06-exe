import os
import copy
from typing import Callable, Dict, List

from processor.batch_params_processor import BatchParamsProcessor
from ui.i18n import t
from utils.unified_logger import logger


def _ensure_unique_path(output_path: str) -> str:
    base, ext = os.path.splitext(output_path)
    counter = 1
    unique_path = output_path
    while os.path.exists(unique_path):
        unique_path = f"{base}_{counter}{ext}"
        counter += 1
    return unique_path


def _build_non_overwrite_output_path(video_path: str, output_config: Dict) -> str:
    output_dir = (output_config.get("path") or "").strip()
    base_dir = output_dir if output_dir else os.path.dirname(video_path)
    base_name = os.path.basename(video_path)
    output_path = os.path.join(base_dir, base_name)
    if os.path.abspath(output_path) == os.path.abspath(video_path) or os.path.exists(output_path):
        output_path = _ensure_unique_path(output_path)
    return output_path


def process_batch(
    video_list: List[Dict],
    config: Dict,
    progress_callback: Callable[[int, str], None],
    status_callback: Callable[[int, str], None],
    is_running_callback: Callable[[], bool],
) -> None:
    def _merge_config(base: Dict, override: Dict) -> Dict:
        merged = copy.deepcopy(base or {})
        if not override:
            return merged
        for key, value in override.items():
            if (
                isinstance(value, dict)
                and isinstance(merged.get(key), dict)
            ):
                merged[key] = _merge_config(merged[key], value)
            else:
                merged[key] = value
        return merged

    total = len(video_list)
    logger.info(f"[Batch] start total={total}")
    if total == 0:
        progress_callback(100, t("batch.progress.all_done", "全部处理完成"))
        return

    last_progress = 0
    def emit_progress(progress: int, message: str) -> None:
        nonlocal last_progress
        last_progress = progress
        progress_callback(progress, message)

    stopped = False

    for idx, video_info in enumerate(video_list):
        if not is_running_callback():
            stopped = True
            break

        video_path = video_info["path"]
        row_index = video_info.get("row_index", idx)
        status_callback(row_index, "processing")
        emit_progress(
            int((idx / total) * 100),
            t(
                "batch.progress.processing_file",
                "正在处理: {name}",
                name=os.path.basename(video_path),
            ),
        )
        logger.info(f"[Batch] processing idx={idx + 1}/{total} path={video_path}")

        try:
            video_config = _merge_config(config or {}, video_info.get("params"))
            processor = BatchParamsProcessor(copy.deepcopy(video_config))
            # 确定输出路径
            output_config = video_config.get("output", {})
            overwrite_original = False

            # 输出到新路径（默认同目录并自动追加后缀）
            output_path = _build_non_overwrite_output_path(video_path, output_config)
            video_info["output_path"] = output_path

            logger.info(
                "[Batch] output overwrite=%s output=%s",
                overwrite_original,
                output_path,
            )

            # 确保输出目录存在（非覆盖模式也需要）
            output_parent_dir = os.path.dirname(output_path)
            if not output_parent_dir:
                error_message = "输出目录无效"
                status_callback(idx, f"error:{error_message}")
                logger.error(f"[Batch] failed idx={idx + 1}/{total} error={error_message}")
                break
            os.makedirs(output_parent_dir, exist_ok=True)

            # 处理视频
            success = processor.process_video(
                video_path,
                output_path,
                variant=idx,
                progress_callback=lambda p, m: emit_progress(
                    int((idx + p / 100) / total * 100), m
                ),
                should_stop=lambda: not is_running_callback(),
            )

            if not is_running_callback():
                status_callback(row_index, "stopped")
                logger.info(f"[Batch] stopped idx={idx + 1}/{total} path={video_path}")
                stopped = True
                break

            if success:
                status_callback(row_index, "done")
                logger.info(f"[Batch] success idx={idx + 1}/{total} output={output_path}")
            else:
                status_callback(row_index, "failed")
                logger.error(f"[Batch] failed idx={idx + 1}/{total} output={output_path}")

        except Exception as e:
            logger.error(f"[Batch] exception idx={idx + 1}/{total} error={e}")
            status_callback(row_index, f"error:{str(e)}")

    if stopped:
        emit_progress(last_progress, t("batch.progress.stopped", "处理已停止"))
        logger.info("[Batch] stopped")
    else:
        emit_progress(100, t("batch.progress.all_done", "全部处理完成"))
        logger.info("[Batch] end")
