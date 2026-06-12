function app() {
  return {
    hosts: [],
    services: [],
    diagnostics: {},
    scanning: false,
    wsState: 'disconnected',
    _ws: null,
    _retryTimer: null,

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
        case 'cache':
          if (msg.data.hosts) this.hosts = msg.data.hosts;
          if (msg.data.services) this.services = msg.data.services;
          if (msg.data.diagnostics) this.diagnostics = msg.data.diagnostics;
          break;
      }
    },

    async fetchInitial() {
      try {
        const [h, s, d] = await Promise.all([
          fetch('/api/hosts').then(r => r.json()),
          fetch('/api/services').then(r => r.json()),
          fetch('/api/diagnostics').then(r => r.json()),
        ]);
        if (h.length) this.hosts = h;
        if (s.length) this.services = s;
        if (d.checks) this.diagnostics = d;
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
  };
}
