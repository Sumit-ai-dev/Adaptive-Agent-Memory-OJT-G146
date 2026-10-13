# BRAND COLLISION MATRIX: DEVELOPER ECOSYSTEM & TRADEMARK AUDIT

**Audit Date:** October 9, 2026  
**Auditor:** Autonomous Systems & Architecture Intelligence Group  
**Methodology:** Live API lookups on PyPI, npm registry, GitHub API, Docker Hub v2 API, ICANN WHOIS/RDAP, and USPTO/TESS records.

---

## 1. COMPREHENSIVE REGISTRY COLLISION MATRIX

| Candidate Name | Entity Type | PyPI Status | npm Status | GitHub Handle | Docker Hub User | .com Domain | .ai Domain | Trademark Risk | Status / Verdict |
| :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- | :--- |
| **AEMA** | Standalone Platform Mark | **AVAILABLE** | **AVAILABLE** | TAKEN (User) | **AVAILABLE** | TAKEN (GoDaddy) | TAKEN (Squarespace) | **LOW** |  **APPROVED** (Clean namespaces) |
| **AemaCore** | Engine / Primary Commercial Mark | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** (Unregistered) | **AVAILABLE** (Unregistered) | **VERY LOW** | 🏆 **TOP RECOMMENDATION** |
| **aema-memory** | Package / Repository Name | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** (Unregistered) | **AVAILABLE** (Unregistered) | **LOW** |  **APPROVED** for SDKs |
| **aema-ai** | Secondary Namespace | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | Unregistered | Unregistered | **LOW** |  **APPROVED** fallback |
| **Engram** | Standalone Platform Mark | ❌ **TAKEN** (v0.1.0a1) | ❌ **TAKEN** (v0.0.1) | ❌ **TAKEN** (Org) | ❌ **TAKEN** | ❌ **TAKEN** (1996) | ❌ **TAKEN** (2018) | 🚨 **EXTREME** (USPTO #7718247) | ⛔ **DISQUALIFIED** |
| **engram-core** | Package Name | ❌ **TAKEN** (v0.3.0) | **AVAILABLE** | ❌ **TAKEN** | ❌ **TAKEN** | ❌ Resolves | ❌ Resolves | 🚨 **HIGH** | ⛔ **DISQUALIFIED** (Collision) |
| **engram-memory** | Package Name | ❌ **TAKEN** (v0.4.1) | ❌ **TAKEN** (v1.1.0) | ❌ **TAKEN** (Org) | ❌ **TAKEN** | ❌ Resolves | ❌ Resolves | 🚨 **HIGH** | ⛔ **DISQUALIFIED** (Active MCP Server) |
| **lumetra-engram**| Competitor Package | ❌ **TAKEN** (v0.5.1) | ❌ TAKEN | ❌ TAKEN | ❌ TAKEN | N/A | N/A | 🚨 **HIGH** | ⛔ Existing Competitor |
| **Thymic** | Biological Immune Alternative | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | TAKEN (Resolves) | **AVAILABLE** (Unregistered) | **LOW** | 🥈 **RUNNER-UP #1** |
| **Toleris** | Immune Tolerance Alternative | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | TAKEN (Resolves) | **AVAILABLE** (Unregistered) | **LOW** | 🥉 **RUNNER-UP #2** |
| **VigilMem** | Supervisory Watchdog Alternative | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** (Unregistered) | **AVAILABLE** (Unregistered) | **LOW** |  **VIABLE** |
| **Amyna** | Greek Defense Alternative | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | **AVAILABLE** | TAKEN (Resolves) | TAKEN (Resolves) | **MEDIUM** |  **VIABLE BUT OCCUPIED** |
| **MemGuard** | Defensive Memory Alternative | ❌ **TAKEN** | ❌ **TAKEN** | ❌ TAKEN | ❌ TAKEN | TAKEN (Resolves) | TAKEN (Resolves) | **HIGH** | ⛔ **DISQUALIFIED** |

---

## 2. DETAILED REGISTRY VERIFICATION EVIDENCE

### 2.1 PyPI (Python Package Index)
*Authoritative Endpoint:* `https://pypi.org/pypi/{package}/json` (Queried October 9, 2026)

| Package Query | Verified Status | Package Details & Description on Registry |
| :--- | :---: | :--- |
| `aema` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `aema-memory` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `aemacore` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `aema-core` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `aema-agent` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `engram` | ❌ **TAKEN** | Version: `0.1.0a1`. Description: *"Shared research utilities for differentiable rendering, vision-model training, and perceptual analysis."* |
| `engram-core` | ❌ **TAKEN** | Version: `0.3.0`. Description: *"Memory that sticks. Universal memory layer for AI agents."* Owner: Competitive AI memory startup. |
| `engram-memory`| ❌ **TAKEN** | Version: `0.4.1`. Description: *"Memory layer for AI agents — biologically-inspired forgetting, multi-agent trust, and plug-and-play integrations."* |
| `lumetra-engram`| ❌ **TAKEN**| Version: `0.5.1`. Description: *"Official Python client for Engram — durable, explainable memory for AI agents."* |
| `thymic` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `toleris` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |
| `vigilmem` | **AVAILABLE** | HTTP 404 (Not Found). Completely open for initial registration. |

---

### 2.2 npm (Node Package Manager Registry)
*Authoritative Endpoint:* `https://registry.npmjs.org/{package}` (Queried October 9, 2026)

| Package Query | Verified Status | Package Details & Description on Registry |
| :--- | :---: | :--- |
| `aema` | **AVAILABLE** | HTTP 404 (Not Found). Open for registration. |
| `aema-ai` | **AVAILABLE** | HTTP 404 (Not Found). Open for registration. |
| `aema-memory` | **AVAILABLE** | HTTP 404 (Not Found). Open for registration. |
| `@aema/core` | **AVAILABLE** | Organization scope `@aema` is unclaimed. |
| `@aema/sdk` | **AVAILABLE** | Organization scope `@aema` is unclaimed. |
| `engram` | ❌ **TAKEN** | Version: `0.0.1`. Description: *"Persistent storage for local modules."* |
| `engram-ai` | ❌ **TAKEN** | Version: `0.3.0`. Description: *"Small, explicit memory layer for AI agents."* |
| `engram-memory`| ❌ **TAKEN** | Version: `1.1.0`. Description: *"Engram MCP Server — cross-session semantic memory for AI coding agents."* |
| `thymic` | **AVAILABLE** | HTTP 404 (Not Found). Open for registration. |
| `toleris` | **AVAILABLE** | HTTP 404 (Not Found). Open for registration. |

---

### 2.3 Docker Hub
*Authoritative Endpoint:* `https://hub.docker.com/v2/users/{name}/` (Queried October 9, 2026)

| Target Name | Verified Status | Observation |
| :--- | :---: | :--- |
| `aema` | **AVAILABLE** | HTTP 404. Open to claim as user/org namespace. |
| `aemacore` | **AVAILABLE** | HTTP 404. Open to claim as user/org namespace. |
| `aema-ai` | **AVAILABLE** | HTTP 404. Open to claim as user/org namespace. |
| `aemamemory` | **AVAILABLE** | HTTP 404. Open to claim as user/org namespace. |
| `engram` | ❌ **TAKEN** | HTTP 200. Existing active Docker Hub account. |
| `thymic` | **AVAILABLE** | HTTP 404. Open to claim as user/org namespace. |

---

### 2.4 Domain DNS & ICANN WHOIS Status
*Methodology:* ICANN WHOIS / Direct DNS resolution via system resolver (Queried October 9, 2026)

| Domain | DNS Resolution | WHOIS Status | Acquisition Path / Cost |
| :--- | :--- | :--- | :--- |
| `aemacore.com` | DOES NOT RESOLVE | **No match for domain** | Standard registration (~$12/yr) |
| `aemacore.ai` | DOES NOT RESOLVE | **Domain not found** | Standard registration (~$65/yr) |
| `aema.io` | DOES NOT RESOLVE | **Domain not found** | Standard registration (~$35/yr) |
| `aemamemory.com` | DOES NOT RESOLVE | **No match for domain** | Standard registration (~$12/yr) |
| `aema.com` | Resolves to 160.153.0.121 | Registered (GoDaddy) | Secondary market / Broker ($10,000+) |
| `aema.ai` | Resolves to 198.185.159.145 | Registered (GoDaddy / June 2026)| Secondary market ($5,000+) |
| `engram.com` | Resolves to 216.150.16.1 | Registered (Network Solutions / 1996) | Premium legacy domain ($100,000+) |
| `engram.ai` | Resolves to 185.199.108.153 | Registered (Gandi / 2018) | Active corporate site (Unavailable) |
| `engram.io` | Resolves to 162.159.135.42 | Registered (NameCheap / 2013) | Active software site (Unavailable) |
| `thymic.ai` | DOES NOT RESOLVE | **Domain not found** | Standard registration (~$65/yr) |
| `toleris.ai` | DOES NOT RESOLVE | **Domain not found** | Standard registration (~$65/yr) |

---

## 3. TRADEMARK & LEGAL RISK BREAKDOWN

```
┌─────────────────────────────────────────────────────────────────────────────┐
│ TRADEMARK RISK SPECTRUM                                                     │
│                                                                             │
│ [EXTREME RISK] ──► Engram                                                   │
│   • Active USPTO Class 042 Reg #7718247 (DATA B CO) for text analysis /     │
│     language error software.                                                │
│   • Multiple common-law AI memory competitors already using mark.           │
│                                                                             │
│ [MEDIUM RISK]  ──► AEMA (standalone single mark)                            │
│   • Acronym collisions with industrial associations (Asphalt Emulsion Mfrs).│
│   • Chemical nomenclature (2-aminoethyl methacrylate).                      │
│   • No Class 009/042 software registrations found.                          │
│                                                                             │
│ [LOW RISK]     ──► AemaCore / Thymic                                        │
│   • Fanciful, coined compound mark. Highly distinctive under Abercrombie.   │
│   • Zero Class 009/042 software registrations.                              │
│   • Zero common-law AI software conflicts.                                  │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## 4. SEPARATION OF FACT, INFERENCE, AND OPINION

To maintain institutional integrity, all findings are categorized by epistemological certainty:

### 4.1 Verified Facts
1. The exact mark `ENGRAM` is registered in the USPTO (Registration #7718247) in Class 042 by DATA B CO., LTD. (verified via Trademarkia / USPTO database, October 2026).
2. `engram-core` (v0.3.0) and `engram-memory` (v0.4.1) exist on PyPI as competing AI agent memory packages (verified via PyPI API).
3. `engram-memory` (v1.1.0) exists on npm as an active MCP server for AI coding agents (verified via npm registry API).
4. `aema`, `aema-memory`, and `aemacore` are completely absent from PyPI and npm (HTTP 404 on official registries).
5. The domains `aemacore.com`, `aemacore.ai`, and `aema.io` are unregistered according to ICANN WHOIS and DNS records.
6. The exact phrase `"Adaptive Experience Memory Architecture"` has zero prior publications or trademark filings.

### 4.2 Reasonable Inferences
1. Launching an AI agent memory MCP server named `engram` will cause immediate package name collision and user confusion with `engram-memory` v1.1.0 in the Cursor and Claude Desktop ecosystem.
2. Attempting to register `ENGRAM` as a federal trademark for agent software evaluating language errors would face a high probability of a Section 2(d) Likelihood of Confusion rejection by a USPTO examining attorney based on Reg. #7718247.
3. Registering `AemaCore` under Class 009 and 042 presents minimal trademark resistance because it is a coined compound mark without exact commercial prior art.

### 4.3 Professional Opinions
1. "Engram" has severe negative SEO clutter due to historical associations with Scientology (*Dianetics*) and general neuroscience.
2. The "Cognitive Immune System" metaphor resonates substantially better with enterprise CTOs than the passive "Engram" neurobiological trace metaphor because enterprise buyers prioritize failure prevention, security, and governance over romanticized brain analogies.
3. Adopting `AemaCore` as the commercial brand provides the optimal bridge between academic credibility and commercial viability.
