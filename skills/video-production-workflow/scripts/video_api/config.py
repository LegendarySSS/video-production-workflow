import getpass
import json
import os
import warnings
from pathlib import Path


class VideoError(Exception):
    pass


PROVIDERS = {
    "kling": {
        "key": "KLING_API_KEY",
        "base": "https://api-singapore.klingai.com",
        "model": "kling-4.0",
    },
    "seedance": {
        "key": "ARK_API_KEY",
        "base": "https://ark.cn-beijing.volces.com/api/v3",
        "model": "doubao-seedance-2-0-260128",
    },
    "runway": {
        "key": "RUNWAYML_API_SECRET",
        "base": "https://api.dev.runwayml.com/v1",
        "model": "gen4.5",
    },
}


def load_keys(env_file):
    values = {}
    path = Path(env_file)
    allowed = {item["key"] for item in PROVIDERS.values()}
    if path.exists():
        for line_number, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if line.startswith("export "):
                line = line[7:]
            name, separator, value = line.partition("=")
            name = name.strip()
            if name not in allowed:
                continue
            if not separator:
                raise VideoError(f"环境文件第 {line_number} 行格式错误")
            value = value.strip()
            if value.startswith('"'):
                try:
                    value = json.loads(value)
                except ValueError as error:
                    raise VideoError(f"环境文件第 {line_number} 行引号格式错误") from error
            elif value.startswith("'") and value.endswith("'"):
                value = value[1:-1]
            if not isinstance(value, str):
                raise VideoError("密钥必须是字符串")
            values[name] = value
    for name in allowed:
        if name in os.environ:
            values[name] = os.environ[name]
    return values


def credential(provider, keys):
    name = PROVIDERS[provider]["key"]
    value = keys.get(name, "").strip()
    if not value or any(character.isspace() for character in value):
        raise VideoError(f"请在本机配置有效的 {name}；不要把密钥发送到聊天中")
    if value.lower().startswith(("your_", "your-", "replace_")):
        raise VideoError(f"{name} 仍是示例值，请替换成本人的 API Key")
    return value


def configure(provider, env_file):
    path = Path(env_file)
    if path.exists():
        raise VideoError("环境文件已存在；请在本机编辑，或用 --env-file 指定新文件，避免覆盖")
    name = PROVIDERS[provider]["key"]
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", getpass.GetPassWarning)
            secret = getpass.getpass(f"输入 {name}（不回显）：").strip()
    except (getpass.GetPassWarning, EOFError) as error:
        raise VideoError("需要本人在支持不回显输入的终端配置密钥；不会降级成明文输入") from error
    credential(provider, {name: secret})
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(descriptor, "w", encoding="utf-8") as output:
        output.write(f"{name}={json.dumps(secret)}\n")
    return {"provider": provider, "env_file": str(path), "saved": True}


def redact(message, keys):
    text = str(message)
    for value in sorted(keys.values(), key=len, reverse=True):
        if value:
            text = text.replace(value, "[REDACTED]")
    return text
