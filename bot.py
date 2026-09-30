import os
import sys
import json
import time
import signal
import hashlib
import asyncio
import aiohttp

from urllib.parse import parse_qs, unquote, quote

from utils.banner import show_banner

RESET = "\033[0m"
BOLD = "\033[1m"
RED = "\033[91m"
GREEN = "\033[92m"
YELLOW = "\033[93m"

MY_PROJECT = "Lovaum Miniapp"
BASE_URL = "https://lovaum.lovable.app"
REF_CODE = "6004380466"

def fit_width(msg):
    text = str(msg)
    return text if len(text) <= 63 else text[:63]

def log_green(msg):
    print(f"{GREEN}{BOLD}{fit_width(msg)}{RESET}", flush=True)

def log_yellow(msg):
    print(f"{YELLOW}{BOLD}{fit_width(msg)}{RESET}", flush=True)

def log_red(msg):
    print(f"{RED}{BOLD}{fit_width(msg)}{RESET}", flush=True)

def signal_handler(sig, frame):
    print(flush=True)
    log_red("Script stopped by user")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

def clean_text(value, fallback):
    if value is None:
        return str(fallback)
    text = str(value)
    for code in (91, 93, 124, 35, 33, 64, 36, 37, 94, 38, 42, 40, 41, 45, 44, 58, 59, 39, 34, 96, 126, 43, 61, 60, 62, 63, 47, 92):
        text = text.replace(chr(code), " ")
    text = "".join(char for char in text if ord(char) < 128)
    text = " ".join(text.split())
    return text if text else str(fallback)

def shorten(value, fallback, limit):
    text = clean_text(value, fallback)
    return text if len(text) <= limit else text[:limit].rstrip()

def unit_word(value, singular, plural):
    try:
        return singular if int(float(value)) == 1 else plural
    except Exception:
        return plural

def format_duration(seconds):
    total = int(max(0, seconds))
    hours = total // 3600
    minutes = (total % 3600) // 60
    rest = total % 60
    if hours:
        return f"{hours} {unit_word(hours, 'hour', 'hours')} {minutes} {unit_word(minutes, 'minute', 'minutes')}"
    if minutes:
        return f"{minutes} {unit_word(minutes, 'minute', 'minutes')} {rest} {unit_word(rest, 'second', 'seconds')}"
    return f"{rest} {unit_word(rest, 'second', 'seconds')}"

def format_amount(value):
    try:
        number = round(float(value), 6)
    except Exception:
        return str(value)
    text = f"{number:.6f}".rstrip("0").rstrip(".")
    return text if text else "0"

def format_int(value):
    try:
        return str(int(float(value)))
    except Exception:
        return "0"

def number_of(value, fallback=0.0):
    try:
        return float(value)
    except Exception:
        return fallback

def display_name(state, account):
    user = state.get("user") if isinstance(state.get("user"), dict) else {}
    for value in (
        user.get("firstName"),
        account.get("firstName"),
        user.get("username"),
        account.get("username"),
    ):
        name = clean_text(value, "")
        if name:
            return name
    return "Miner"

def encode_node(value):
    counter = [0]

    def walk(item):
        if item is True:
            return {"t": 2, "s": 2}
        if item is False:
            return {"t": 2, "s": 3}
        if item is None:
            return {"t": 2, "s": 0}
        if isinstance(item, bool):
            return {"t": 2, "s": 2 if item else 3}
        if isinstance(item, (int, float)):
            return {"t": 0, "s": item}
        if isinstance(item, str):
            return {"t": 1, "s": item}
        if isinstance(item, dict):
            counter[0] += 1
            return {
                "t": 10,
                "i": counter[0],
                "p": {"k": list(item.keys()), "v": [walk(x) for x in item.values()]},
                "o": 0,
            }
        if isinstance(item, (list, tuple)):
            counter[0] += 1
            return {"t": 9, "i": counter[0], "a": [walk(x) for x in item], "o": 0}
        return {"t": 1, "s": str(item)}

    return walk(value)

def decode_node(node):
    if not isinstance(node, dict):
        return node
    kind = node.get("t")
    if kind in (0, 1):
        return node.get("s")
    if kind == 2:
        return {0: None, 1: None, 2: True, 3: False}.get(node.get("s"))
    if kind == 9:
        return [decode_node(item) for item in node.get("a", [])]
    if kind in (10, 11):
        payload = node.get("p") or {}
        keys = payload.get("k") or []
        values = payload.get("v") or []
        return {key: decode_node(item) for key, item in zip(keys, values)}
    if kind == 25:
        raw = node.get("s")
        if isinstance(raw, dict) and isinstance(raw.get("message"), dict):
            return {"__error__": decode_node(raw.get("message"))}
        return {"__error__": str(raw)}
    return None

