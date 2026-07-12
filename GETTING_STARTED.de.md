<div align="center">
  <img src="RayStudio.png" alt="RayStudio Logo" width="120"/>

  <h1>NetScanX: Erste Schritte</h1>
</div>

[English](GETTING_STARTED.md) · [Zurück zur README](README.de.md)

---

Keine Vorkenntnisse nötig. NetScanX bietet **portable Binaries**: keine Python-Installation nötig, einfach eine Datei herunterladen und starten.

### Windows

**1. Herunterladen**

Die [Releases-Seite](https://github.com/9t29zhmwdh-coder/NetScanX/releases) im Browser öffnen. Beim neuesten Release auf **Assets** klicken, um die Liste aufzuklappen, dann `NetScanX-Start-Windows.exe` herunterladen.

<!-- TODO: Screenshot der Releases-Seite mit aufgeklappter Assets-Liste -->

**2. Starten**

Ordner mit der heruntergeladenen Datei öffnen (meist "Downloads") und Doppelklick auf `NetScanX-Start-Windows.exe`. Windows zeigt vermutlich einen blauen Bildschirm "Windows hat Ihren PC geschützt", das liegt daran, dass die Datei nicht digital signiert ist, nicht daran, dass etwas kaputt ist. Auf **"Weitere Informationen"**, dann **"Trotzdem ausführen"** klicken.

Ein Browser-Tab öffnet sich automatisch mit dem NetScanX-Dashboard, das bereits das lokale Netzwerk scannt.

<p align="center">
  <img src="docs/dashboard-screenshot.png" alt="NetScanX-Dashboard mit Change-Report- und Asset-Inventory-Karten" width="700"/>
</p>
<p align="center"><sub>Der Screenshot zeigt synthetische Demo-Daten, kein echtes Netzwerk.</sub></p>

### Linux

**1. Herunterladen**

[Releases-Seite](https://github.com/9t29zhmwdh-coder/NetScanX/releases) öffnen, **Assets** beim neuesten Release aufklappen, `NetScanX-Start-Linux` herunterladen.

**2. Terminal öffnen**

Bei den meisten Linux-Desktops: <kbd>Strg</kbd>+<kbd>Alt</kbd>+<kbd>T</kbd> drücken oder "Terminal" im Anwendungsmenü suchen.

**3. Starten**

```bash
cd ~/Downloads
chmod +x NetScanX-Start-Linux
./NetScanX-Start-Linux
```

Der `chmod +x`-Schritt ist nötig, weil heruntergeladene Dateien unter Linux standardmässig nicht ausführbar sind: ohne ihn passiert beim Doppelklick oder Ausführen nichts.

### macOS

**1. Herunterladen**

[Releases-Seite](https://github.com/9t29zhmwdh-coder/NetScanX/releases) öffnen, **Assets** beim neuesten Release aufklappen, `NetScanX-Start-macOS` herunterladen.

**2. Starten**

Doppelklick auf die heruntergeladene Datei. macOS verweigert mit "kann nicht geöffnet werden, da der Entwickler nicht verifiziert werden kann". Stattdessen: Rechtsklick (oder Ctrl-Klick) auf die Datei → **"Öffnen"** → im Dialog nochmal **"Öffnen"** bestätigen. Das ist nur einmal nötig.

### Was danach passiert (alle Plattformen)

Ein Browser-Tab öffnet sich automatisch mit dem NetScanX-Dashboard, das bereits das lokale Netzwerk scannt. Es wird nichts installiert: die eine Datei löschen entfernt alles wieder vollständig.

Lieber die volle `pip`-installierte CLI statt der portablen Version? Die plattformspezifischen Befehle im [Schnellstart](README.de.md#schnellstart) sind bereits copy-paste-fertig.

### Troubleshooting

| Meldung / Problem | Was es bedeutet |
|---|---|
| "Windows hat Ihren PC geschützt" | Normal bei kleinen, unsignierten Open-Source-Tools, siehe Windows Schritt 2 |
| Doppelklick unter Linux tut nichts | Datei ist noch nicht als ausführbar markiert, `chmod +x` wie oben ausführen |
| macOS: "kann nicht geöffnet werden, da der Entwickler nicht verifiziert werden kann" | Rechtsklick → "Öffnen" einmalig, um Gatekeeper zu umgehen, siehe macOS Schritt 2 |
| Browser öffnet sich nicht automatisch | Manuell `http://localhost:8080` in einem beliebigen Browser öffnen, während das Tool läuft |
| Firewall fragt nach Netzwerkzugriff | Erlauben: NetScanX braucht das, um das lokale Netzwerk zu scannen, sendet aber sonst keine Daten irgendwohin |

Hakt's trotzdem? Ein [Issue auf GitHub](https://github.com/9t29zhmwdh-coder/NetScanX/issues) eröffnen.
