function app() {
  return {
    hosts: [],
    services: [],
    diagnostics: {},
    changes: [],
    assets: [],
    scanning: false,
    wsState: 'disconnected',
    _ws: null,
    _retryTimer: null,
    speedtestTarget: '',
    speedtestCount: 15,
    speedtestRunning: false,
    speedtestError: '',
    speedtest: {},
    baselinePinning: false,
    baselineError: '',

    init() {
      this.connectWS();
      this.fetchInitial();
    },

    connectWS() {
      const protocol = location.protocol === 'https:' ? 'wss' : 'ws';
      const url = `${protocol}://${location.host}/ws`;
      this._ws = new WebSocket(url);

      this._ws.onopen = () => {
        this.wsState = 'connected';
        clearTimeout(this._retryTimer);
      };

      this._ws.onmessage = (ev) => {
        try {
          const msg = JSON.parse(ev.data);
          this.handleMessage(msg);
        } catch (_) {}
      };

      this._ws.onclose = () => {
        this.wsState = 'disconnected';
        this._retryTimer = setTimeout(() => this.connectWS(), 5000);
      };

      this._ws.onerror = () => {
        this._ws.close();
      };
    },

    handleMessage(msg) {
      switch (msg.type) {
        case 'scan_start':
          this.scanning = true;
          break;
        case 'scan_done':
          this.scanning = false;
          break;
        case 'hosts':
          this.hosts = msg.data || [];
          break;
        case 'services':
          this.services = msg.data || [];
          break;
        case 'diagnostics':
          this.diagnostics = msg.data || {};
          break;
        case 'speedtest':
          this.speedtest = msg.data || {};
          break;
        case 'change_detected':
          this.changes = msg.data || [];
          break;
        case 'cache':
          if (msg.data.hosts) this.hosts = msg.data.hosts;
          if (msg.data.services) this.services = msg.data.services;
          if (msg.data.diagnostics) this.diagnostics = msg.data.diagnostics;
          if (msg.data.speedtest) this.speedtest = msg.data.speedtest;
          break;
      }
    },

    async fetchInitial() {
      try {
        const [h, s, d, sp, c, a] = await Promise.all([
          fetch('/api/hosts').then(r => r.json()),
          fetch('/api/services').then(r => r.json()),
          fetch('/api/diagnostics').then(r => r.json()),
          fetch('/api/speedtest').then(r => r.json()),
          fetch('/api/changes').then(r => r.json()),
          fetch('/api/assets').then(r => r.json()),
        ]);
        if (h.length) this.hosts = h;
        if (s.length) this.services = s;
        if (d.checks) this.diagnostics = d;
        if (sp.host) this.speedtest = sp;
        if (c.length) this.changes = c;
        if (a.length) this.assets = a;
      } catch (_) {}
    },

    async triggerScan() {
      this.scanning = true;
      try {
        await fetch('/api/scan');
      } catch (_) {
        this.scanning = false;
      }
    },

    async runSpeedtest() {
      this.speedtestError = '';
      const target = this.speedtestTarget.trim();
      if (!target) {
        this.speedtestError = 'Bitte IP oder Hostname eingeben';
        return;
      }
      this.speedtestRunning = true;
      try {
        const resp = await fetch('/api/speedtest', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ host: target, count: this.speedtestCount }),
        });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        this.speedtest = await resp.json();
      } catch (e) {
        this.speedtestError = e.message || 'Speedtest fehlgeschlagen';
      } finally {
        this.speedtestRunning = false;
      }
    },

    async pinBaseline() {
      this.baselineError = '';
      this.baselinePinning = true;
      try {
        const resp = await fetch('/api/baseline', { method: 'POST' });
        if (!resp.ok) {
          const err = await resp.json().catch(() => ({}));
          throw new Error(err.detail || `HTTP ${resp.status}`);
        }
        const a = await fetch('/api/assets').then(r => r.json());
        if (a.length) this.assets = a;
      } catch (e) {
        this.baselineError = e.message || 'Baseline konnte nicht gesetzt werden';
      } finally {
        this.baselinePinning = false;
      }
    },
  };
}
