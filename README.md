<div align="center">

<img width="100%" alt="header" src="https://capsule-render.vercel.app/api?type=waving&height=210&text=Lovaum%20Bot&fontAlign=50&fontAlignY=36&fontSize=56&desc=Mining%20Cycles%7CProfit%20Claims%7CReward%20Ads%7CPower%20Points%7CCountdown"/>

<img alt="typing" src="https://readme-typing-svg.demolab.com?font=Inter&size=18&duration=3000&pause=650&center=true&vCenter=true&width=900&lines=Full%20daily%20cycle%20automation%20for%20the%20Lovaum%20Miniapp;Earning%20is%20started%20once%20and%20the%20mined%20profit%20is%20claimed%20every%20cycle;The%20channel%20gate%20plus%20the%20one%20time%20signup%20bonus%20are%20handled%20automatically;Reward%20ads%20and%20reward%20boxes%20credited%20only%20after%20the%20server%20confirms;Multi%20account%20with%20proxy%20support%20and%20a%20live%20countdown%20between%20cycles"/>

<p>
  <img alt="python" src="https://img.shields.io/badge/Python-3.8%2B-3776AB?logo=python&logoColor=white"/>
  <img alt="platform" src="https://img.shields.io/badge/Platform-Lovaum%20Miniapp-111111"/>
  <img alt="multi-account" src="https://img.shields.io/badge/Multi--Account-Supported-111111"/>
  <img alt="proxy" src="https://img.shields.io/badge/Proxy-Supported-111111"/>
  <img alt="author" src="https://img.shields.io/badge/by-Yuurisandesu-111111"/>
</p>

<p>
  <b>Lovaum Bot</b> is a full automation bot for the Lovaum Telegram Miniapp.<br/>
  It handles the complete daily cycle: a signed sign in with a stable per account device line, the mandatory channel gate together with the one time signup bonus, the mining earning cycle from start through profit claim, the hourly reward advertisement that pays power points, every reward box waiting for this account, and an optional payout request to your own TON wallet, all running automatically across multiple accounts with proxy support and a live countdown between cycles.<br/>
  Built and distributed by <b>Yuurisandesu</b>.
</p>

</div>

---

## Table of Contents

- [Requirements](#requirements)
- [Installation](#installation)
- [Configuration](#configuration)
- [Running the Bot](#running-the-bot)
- [Features](#features)
- [File Structure](#file-structure)
- [Disclaimer](#disclaimer)

---

## Requirements

- Python `3.8+`
- Git

---

## Installation

**Clone the repository:**

```bash
git clone https://github.com/Yuurisan-N1/Lovaum-Miniapp.git
cd Lovaum-Miniapp
```

**Install dependencies:**

```bash
pip install aiohttp yuurisan
```

---

## Configuration

### 1. Accounts (data.txt)

Fill `data.txt` with Telegram WebApp `initData` for each account, one per line:

```
user=%7B%22id%22...&hash=abc123
user=%7B%22id%22...&hash=def456
```

> `initData` can be obtained from the browser DevTools when opening Lovaum on Telegram Web.

An optional `|TON_ADDRESS` suffix is tolerated on the same line. When it is present the bot saves that address and sends a payout request as soon as the mined balance reaches the minimum the server reports, so the line looks like `user=%7B%22id%22...&hash=abc123|UQ...`.

### 2. Proxy (proxy.txt)

Fill `proxy.txt` with proxies, one per line (optional, leave empty to run without proxy):

```
host:port
host:port:user:pass
http://user:pass@host:port
```

Proxies are assigned to accounts by index in round-robin order.

### 3. Bot Settings (config.json)

`sleep_seconds` controls how many seconds the bot waits between cycles. If `config.json` is missing, it is created automatically with a default of `3600` seconds.

---

## Running the Bot

```bash
python bot.py
```

Press `Ctrl+C` at any time to stop the bot cleanly.

---

## Features

### Sign In and Device Line

Every account signs in with its own credential plus a device identifier derived from its Telegram id, and the session the server hands back is carried for the rest of the cycle. The sign in line reports the account name, its Lovaum coin balance and its reward point balance as the server returns them.

### Channel Gate and Signup Bonus

The miniapp keeps earning locked until the official channels are joined, so the bot checks that gate first and reports the channel bonus the moment the server pays it. An account that has not joined yet is reported in yellow instead of being run further.

### Earning Cycle

Earning is started when the server says no cycle is active, and the mined profit is claimed on every cycle. The claim line only appears when the server answers with a collected amount, and the account balance and mining power are read back from the server afterwards.

### Reward Advertisements

The watch and earn slot is read first so the bot knows how many reward points are paid, how many are left for the day and when the next slot opens. A slot that is still cooling down or already used for the day is reported instead of being hammered, and a credited advertisement prints the points the server answered with.

### Reward Boxes

Every sealed reward box held by the account is opened one by one and each opening prints the power points the server credited.

### Payout Request

When the data line carries a TON address, the bot saves it and sends a payout request once the mined balance reaches the minimum the server reports. A payout that the server refuses is reported with the reason it gave, and an account without an address simply skips this phase.

### Multi Account

All accounts in `data.txt` are processed one after another in the order they are listed within every cycle. The cycle number is logged at the start of each round.

### Proxy Support

Proxies are loaded from `proxy.txt` and assigned to accounts by position in round-robin order. Proxy credentials are masked in log output. Running without proxies is fully supported.

### Auto Countdown

After all accounts complete a cycle, the bot displays a live `HH:MM:SS` countdown until the next cycle starts.

---

## File Structure

```text
Lovaum-Miniapp/
├── bot.py          # Main bot, full daily cycle automation
├── config.json     # Sleep duration between cycles
├── data.txt        # Account initData, one per line
├── proxy.txt       # Proxy list, one per line (optional)
├── LICENSE         # License file
└── utils/
    └── banner.py   # Banner using yuurisan module
```

---

## Disclaimer

This tool is built for educational and technical exploration purposes. Use it wisely and at your own responsibility.

---

<div align="center">
<img width="100%" alt="footer" src="https://capsule-render.vercel.app/api?type=waving&height=120&section=footer"/>
</div>
