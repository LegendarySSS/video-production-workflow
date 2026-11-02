import hashlib
import json
import os
import tempfile
import time
from datetime import datetime, timezone
from pathlib import Path

from .config import VideoError, redact
from .providers import Provider, build_request, require, validate_task_id
from .transport import APIError


TERMINAL = {"succeeded", "failed", "cancelled", "expired", "rejected"}


def now():
    return datetime.now(timezone.utc).isoformat()


def read_json(path):
    try:
        with Path(path).open(encoding="utf-8") as source:
            value = json.load(source)
    except (ValueError, OSError) as error:
        raise VideoError("JSON 文件无法读取或格式错误") from error
    require(isinstance(value, dict), "JSON 顶层必须是对象")
    return value


def save_record(directory, record):
    directory = Path(directory)
    descriptor, name = tempfile.mkstemp(prefix=".task-", suffix=".tmp", dir=directory)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as output:
            json.dump(record, output, ensure_ascii=False, indent=2)
            output.write("\n")
            output.flush()
            os.fsync(output.fileno())
        os.replace(name, directory / "task.json")
    finally:
        Path(name).unlink(missing_ok=True)


def load_record(directory):
    record = read_json(Path(directory) / "task.json")
    require(record.get("provider") in ("kling", "seedance", "runway"), "任务记录供应商不正确")
    if record.get("task_id"):
        validate_task_id(record["task_id"])
    return record


def submit(spec, directory, keys, transport):
    plan = build_request(spec)
    provider = Provider(plan["provider"], keys, transport)
    directory = Path(directory)
    try:
        directory.mkdir(parents=True, exist_ok=False, mode=0o700)
    except FileExistsError as error:
        raise VideoError("任务目录已存在；先查询原任务。新的付费尝试必须使用新目录") from error
    record = {
        "schema_version": "0.2.0", "provider": plan["provider"], "model": plan["model"],
        "spec": spec, "request_sha256": hashlib.sha256(
            json.dumps(plan["body"], ensure_ascii=False, sort_keys=True).encode("utf-8")
        ).hexdigest(), "status": "submitting", "task_id": None, "outputs": [],
        "created_at": now(), "updated_at": now(), "notes": plan["notes"],
        "quality_review": "pending", "cost": None,
    }
    save_record(directory, record)
    try:
        record["task_id"] = provider.create(plan)
        record["status"] = "queued"
    except VideoError as error:
        record["status"] = "rejected" if isinstance(error, APIError) and not error.ambiguous else "submission_unknown"
        record["last_error"] = redact(str(error), keys)
        record["updated_at"] = now()
        save_record(directory, record)
        raise VideoError(record["last_error"] + " 已保存任务记录；不要自动重提。") from error
    record["updated_at"] = now()
    save_record(directory, record)
    return record


def attach(directory, task_id):
    record = load_record(directory)
    require(not record.get("task_id"), "任务记录已有 ID，拒绝替换")
    require(record.get("status") in ("submitting", "submission_unknown"), "仅能关联提交状态不明的任务")
    record.update(task_id=validate_task_id(task_id), status="queued", updated_at=now())
    save_record(directory, record)
    return record


def refresh(directory, keys, transport):
    record = load_record(directory)
    require(bool(record.get("task_id")), "记录中无任务 ID；请先到控制台核对，必要时用 attach 关联")
    provider = Provider(record["provider"], keys, transport)
    update = provider.status(record["task_id"])
    if update.get("error"):
        update["error"] = redact(json.dumps(update["error"], ensure_ascii=False), keys)[:1500]
    record.update(update, updated_at=now())
    save_record(directory, record)
    return record


def wait(directory, keys, transport, timeout, interval):
    require(timeout > 0 and 5 <= interval <= 60, "超时必须大于 0，轮询间隔为 5–60 秒")
    deadline = time.monotonic() + timeout
    while True:
        record = refresh(directory, keys, transport)
        if record["status"] in TERMINAL:
            return record, False
        remaining = deadline - time.monotonic()
        if remaining <= 0:
            return record, True
        time.sleep(min(interval, remaining))


def download(directory, keys, transport, destination, index, max_bytes):
    require(index >= 0 and max_bytes > 0, "index 不能为负，下载大小上限必须大于 0")
    require(not Path(destination).exists() and not Path(destination).is_symlink(), "输出文件已存在，拒绝覆盖")
    record = refresh(directory, keys, transport)
    require(record["status"] == "succeeded", "任务尚未成功，不能下载")
    require(index < len(record["outputs"]), "视频输出序号超出范围")
    path = transport.download(record["outputs"][index], destination, max_bytes)
    record.setdefault("downloads", []).append({"index": index, "path": path, "downloaded_at": now()})
    record["updated_at"] = now()
    save_record(directory, record)
    return record


def summary(record, directory):
    return {
        "provider": record["provider"], "model": record["model"],
        "task_id": record.get("task_id"), "status": record["status"],
        "record": str((Path(directory) / "task.json").resolve()),
        "output_count": len(record.get("outputs", [])), "quality_review": record.get("quality_review", "pending"),
        "error": record.get("error") or record.get("last_error"),
        "notes": record.get("notes", []), "downloads": record.get("downloads", []),
    }