def unwrap(node):
    data = decode_node(node)
    if isinstance(data, dict) and ("result" in data or "error" in data):
        error = data.get("error")
        if isinstance(error, dict):
            error = error.get("__error__", error)
        return data.get("result"), error
    return data, None

def error_text(error):
    if isinstance(error, dict):
        return clean_text(error.get("message"), "")
    return clean_text(error, "")

def tsr_body(payload):
    return json.dumps(
        {"t": encode_node({"data": payload}), "f": 63, "m": []},
        separators=(",", ":"),
    )

def build_headers():
    return {
        "accept": "application/x-tss-framed, application/x-ndjson, application/json",
        "content-type": "application/json",
        "origin": BASE_URL,
        "referer": BASE_URL + "/",
        "user-agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/152.0.0.0 Mobile Safari/537.36",
        "x-tsr-serverfn": "true",
    }

def query_path(fn_id, payload):
    return f"/_serverFn/{fn_id}?payload=" + quote(tsr_body(payload), safe="")

def normalize_proxy(proxy_line):
    if not proxy_line:
        return None
    value = proxy_line.strip()
    if "://" in value:
        return value
    parts = value.split(":")
    if len(parts) == 4:
        host, port, user, password = parts
        return f"http://{user}:{password}@{host}:{port}"
    if len(parts) == 3:
        host, port, user = parts
        return f"http://{user}@{host}:{port}"
    return f"http://{value}"

def mask_proxy(proxy_url):
    try:
        value = proxy_url.split("://")[-1]
        after_at = value.split("@")[-1]
        host_part = after_at.split(":")[0]
        port_part = after_at.split(":")[1] if ":" in after_at else ""
        octets = host_part.split(".")
        if len(octets) == 4:
            masked_host = f"{octets[0]}*****{octets[3]}"
        elif len(host_part) > 4:
            masked_host = f"{host_part[:2]}*****{host_part[-2:]}"
        else:
            masked_host = "***"
        suffix = f":{port_part}" if port_part else ""
        return f"http://user:pass@{masked_host}{suffix}"
    except Exception:
        return "http://user:pass@***:***"

def load_config():
    defaults = {"settings": {"sleep_seconds": 3600}}
    if not os.path.exists("config.json"):
        return defaults
    try:
        with open("config.json") as handle:
            return json.load(handle)
    except Exception:
        return defaults

def load_lines(filename, required):
    if not os.path.exists(filename):
        if required:
            log_red(f"File {clean_text(filename, 'data.txt')} was not found")
            sys.exit(1)
        return []
    lines = [line.strip() for line in open(filename).readlines() if line.strip()]
    lines = [line for line in lines if not line.startswith("#")]
    if required and not lines:
        log_red("File data.txt is empty and holds no initData string")
        sys.exit(1)
    return lines

def parse_init_data(line):
    value = line.strip()
    if "tgWebAppData=" in value:
        value = value.split("tgWebAppData=", 1)[1]
        value = value.split("&tgWebAppVersion")[0].split("&tgWebAppPlatform")[0]
        value = unquote(value)
    fields = parse_qs(value, keep_blank_values=True)
    raw_user = (fields.get("user") or [""])[0]
    if not raw_user:
        return None
    try:
        profile = json.loads(raw_user)
    except Exception:
        try:
            profile = json.loads(unquote(raw_user))
        except Exception:
            return None
    if not isinstance(profile, dict) or not profile.get("id"):
        return None
    return {
        "initData": value,
        "id": str(profile.get("id")),
        "username": str(profile.get("username") or ""),
        "firstName": str(profile.get("first_name") or ""),
    }

def busy_error(status, payload):
    if status in (500, 502, 503, 504):
        return True
    if isinstance(payload, dict):
        message = str(payload.get("message") or "")
    else:
        message = str(payload or "")
    message = message.lower()
    return "busy" in message or "timeout" in message

