import ipaddress
import json
import os
import socket
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

from .config import VideoError, redact


class APIError(VideoError):
    def __init__(self, message, ambiguous=False):
        super().__init__(message)
        self.ambiguous = ambiguous


class NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, request, response, code, message, headers, url):
        return None


def https_url(value):
    if not isinstance(value, str):
        raise VideoError("素材地址必须是 HTTPS 字符串")
    if any(ord(character) < 32 or ord(character) == 127 for character in value):
        raise VideoError("素材地址不能包含控制字符")
    parsed = urllib.parse.urlsplit(value)
    if parsed.scheme != "https" or not parsed.hostname or parsed.username or parsed.password:
        raise VideoError("仅接受不含用户名密码的 HTTPS 素材地址")
    try:
        if parsed.port not in (None, 443):
            raise VideoError("素材 HTTPS 地址只能使用默认端口")
    except ValueError as error:
        raise VideoError("素材地址端口错误") from error
    if parsed.fragment:
        raise VideoError("素材地址不能包含 fragment")
    return value


def public_download_url(value):
    https_url(value)
    host = urllib.parse.urlsplit(value).hostname
    try:
        addresses = socket.getaddrinfo(host, 443, type=socket.SOCK_STREAM)
    except OSError as error:
        raise VideoError("视频下载域名解析失败；请稍后重新查询任务") from error
    if not addresses or any(not ipaddress.ip_address(item[4][0]).is_global for item in addresses):
        raise VideoError("拒绝从本机、内网或保留地址下载视频")


class Transport:
    def __init__(self, keys, timeout=60):
        self.keys = keys
        self.timeout = timeout
        self.opener = urllib.request.build_opener(NoRedirect())

    def request(self, method, url, headers, body=None):
        payload = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
        request = urllib.request.Request(url, payload, headers, method=method)
        attempts = 3 if method == "GET" else 1
        for attempt in range(attempts):
            try:
                with self.opener.open(request, timeout=self.timeout) as response:
                    raw = response.read(8 * 1024 * 1024 + 1)
                if len(raw) > 8 * 1024 * 1024:
                    raise ValueError("response too large")
                result = json.loads(raw)
                if not isinstance(result, dict):
                    raise ValueError("expected object")
                return result
            except urllib.error.HTTPError as error:
                retryable = error.code == 429 or error.code >= 500
                if retryable and attempt + 1 < attempts:
                    delay = error.headers.get("Retry-After", "")
                    time.sleep(min(float(delay), 10) if delay.isdigit() else 2 ** attempt)
                    continue
                detail = ""
                try:
                    data = json.loads(error.read(16384))
                    detail = data.get("message") or data.get("error", "")
                    if isinstance(detail, dict):
                        detail = detail.get("message", "")
                except (ValueError, AttributeError):
                    pass
                hint = ""
                if error.code in (401, 403):
                    hint = "检查 API Key、模型开通权限与 API 账户额度。"
                elif error.code == 429:
                    hint = "请求受限；查询已有任务，不要盲目重复提交。"
                raise APIError(
                    redact(f"API HTTP {error.code}。{hint} {str(detail)[:1000]}", self.keys),
                    ambiguous=method == "POST" and (error.code >= 500 or error.code == 408),
                ) from None
            except (urllib.error.URLError, TimeoutError, OSError) as error:
                if attempt + 1 < attempts:
                    time.sleep(2 ** attempt)
                    continue
                raise APIError(
                    "API 网络或 TLS 请求失败；提交结果不明时请先到供应商控制台核对。",
                    ambiguous=method == "POST",
                ) from error
            except (ValueError, UnicodeError) as error:
                raise APIError("API 返回了无法解析的响应", ambiguous=method == "POST") from error
        raise AssertionError("request loop must return or raise")

    def download(self, url, destination, max_bytes):
        destination = Path(destination)
        if destination.exists() or destination.is_symlink():
            raise VideoError("输出文件已存在，拒绝覆盖")
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            for redirect in range(6):
                public_download_url(url)
                try:
                    response = self.opener.open(
                        urllib.request.Request(url, headers={"User-Agent": "video-production-workflow/0.2"}),
                        timeout=self.timeout,
                    )
                    break
                except urllib.error.HTTPError as error:
                    location = error.headers.get("Location")
                    if error.code not in (301, 302, 303, 307, 308) or not location or redirect == 5:
                        raise VideoError(f"视频下载失败（HTTP {error.code}）；可重新查询后再下载") from None
                    url = urllib.parse.urljoin(url, location)
            else:
                raise VideoError("视频下载重定向次数超限")
            with response:
                length = response.headers.get("Content-Length", "")
                if length.isdigit() and int(length) > max_bytes:
                    raise VideoError("视频超过下载大小上限")
                first_chunk = response.read(65536)
                if len(first_chunk) < 12 or first_chunk[4:8] != b"ftyp":
                    raise VideoError("下载结果不是可识别的 MP4/MOV 文件，未保存为成片")
                descriptor, name = tempfile.mkstemp(prefix=".video-", suffix=".part", dir=destination.parent)
                temporary = Path(name)
                with os.fdopen(descriptor, "wb") as output:
                    total = 0
                    chunk = first_chunk
                    while chunk:
                        total += len(chunk)
                        if total > max_bytes:
                            raise VideoError("视频超过下载大小上限")
                        output.write(chunk)
                        chunk = response.read(65536)
                    if length.isdigit() and total != int(length):
                        raise VideoError("视频下载不完整，可重新下载同一任务")
                    output.flush()
                    os.fsync(output.fileno())
                os.link(temporary, destination)
            return str(destination.resolve())
        except (urllib.error.URLError, TimeoutError, OSError) as error:
            raise VideoError("视频下载或保存失败；原输出未覆盖，可重新下载同一任务") from error
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
