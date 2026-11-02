import re
from urllib.parse import quote, urlencode

from .config import PROVIDERS, VideoError, credential
from .transport import APIError, https_url


SPEC_FIELDS = {
    "provider", "model", "prompt", "duration", "aspect_ratio", "resolution", "audio",
    "image", "last_image", "reference_images", "reference_videos", "reference_audio", "seed",
}
RATIOS = {"16:9", "9:16", "1:1", "4:3", "3:4", "21:9", "adaptive"}
SEEDANCE_MODELS = {
    "doubao-seedance-2-0-260128", "doubao-seedance-2-0-fast-260128",
    "doubao-seedance-2-0-mini-260615", "doubao-seedance-2-5-260628",
}


def require(condition, message):
    if not condition:
        raise VideoError(message)


def build_request(spec):
    require(isinstance(spec, dict), "镜头 JSON 必须是对象")
    require(not set(spec) - SPEC_FIELDS, "镜头 JSON 存在不支持的字段；请对照示例，不能静默丢弃参数")
    provider = spec.get("provider")
    require(provider in PROVIDERS, "provider 必须是 kling、seedance 或 runway")
    prompt = spec.get("prompt")
    require(isinstance(prompt, str) and prompt.strip(), "prompt 不能为空")
    duration = spec.get("duration", 5)
    require(type(duration) is int, "duration 必须是整数秒数")
    ratio = spec.get("aspect_ratio", "16:9")
    require(isinstance(ratio, str) and ratio in RATIOS, "不支持的 aspect_ratio")
    resolution = spec.get("resolution", "720p")
    require(isinstance(resolution, str), "resolution 必须是字符串")
    audio = spec.get("audio")
    require(audio is None or type(audio) is bool, "audio 必须是布尔值")
    seed = spec.get("seed")
    require(seed is None or type(seed) is int and 0 <= seed <= 4294967295, "seed 必须是 0 到 4294967295 的整数")
    image = spec.get("image")
    last_image = spec.get("last_image")
    for value in (image, last_image):
        if value is not None:
            https_url(value)
    require(not last_image or image, "last_image 需要同时指定 image 首帧")
    images = spec.get("reference_images", [])
    videos = spec.get("reference_videos", [])
    audios = spec.get("reference_audio", [])
    for values in (images, videos, audios):
        require(isinstance(values, list), "reference_* 必须是 HTTPS 地址数组")
        for value in values:
            https_url(value)
    model = spec.get("model", PROVIDERS[provider]["model"])
    require(isinstance(model, str), "model 必须是字符串")
    notes = []

    if provider == "kling":
        require(model == "kling-4.0", "此适配器使用 Kling 4.0 新版接口，不能直接填写旧版模型 ID")
        require(3 <= duration <= 30, "Kling 4.0 时长为 3–30 秒")
        require(resolution in ("720p", "1080p"), "Kling 当前适配 720p 或 1080p")
        require(ratio in ("16:9", "9:16", "1:1", "21:9", "adaptive"), "Kling 不支持该画幅")
        require(not audios, "Kling 音频参考需预建 voice profile；此入口不接受原始音频 URL")
        require(seed is None, "Kling 4.0 此入口未提供 seed 参数")
        require(audio is not False, "Kling 4.0 原生音画默认开启；静音请在后期处理，不传未核实开关")
        require(len(images) + bool(image) + bool(last_image) <= 10, "Kling 最多 10 张输入图片")
        require(len(videos) <= 5, "Kling 最多 5 段参考视频，合计时长需在平台限制内")
        settings = {"duration": duration, "resolution": resolution, "aspect_ratio": ratio}
        if image or images or videos:
            contents = [{"type": "prompt", "text": prompt}]
            if image:
                contents.append({"type": "first_frame", "id": "start", "url": image})
            if last_image:
                contents.append({"type": "last_frame", "id": "end", "url": last_image})
            contents += [{"type": "refer_image", "id": f"image_{index}", "url": value}
                         for index, value in enumerate(images, 1)]
            contents += [{"type": "feature_video", "id": f"video_{index}", "url": value}
                         for index, value in enumerate(videos, 1)]
            endpoint = "/omni-video/kling-4.0"
            body = {"contents": contents, "settings": settings}
            notes.append("提示词中用 @start、@end、@image_1、@video_1 明确各素材用途；本入口走 Omni。")
        else:
            endpoint = "/text-to-video/kling-4.0"
            body = {"prompt": prompt, "settings": settings}
        notes.append("Kling 原生音画默认开启；单次生成结果仍需检查动作、对白和身份。")
    elif provider == "seedance":
        require(model in SEEDANCE_MODELS, "未支持的 Seedance Model ID，请先核对官方文档并更新适配器")
        maximum = 30 if model == "doubao-seedance-2-5-260628" else 15
        require(4 <= duration <= maximum, f"该 Seedance 模型时长为 4–{maximum} 秒")
        require(resolution in ("480p", "720p", "1080p"), "Seedance 此入口适配 480p、720p、1080p")
        if "fast" in model or "mini" in model:
            require(resolution != "1080p", "Seedance Fast/Mini 此入口最高 720p")
        require(not (image and (images or videos or audios)), "Seedance 首尾帧模式与多模态参考模式需分别提交")
        require(len(images) <= 9 and len(videos) <= 3 and len(audios) <= 3, "参考素材数量超过此入口支持上限")
        require(not audios or images or videos, "此入口的音频参考需同时提供图片或视频")
        content = [{"type": "text", "text": prompt}]
        for role, value in (("first_frame", image), ("last_frame", last_image)):
            if value:
                content.append({"type": "image_url", "image_url": {"url": value}, "role": role})
        for kind, role, values in (("image", "reference_image", images),
                                   ("video", "reference_video", videos),
                                   ("audio", "reference_audio", audios)):
            content += [{"type": f"{kind}_url", f"{kind}_url": {"url": value}, "role": role}
                        for value in values]
        endpoint = "/contents/generations/tasks"
        body = {"model": model, "content": content, "duration": duration,
                "ratio": ratio, "resolution": resolution}
        if audio is not None:
            body["generate_audio"] = audio
        if seed is not None:
            body["seed"] = seed
        notes.append("含人脸参考需符合方舟可信素材/授权肖像规则；输入视频、音频时长由平台校验。")
    else:
        require(model == "gen4.5", "此 Runway 适配器仅支持 Gen-4.5")
        require(2 <= duration <= 10, "Gen-4.5 时长为 2–10 秒")
        require(resolution == "720p", "Gen-4.5 此入口输出 720p")
        require(not (last_image or images or videos or audios), "Gen-4.5 此入口只接受单张 image 首帧，不支持这些额外参考")
        require(audio is not True, "Gen-4.5 此入口不提供原生有声生成，请单独规划音频与口型流程")
        sizes = {"16:9": "1280:720", "9:16": "720:1280", "1:1": "960:960",
                 "4:3": "1104:832", "3:4": "832:1104", "21:9": "1584:672"}
        require(ratio in sizes, "Gen-4.5 需要明确画幅，不接受 adaptive")
        require(image is not None or ratio == "16:9", "Gen-4.5 文生此入口只开放已核实的 16:9；竖屏请提供首帧")
        require(len(prompt.encode("utf-16-le")) // 2 <= 1000, "Runway prompt 最多 1000 个 UTF-16 单元")
        endpoint = "/image_to_video" if image else "/text_to_video"
        body = {"model": model, "promptText": prompt, "ratio": sizes[ratio], "duration": duration}
        if image:
            body["promptImage"] = image
        if seed is not None:
            body["seed"] = seed
        notes.append("Gen-4.5 生成动作画面；该入口不自动提供配音、对口型或完整剪辑。")
    return {"provider": provider, "model": model, "endpoint": endpoint, "body": body, "notes": notes}


class Provider:
    def __init__(self, name, keys, transport):
        require(name in PROVIDERS, "未知供应商")
        self.name = name
        self.base = PROVIDERS[name]["base"]
        self.transport = transport
        self.headers = {"Authorization": "Bearer " + credential(name, keys),
                        "Content-Type": "application/json"}
        if name == "runway":
            self.headers["X-Runway-Version"] = "2024-11-06"

    def create(self, plan):
        response = self.transport.request("POST", self.base + plan["endpoint"], self.headers, plan["body"])
        self.check_response(response)
        result = response.get("data", {}) if self.name == "kling" else response
        task_id = result.get("id") if isinstance(result, dict) else None
        require(isinstance(task_id, str) and bool(task_id), "提交响应缺少任务 ID；请先到供应商控制台核对，不要直接重提")
        return validate_task_id(task_id)

    def check_response(self, response):
        if self.name == "kling" and response.get("code") != 0:
            raise APIError(f"Kling 业务错误 {response.get('code')}：{response.get('message', '')}")

    def status(self, task_id):
        task_id = validate_task_id(task_id)
        if self.name == "kling":
            endpoint = "/tasks?" + urlencode({"task_ids": task_id})
        elif self.name == "seedance":
            endpoint = "/contents/generations/tasks/" + quote(task_id, safe="")
        else:
            endpoint = "/tasks/" + quote(task_id, safe="")
        response = self.transport.request("GET", self.base + endpoint, self.headers)
        self.check_response(response)
        if self.name == "kling":
            items = response.get("data")
            require(isinstance(items, list), "Kling 查询响应缺少任务数组")
            matches = [item for item in items if isinstance(item, dict) and item.get("id") == task_id]
            require(len(matches) == 1, "Kling 未返回所查询的唯一任务，保留原状态后再查询")
            item = matches[0]
            values = item.get("outputs", [])
            require(isinstance(values, list) and all(isinstance(value, dict) for value in values), "Kling 视频输出格式错误")
            outputs = [value.get("url") for value in values if value.get("type") == "video"]
            error = item.get("message")
        else:
            item = response
            require(item.get("id") == task_id, "任务查询响应 ID 不匹配")
            if self.name == "seedance":
                content = item.get("content") or {}
                require(isinstance(content, dict), "Seedance 视频输出格式错误")
                url = content.get("video_url")
                outputs = [url] if url else []
                error = item.get("error")
            else:
                outputs = item.get("output", [])
                error = item.get("failure") or item.get("failureCode")
        raw_status = item.get("status")
        require(isinstance(raw_status, str), "查询响应缺少 status")
        state = raw_status.lower()
        mapping = {"submitted": "queued", "pending": "queued", "throttled": "queued",
                   "queued": "queued", "processing": "running", "running": "running",
                   "succeeded": "succeeded", "failed": "failed", "canceled": "cancelled",
                   "cancelled": "cancelled", "expired": "expired"}
        require(state in mapping, f"未知任务状态 {state}；不会推断成功或自动重提")
        require(isinstance(outputs, list), "查询响应输出列表格式错误")
        outputs = [https_url(url) for url in outputs]
        if mapping[state] == "succeeded":
            require(bool(outputs), "任务报告成功但缺少视频地址，请重新查询")
        return {"status": mapping[state], "outputs": outputs, "error": error,
                "usage": item.get("usage"), "quality_review": "pending"}


def validate_task_id(value):
    require(isinstance(value, str) and re.fullmatch(r"[A-Za-z0-9_-]{1,200}", value), "任务 ID 格式不正确")
    return value
