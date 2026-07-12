# Enterprise Features

This document lists features planned for the Enterprise Edition of this
project, licensed separately under
[LICENSE.COMMERCIAL](LICENSE.COMMERCIAL). See [COMMERCIAL.md](COMMERCIAL.md)
for the licensing model.

## Status

No Enterprise features have shipped yet. This list is a forward-looking plan,
not a changelog of existing functionality: everything currently in this
repository is part of the Community Edition and remains MIT-licensed. See the
repository's own [ROADMAP.md](ROADMAP.md), "Dual-Licensing Readiness"
section, for the prerequisites that need to land first.

## Planned

- Multi-site and multi-tenant aggregation: a consolidated view across scans
  and baselines from multiple local networks, for MSPs managing several
  client sites.
- Credentialed enrichment (WMI, WinRM): deeper per-device data than
  unauthenticated network discovery can provide.
- Intune/Entra ID and UniFi controller integration: correlating scan
  results with existing device management and network infrastructure.
- Centralized reporting server: a fleet-wide dashboard aggregating results
  across sites, instead of a dashboard per scan host.

## Not planned

The core scanner, baseline/drift engine, and local dashboard stay in the
Community Edition permanently. Dual-licensing governs only new, enterprise-
shaped capabilities such as the ones listed above, not the tool's standalone
usefulness for a single network.
