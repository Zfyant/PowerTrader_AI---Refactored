<div align="center">

# 🤖 PowerTrader AI <a href="https://github.com/garagesteve1155/PowerTrader_AI" target="_blank"><img src="https://img.shields.io/badge/GitHub-100000?style=for-the-badge&logo=github&logoColor=white" alt="GitHub"></a>

### <font color="orange">The Trading Bot That Thinks Like a Human <i>(But Faster)</i></font>

</div>

<div align="center">
  <button style="background-color: #329235ff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: default;">🪙 Fully Automated Crypto Trading</button> 
  <button style="background-color: #2e8a8dff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: default;">🤖 Pattern-Matching Intelligence</button> 
  <button style="background-color: #4c4eafff; color: white; padding: 10px 20px; border: none; border-radius: 4px; cursor: default;">🧠 Smart DCA</button>
</div>

<div align="center">

[![Version](https://img.shields.io/badge/version-1.0.0-blue?style=for-the-badge&logo=none)](https://github.com/garagesteve1155/PowerTrader_AI) [![Python](https://img.shields.io/badge/Python-3.10%2B-FFD43B?style=for-the-badge&logo=python&logoColor=blue)](https://github.com/garagesteve1155/PowerTrader_AI) [![License](https://img.shields.io/badge/License-Apache%202.0-orange?style=for-the-badge)](https://github.com/garagesteve1155/PowerTrader_AI) [![Maintenance](https://img.shields.io/badge/Maintained%3F-yes-green.svg?style=for-the-badge)](https://github.com/garagesteve1155/PowerTrader_AI)

<br>

## 🆚 Why This Bot is Different


<br>

Most bots are "black boxes" or just guess based on RSI. **PowerTrader AI** is transparent.

</div>

<div align="center">
  <table align="center">
    <tr>
      <th align="center">❌ Typical Trading Bots</th>
      <th align="center">✅ PowerTrader AI</th>
    </tr>
    <tr>
      <td align="center">Complex Neural Networks (Black Box)</td>
      <td align="center"><b>Pattern Recognition (Transparent)</b></td>
    </tr>
    <tr>
      <td align="center">Expensive GPU Required</td>
      <td align="center"><b>Runs on Any CPU</b></td>
    </tr>
    <tr>
      <td align="center">"Trust me, bro" logic</td>
      <td align="center"><b>"I've seen this pattern before" logic</b></td>
    </tr>
  </table>
</div>

<div align="center">

<br>

## 🧠 Core Philosophy: The "Perfect Memory"

</div>

<br>

> Imagine looking at a chart and saying: *"Hey, I've seen this exact pattern 50 times before. Usually, price goes up after this."*
> 
> That is exactly what PowerTrader AI does. 
> 
> It scans **every single candle in history** across multiple timeframes (1H to 1W) to find the closest matches to the current moment.

<div align="center">

<br>

| ⏱️ Timeframe | 🔍 What It Sees |
| :--- | :--- |
| **1 Hour** | Short-term momentum shifts |
| **4 Hours** | Intraday trend changes |
| **1 Day** | Daily market cycles |
| **1 Week** | Major trend reversals |

<br>

## ⚡ How It Actually Trades (The 3 Stages)

<table align="center">
  <tr>
    <td align="center" width="33%">
      <h1>🎯</h1>
      <h3>Stage 1: Smart Entry</h3>
      <p>The <b>Thinker</b> watches for "Oversold" signals on multiple timeframes.<br><br><b>The Rule:</b><br><code>LONG 3+</code> & <code>SHORT 0</code><br><br>We only buy when history says the odds are overwhelmingly in our favor.</p>
    </td>
    <td align="center" width="33%">
      <h1>🛡️</h1>
      <h3>Stage 2: Protective DCA</h3>
      <p>If the market dips, we don't panic. We use a <b>Tiered DCA System</b>.<br><br><b>Triggers:</b><br>🔹 Crosses 4th/5th prediction line<br>🔹 Max Drawdown % hit<br><br>⚠️ <i>Max 2 DCAs per 24h safety lock.</i></p>
    </td>
    <td align="center" width="33%">
      <h1>🚀</h1>
      <h3>Stage 3: Trailing Profit</h3>
      <p>We let winners run with a <b>Dynamic Trailing Stop</b>.<br><br><b>Targets:</b><br>🎯 5% (Standard)<br>🎯 2.5% (Recovery)<br><br>Once hit, a <b>0.5% trail</b> follows the price up!</p>
    </td>
  </tr>
</table>


<br>

## 📦 Quick Start & Deep Dive

<br>

</div>

<details>
<summary><b>�️ Step 1: Installation & Prerequisites (Click to Expand)</b></summary>
<br>

### 1. Install Python
1. Go to **python.org** and download Python for Windows (3.10 or newer).
2. Run the installer.
3. **CRITICAL:** Check the box that says: **“Add Python to PATH”**.
4. Click **Install Now**.

> **CRITICAL WARNING:** If you have any crypto holdings in your Robinhood account, you **MUST** either transfer them out or sell them to cash **BEFORE** using this bot.
>
> *Why?* The bot tracks performance based on your cash balance and its own trade history. Existing coins will confuse its logic. **Start with a clean slate (Cash Only).**

### 2. Get the Code

> **Note:** Please download files manually for now. 
> **Avoid "Download ZIP" due to a known GitHub structure quirk.**

1. Create a folder: `C:\PowerTraderAI`
2. Download `pt_hub.py` and all repo files into it.

### 3. Install Dependencies
Open **Command Prompt** (`cmd`) and run:

```bash
cd C:\PowerTraderAI

# If using Python 3.12+, run this first to avoid distutils errors:
python -m pip install setuptools

# Install bot requirements:
python -m pip install -r requirements.txt
```

### 4. Launch the Hub
This is your command center.
```bash
python pt_hub.py
```

</details>

<details>
<summary><b>⚙️ Step 2: Configuration & Robinhood API Keys (Click to Expand)</b></summary>
<br>

Once the Hub is open, go to **Settings** and follow this exact sequence:

### 1. Basic Setup
- **Main Neural Folder**: Set this to the folder containing `pt_hub.py` (e.g., `C:\PowerTraderAI`).
- **Coins**: Select **BTC** to start.

> **Note on Folders:** PowerTrader uses a simple structure. **BTC** lives in the main folder, and any other coin you add (like ETH, DOGE) will automatically get its own subfolder created inside it.

### 2. Robinhood API Setup
*This connects the bot to your account safely.*

1. Click **Robinhood API Setup** inside Settings.
2. Click **Generate Keys**.
3. **Copy the Public Key** shown in the wizard.
4. Go to your **Robinhood Account** -> **Security** -> **API Keys**.
5. Add a new key and paste the Public Key.
6. **Important:** Enable "Trading" permissions when asked.
7. Robinhood will show you an **API Key** (starts with `rh...`). Copy it.
8. Paste it back into the bot's wizard and click **Save**.
9. Close the wizard and click **SAVE** on the main Settings screen.

> **Security Note:** Your keys are stored locally in `r_key.txt` and `r_secret.txt`. Keep these safe!

</details>

<details>
<summary><b>🧠 Step 3: Training & Running the Bot (Click to Expand)</b></summary>
<br>

### The Workflow
1. **Train All**: Click this button in the Hub.
   - The AI scans the entire history of the selected coins.
   - It builds a memory database of patterns.
   - *Wait for this to finish.*

2. **Start All**: Click this when training is complete.
   - Launches `pt_thinker.py` (The Brain).
   - Launches `pt_trader.py` (The Executioner).

### Adding More Coins Later
1. Open **Settings**.
2. Add a new coin (e.g., ETH).
3. **Save**.
4. **Train All** again (it needs to learn the new coin's history).
5. **Start All**.

</details>

<details>
<summary><b>📈 Deep Dive: Understanding the Signals (Click to Expand)</b></summary>
<br>

### The "Instance-Based" Engine
PowerTrader isn't a neural network in the traditional "black box" sense. It uses **kNN (k-Nearest Neighbors) with Reliability Weighting**.

- **Input:** It looks at the current candle pattern.
- **Process:** It finds the top matches from history (1H to 1W timeframes).
- **Prediction:** It calculates a weighted average of what happened *after* those matches.
- **Visuals:** On the chart, you will see **Blue Lines (Predicted Lows)** and **Orange Lines (Predicted Highs)** for each timeframe.
- **Feedback Loop:** After every candle close, it re-evaluates its past predictions and adjusts the weights of those memories.

### Signal Strength Levels
- **LONG 0-2**: Weak correlation. The AI sees some bullish patterns, but not enough to risk capital.
- **LONG 3+ (THE TRIGGER):** **High Confidence.**
  - *Technical Definition:* The current **Ask Price** has dropped *below* the **Predicted Low (Blue Line)** on at least 3 different timeframes simultaneously.
  - *Meaning:* The asset is statistically oversold compared to historical patterns.
- **SHORT 1+**: Bearish pressure detected. The bot will **never** buy if the Short signal is > 0.

> **The Entry Rule:** `LONG >= 3` AND `SHORT == 0`

</details>

<br>

<div align="center">

## ⚙️ Workflow Summary

Once configured, your daily loop is simple!

<table>
  <tr>
    <td align="center"><b>Step 1: Setup ⚙️</b></td>
    <td align="center"><b>Step 2: Train 🧠</b></td>
    <td align="center"><b>Step 3: Trade 🚀</b></td>
  </tr>
  <tr>
    <td align="left">
      Configure keys & coins.<br>
      (One-time setup)
    </td>
    <td align="left">
      Click <b>Train All</b>.<br>
      Updates the "memory."
    </td>
    <td align="left">
      Click <b>Start All</b>.<br>
      Sit back and monitor.
    </td>
  </tr>
</table>

<br>

## 📊 The Neural Dashboard (Cheat Sheet)

When you see the logs, here is what the signals mean:

| Signal | Meaning | Action |
| :--- | :--- | :--- |
| 🟢 **LONG 0-2** | Weak buy signal | Wait ✋ |
| 🟢 **LONG 3+** | Strong buy signal | **Ready to Buy** ✅ |
| 🔴 **SHORT 1+** | Sell pressure detected | **Do Not Enter** 🚫 |

 **The Golden Ticket 🎫 :** `LONG 3+` AND `SHORT 0` = 🚀 **TRADE EXECUTES**

<br>

## ❤️ Support the Project

<div align="center">

**PowerTrader AI is 100% Free & Open Source.**  
*Made by garage coders, for garage coders.*

<br>

<a href="https://cash.app/$garagesteve">
  <img src="https://img.shields.io/badge/Cash_App-$garagesteve-00C244?style=for-the-badge&logo=cashapp&logoColor=white" height="40" />
</a>&nbsp;
<a href="https://paypal.me/garagesteve">
  <img src="https://img.shields.io/badge/PayPal-@garagesteve-00457C?style=for-the-badge&logo=paypal&logoColor=white" height="40" />
</a>&nbsp;
<a href="https://patreon.com/MakingMadeEasy">
  <img src="https://img.shields.io/badge/Patreon-Join_the_Family-F96854?style=for-the-badge&logo=patreon&logoColor=white" height="40" />
</a>

<br>
<br>

<sub>Released under the Apache 2.0 License.</sub>

</div>