async def post_fn(session, fn_id, payload, proxy):
    url = f"{BASE_URL}/_serverFn/{fn_id}"
    for attempt in range(1, 3 + 1):
        try:
            async with session.post(
                url,
                data=tsr_body(payload),
                headers=build_headers(),
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                text = await response.text()
                try:
                    result, error = unwrap(json.loads(text))
                except Exception:
                    result, error = None, None
                if response.status < 400 and not busy_error(response.status, error):
                    return result, error
        except Exception:
            pass
        if attempt < 3:
            countdown(4 * attempt, "Retry in")
    return None, None

async def get_fn(session, fn_id, payload, proxy):
    url = BASE_URL + query_path(fn_id, payload)
    for attempt in range(1, 3 + 1):
        try:
            async with session.get(
                url,
                headers=build_headers(),
                proxy=proxy,
                timeout=aiohttp.ClientTimeout(total=30),
            ) as response:
                text = await response.text()
                if response.status < 400:
                    try:
                        result, error = unwrap(json.loads(text))
                    except Exception:
                        return None, None
                    if not busy_error(response.status, error):
                        return result, error
        except Exception:
            pass
        if attempt < 3:
            countdown(4 * attempt, "Retry in")
    return None, None

async def sign_in(session, account, proxy):
    device_id = hashlib.md5(account["id"].encode()).hexdigest()
    payload, error = await post_fn(
        session, "c182efdf92b76b91a8a86979210d6732238b6b4ad1c22de5c111ebb76db33e76", {"initData": account["initData"], "deviceId": device_id}, proxy
    )
    if isinstance(payload, dict) and payload.get("ok"):
        return True
    return False

async def read_state(session, account, proxy):
    payload, error = await post_fn(session, "7a87ff1b975d33f236435bc30cad483f0f5721fada0f7babee848ff3d320cad2", {"initData": account["initData"]}, proxy)
    if isinstance(payload, dict):
        return payload
    return {}

async def read_mining(session, proxy):
    payload, error = await post_fn(session, "b5b9c98977ce5ae095b27d0ca9db0675cbd5b72aec9be882bedd509cfdbb89cc", {}, proxy)
    if isinstance(payload, dict):
        return payload
    return {}

async def claim_channel_bonus(session, state, proxy):
    membership = state.get("membership") if isinstance(state.get("membership"), dict) else {}
    joined = bool(membership.get("channelJoined"))
    payload, error = await post_fn(session, "774003f9f6db015e99bf119c6ea90afc69759490e3c6bd771ab24ecb84ba3bd0", {}, proxy)
    if not isinstance(payload, dict):
        if not joined:
            log_yellow("Channel gate could not be checked for this account")
        return joined
    if payload.get("claimed"):
        log_green(f"Channel bonus credited {clean_text(format_int(payload.get('claimed')), 0)} coins")
    if not payload.get("miningUnlocked"):
        log_yellow("Channel join is required before mining unlocks")
        return False
    return True

async def start_earning(session, mining, proxy):
    if mining.get("started"):
        return
    payload, error = await post_fn(session, "1cf9f1e8361e57f73accc138b64610b1d34830df0925e65c24c29807ced6cf2c", {}, proxy)
    if isinstance(payload, dict) and payload.get("started") and not payload.get("alreadyRunning"):
        log_green("Earning started for this account")
    elif isinstance(payload, dict) and payload.get("started"):
        return
    elif error_text(error):
        log_yellow(f"Earning start says {clean_text(shorten(error_text(error), 'refused', 24), 'refused')}")

async def claim_ad_rewards(session, proxy):
    now_ms = int(time.time() * 1000)
    state, error = await get_fn(session, "194c375e1aa96cfe428cadce9a153828e0e8c79f5790d49a3ece214f656d2a2e", {}, proxy)
    if not isinstance(state, dict) or not state.get("enabled"):
        return
    limit = int(number_of(state.get("dailyLimit")))
    today = int(number_of(state.get("today")))
    if limit and today >= limit:
        log_yellow("Daily reward ad limit is reached on this account")
        return
    next_at = int(number_of(state.get("nextAt")))
    if next_at and next_at > now_ms:
        log_yellow(f"Ad reward opens in {format_duration((next_at - now_ms) / 1000)}")
        return
    payload, error = await post_fn(session, "ebff04002b9a457dbe1e30cc4408f96e63051bf87adeb934c40610e226d05a52", {}, proxy)
    if isinstance(payload, dict) and payload.get("points") is not None:
        log_green(
            f"Ad reward credited {clean_text(format_int(payload.get('points')), 0)} power points"
        )
        return
    reason = error_text(error)
    if reason in ("AD_COOLDOWN", "AD_LIMIT"):
        log_yellow("Reward ad is still cooling down on this account")
    elif reason:
        log_yellow(f"Reward ad says {clean_text(shorten(reason, 'refused', 24), 'refused')}")

async def open_reward_boxes(session, state, proxy):
    referrals = state.get("referrals") if isinstance(state.get("referrals"), dict) else {}
    boxes = referrals.get("boxes")
    if not isinstance(boxes, list):
        return
    sealed = [box for box in boxes if isinstance(box, dict) and box.get("status") == "sealed"]
    if not sealed:
        log_yellow("No sealed reward box is waiting on this account")
        return
    total = 0
    for box in sealed:
        box_id = str(box.get("id") or "")
        if not box_id:
            continue
        payload, error = await post_fn(session, "916bd53f8d10c81f871ce78052855ccf5f5ba14f5c64681d729425f5dea258d9", {"boxId": box_id}, proxy)
        if isinstance(payload, dict) and payload.get("points") is not None:
            total += int(number_of(payload.get("points")))
            log_green(
                f"Reward box opened for {clean_text(format_int(payload.get('points')), 0)} power points"
            )
        else:
            log_yellow("Reward box was refused by the server")

async def collect_profit(session, proxy):
    payload, error = await post_fn(session, "06c7c831fbdde55c5d8f53e0e46153cf4a7c1cdc23c47d2951cd7ecc40f850f1", {}, proxy)
    if isinstance(payload, dict):
        collected = number_of(payload.get("collected"))
        if collected > 0:
            log_green(f"Profit collected {clean_text(format_amount(collected), 0)} USDT")
        return collected
    reason = error_text(error)
    if reason:
        log_yellow(f"Profit claim says {clean_text(shorten(reason, 'refused', 24), 'refused')}")
    return 0.0

async def process_account(line, proxy, index):
    account = parse_init_data(line)
    if not account:
        log_red(f"Credential line {clean_text(index, 1)} is not valid initData")
        return

    connector = aiohttp.TCPConnector(ssl=False)

    async with aiohttp.ClientSession(connector=connector) as session:
        if not await sign_in(session, account, proxy):
            log_red(f"Sign in failed for account number {clean_text(index, 1)}")
            return

        state = await read_state(session, account, proxy)
        if not state:
            log_red(f"Account number {clean_text(index, 1)} has no readable state")
            return

        user = state.get("user") if isinstance(state.get("user"), dict) else {}
        name = shorten(display_name(state, account), "Miner", 20)
        log_green(
            f"Signed in {clean_text(name, 'Miner')} with "
            f"{clean_text(format_int(user.get('bonusBalance')), 0)} coins and "
            f"{clean_text(format_int(user.get('powerPoints')), 0)} points"
        )

        await claim_channel_bonus(session, state, proxy)

        mining = await read_mining(session, proxy)
        if not mining:
            log_yellow("Earning state was not returned by the server")
            return

        await start_earning(session, mining, proxy)
        await claim_ad_rewards(session, proxy)
        await open_reward_boxes(session, state, proxy)
        await collect_profit(session, proxy)

        mining = await read_mining(session, proxy) or mining
        log_green(
            f"Balance is {clean_text(format_amount(mining.get('balance')), 0)} USDT with "
            f"{clean_text(format_amount(mining.get('power')), 0)} power"
        )

async def main_async(accounts, proxies, sleep_secs):
    cycle = 1
    while True:
        log_yellow(f"Starting automation cycle number {clean_text(cycle, 0)}")

        for index, line in enumerate(accounts):
            if index > 0:
                print()

            proxy_line = proxies[index % len(proxies)] if proxies else None
            proxy_url = normalize_proxy(proxy_line) if proxy_line else None
            if proxy_url:
                log_yellow(f"Using proxy {mask_proxy(proxy_url)}")

            await process_account(line, proxy_url, index + 1)
            countdown(1, "Next account in")

        log_yellow(f"Automation cycle number {clean_text(cycle, 0)} is complete")
        cycle += 1
        countdown(sleep_secs, "Next cycle starts in")
        show_banner(MY_PROJECT)

def countdown(seconds, label):
    total = int(seconds)
    if total < 1:
        return
    line = ""
    for remaining in range(total, 0, -1):
        hours = remaining // 3600
        minutes = (remaining % 3600) // 60
        rest = remaining % 60
        line = f"{label} {hours:02d}:{minutes:02d}:{rest:02d}"
        print(f"\r{YELLOW}{BOLD}{line}{RESET}", end="", flush=True)
        time.sleep(1)
    print("\r" + " " * (len(line) + 6) + "\r", end="", flush=True)

def main():
    try:
        sys.stdout.reconfigure(line_buffering=True)
        sys.stderr.reconfigure(line_buffering=True)
    except Exception:
        pass

    show_banner(MY_PROJECT)

    if sys.platform == "win32":
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

    config = load_config()
    sleep_secs = config.get("settings", {}).get("sleep_seconds", 3600)
    accounts = load_lines("data.txt", True)
    proxies = load_lines("proxy.txt", False)
    asyncio.run(main_async(accounts, proxies, sleep_secs))

if __name__ == "__main__":
    main()
