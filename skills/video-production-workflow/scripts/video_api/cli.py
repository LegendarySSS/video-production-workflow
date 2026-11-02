import argparse
import json
import sys

from . import jobs
from .config import PROVIDERS, VideoError, configure, credential, load_keys, redact
from .providers import build_request
from .transport import Transport


def parser():
    root = argparse.ArgumentParser(description="可灵、Seedance、Runway 视频任务命令行；Python 3.10+，无第三方依赖")
    root.add_argument("--env-file", default=".env", help="仅本机读取的环境文件，进程环境变量优先")
    commands = root.add_subparsers(dest="command", required=True)
    setup = commands.add_parser("configure", help="交互式输入密钥并保存新环境文件；需要本人在终端操作")
    setup.add_argument("--provider", choices=PROVIDERS, required=True)
    doctor = commands.add_parser("doctor", help="离线检查密钥是否已配置；不验证权限或余额")
    doctor.add_argument("--provider", choices=PROVIDERS)
    preview = commands.add_parser("preview", help="离线校验镜头 JSON 并预览请求；不花费额度")
    preview.add_argument("--spec", required=True)
    submit = commands.add_parser("submit", help="创建一次付费视频任务；不会自动重复提交")
    submit.add_argument("--spec", required=True)
    submit.add_argument("--job-dir", required=True)
    submit.add_argument("--confirm-spend", action="store_true", help="确认授权本次创建；不是费用封顶开关")
    for name in ("status", "wait", "download", "attach"):
        command = commands.add_parser(name)
        command.add_argument("--job-dir", required=True)
        if name == "wait":
            command.add_argument("--timeout", type=int, default=600)
            command.add_argument("--poll-interval", type=int, default=60)
        elif name == "download":
            command.add_argument("--output", required=True)
            command.add_argument("--index", type=int, default=0)
            command.add_argument("--max-bytes", type=int, default=2 * 1024 ** 3)
        elif name == "attach":
            command.add_argument("--task-id", required=True)
    return root


def print_json(value, keys):
    print(redact(json.dumps(value, ensure_ascii=False, indent=2), keys))


def main(arguments=None):
    args = parser().parse_args(arguments)
    keys = {}
    try:
        if args.command == "configure":
            print_json(configure(args.provider, args.env_file), keys)
            return 0
        keys = load_keys(args.env_file)
        if args.command == "doctor":
            states = {}
            for name in ([args.provider] if args.provider else PROVIDERS):
                try:
                    credential(name, keys)
                    states[name] = "configured_not_verified"
                except VideoError:
                    states[name] = "missing_or_invalid"
            print_json({"providers": states, "network_called": False}, keys)
            return 0 if "configured_not_verified" in states.values() else 2
        if args.command == "preview":
            plan = build_request(jobs.read_json(args.spec))
            print_json({"network_called": False, "billable": False, **plan}, keys)
            return 0
        transport = Transport(keys)
        timed_out = False
        if args.command == "submit":
            if not args.confirm_spend:
                raise VideoError("submit 会消耗供应商额度；获本人授权后添加 --confirm-spend，仅创建一次任务")
            record = jobs.submit(jobs.read_json(args.spec), args.job_dir, keys, transport)
        elif args.command == "attach":
            record = jobs.attach(args.job_dir, args.task_id)
        elif args.command == "status":
            record = jobs.refresh(args.job_dir, keys, transport)
        elif args.command == "wait":
            record, timed_out = jobs.wait(args.job_dir, keys, transport, args.timeout, args.poll_interval)
        else:
            record = jobs.download(args.job_dir, keys, transport, args.output, args.index, args.max_bytes)
        print_json({**jobs.summary(record, args.job_dir), "wait_timed_out": timed_out}, keys)
        if timed_out:
            print("等待超时，远端任务仍可继续；再次 status/wait，不要重新 submit。", file=sys.stderr)
            return 3
        return 4 if record["status"] in ("failed", "cancelled", "expired", "rejected") else 0
    except (VideoError, OSError, ValueError, KeyError, TypeError) as error:
        message = str(error) if isinstance(error, VideoError) else "本地文件、参数或 API 响应格式错误；检查输入与 task.json。"
        print_json({"error": redact(message, keys)}, keys)
        return 2
    except KeyboardInterrupt:
        print("操作已中断；远端任务不会被自动取消。请检查 task.json 与供应商控制台。", file=sys.stderr)
        return 130
