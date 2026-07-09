<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>

  <h1>NetScanX — Getting Started</h1>
</div>

[🇩🇪 Deutsche Version](GETTING_STARTED.de.md) · [Back to README](README.md)

---

No prior experience needed. NetScanX ships **portable binaries** — no Python installation required at all, just download one file and run it.

### Windows

**1. Download**

Open the [Releases page](https://github.com/9t29zhmwdh-coder/NetScanX/releases) in your browser. Under the newest release, click **Assets** to expand the list, then download `NetScanX-Start-Windows.exe`.

<!-- TODO: Screenshot of the Releases page with the Assets list expanded -->

**2. Run**

Open the folder where it downloaded (usually "Downloads") and double-click `NetScanX-Start-Windows.exe`. Windows will likely show a blue screen saying "Windows protected your PC" — that's because the file isn't digitally signed, not because anything is broken. Click **"More info"**, then **"Run anyway"**.

A browser tab opens automatically with the NetScanX dashboard, already scanning your local network.

<p align="center">
  <img src="docs/dashboard-screenshot.png" alt="NetScanX dashboard showing the Change Report and Asset Inventory cards" width="700"/>
</p>
<p align="center"><sub>Screenshot uses synthetic demo data, not a real network.</sub></p>

### Linux

**1. Download**

Open the [Releases page](https://github.com/9t29zhmwdh-coder/NetScanX/releases), expand **Assets** under the newest release, and download `NetScanX-Start-Linux`.

**2. Open a terminal**

Most Linux desktops: press <kbd>Ctrl</kbd>+<kbd>Alt</kbd>+<kbd>T</kbd>, or find "Terminal" in your application menu.

**3. Run**

```bash
cd ~/Downloads
chmod +x NetScanX-Start-Linux
./NetScanX-Start-Linux
```

The `chmod +x` step is needed because downloaded files aren't executable by default on Linux — without it, double-clicking or running the file does nothing.

### macOS

**1. Download**

Open the [Releases page](https://github.com/9t29zhmwdh-coder/NetScanX/releases), expand **Assets** under the newest release, and download `NetScanX-Start-macOS`.

**2. Run**

Double-click the downloaded file. macOS will refuse with "cannot be opened because the developer cannot be verified". Instead, right-click (or Control-click) the file → **"Open"** → confirm **"Open"** in the dialog. You only need to do this once.

### What happens next (all platforms)

A browser tab opens automatically showing the NetScanX dashboard, already scanning your local network. Nothing is installed — delete the one file to remove it completely.

Prefer the full `pip`-installed CLI over the portable binary instead? Use the platform-specific commands in the main [Quick Start](README.md#quick-start) — they're already copy-paste ready.

### Troubleshooting

| Message / problem | What it means |
|---|---|
| "Windows protected your PC" | Normal for small, unsigned open-source tools — see Windows step 2 |
| Nothing happens when double-clicking on Linux | File isn't marked executable yet — run `chmod +x` as shown above |
| macOS: "cannot be opened because the developer cannot be verified" | Right-click → "Open" once to bypass Gatekeeper, see macOS step 2 |
| Browser doesn't open automatically | Manually open `http://localhost:8080` in any browser while the tool is running |
| Firewall prompt asking to allow network access | Allow it — NetScanX needs this to scan your local network, it doesn't send data anywhere else |

Still stuck? Open an [issue on GitHub](https://github.com/9t29zhmwdh-coder/NetScanX/issues).
