# Evidence Folder Index & Submission Checklist
## Computer Networks Capstone: Phase 1 Evidence Repository

> **Course Requirement (Section 9 & 10)**:
> *"All deliverables must be organised and ready before the evaluation slot. The evaluator should be able to find any piece of evidence within 30 seconds."*
> **Marks Weightage**:
> - LAN Setup & DNS (Tasks A & B): **10 Marks**
> - Backends & Reverse Proxy Load Balancing (Tasks C & D): **10 Marks**
> - HTTPS / TLS Correctness & Handshake (Task E): **8 Marks**
> - Packet Analysis & Protocol Flow Evidence (Task G): **7 Marks**
> - HTTP Caching Demonstration (Task F): **5 Marks**

---

## Network Topology Reference

| Machine | Role | IP Address | Interface |
|:---|:---|:---|:---|
| **Mac 1** | DNS Server + Client | `10.7.9.245` | `en0` |
| **Mac 2** | Edge nginx + Load Balancer | `10.7.5.53` | `en0` |
| **Mac 3** | Backend A | `10.7.22.10` | `en0` |
| **Mac 4** | Backend B + Client | `10.7.7.25` | `en0` |

**Subnet**: `255.255.224.0 (/19)` | **Gateway**: `10.7.0.1`

---

## 1. Quick Navigation Table

| Evaluation Task | Evidence Directory | Status | Artifacts Present |
|:---|:---|:---|:---|
| **Task A: Private LAN + DNS** | `evidence/task-a/` | ✅ COMPLETE | 5 text evidence files |
| **Task B: HTTPS / Load Balancing** | `evidence/task-b/` | ✅ COMPLETE | curl -v, load balancing, nginx config |
| **Task C: HTTP Backends** | `evidence/task-c/` | ✅ VERIFIED (B only) | `Mac4-TaskC-BackendB-Local.png` |
| **Task D: Load Balancer** | `evidence/task-d/` | ✅ VERIFIED | `Mac2-TaskD-LoadBalancing.png`, `Mac4-TaskD-LoadBalancing.png` |
| **Task E: HTTPS / TLS** | `evidence/task-e/` | ✅ VERIFIED | `Mac2-TaskE-Certificate.png`, `Mac2-TaskE-HTTPS.png` |
| **Task F / D: HTTP Caching & Failure** | `evidence/task-f/` | ✅ COMPLETE | Cache headers, explanation, failure before/after/restored |
| **Task G: Wireshark Capture** | `evidence/task-g/` | ✅ COMPLETE | DNS, TCP handshake, TLS text + Wireshark screenshots |
| **Section 6.3: Failures** | `evidence/failures/` | ✅ TEXT EVIDENCE | See task-f/36–39 for failure outputs |

---

## 2. Task A — LAN & DNS (`evidence/task-a/`)

| File | Description |
|:---|:---|
| `01-machine-identity.txt` | All 4 machine IPs, roles, subnet, and gateway |
| `02-dnsmasq-config.txt` | Mac 1 dnsmasq config: listen-address, interface, A records |
| `03-dig-client.txt` | `dig app.cn-capstone.test` from client — NOERROR, TTL 30, answer `10.7.5.53`, server `10.7.9.245#53` |
| `04-dig-public-dns.txt` | `dig @8.8.8.8 app.cn-capstone.test` — NXDOMAIN (proves private-only domain) |
| `05-ping-results.txt` | Pairwise ping matrix between all 4 machines |

---

## 3. Task B — HTTPS / Reverse Proxy / Load Balancing (`evidence/task-b/`)

| File | Description |
|:---|:---|
| `06-https-curl-v.txt` | Full `curl -v` output: TLSv1.3, CHACHA20-POLY1305, SAN verified, `200 OK`, `X-Backend: B`. No `-k` flag used. |
| `07-load-balancing-six-requests.txt` | 6 requests showing alternating `X-Backend: A` and `X-Backend: B` (round-robin proven) |
| `08-nginx-config.txt` | nginx `upstream backend_pool` + `server` block with TLS and proxy headers |

---

## 4. Task C — HTTP Backends (`evidence/task-c/`)

| File | Description |
|:---|:---|
| `Mac4-TaskC-BackendB-Local.png` | `curl -i https://app.cn-capstone.test:8443/api/status` from Mac 4. `200 OK`, `X-Backend: B`, `ETag: "B-v1"`, `Cache-Control: max-age=60`. |

---

## 5. Task D — Load Balancing (`evidence/task-d/`)

| File | Description |
|:---|:---|
| `Mac2-TaskD-LoadBalancing.png` | 20-request loop from Mac 2 showing `X-Backend` alternating A/B |
| `Mac4-TaskD-LoadBalancing.png` | 20-request loop from Mac 4 using `--resolve` flag. `X-Backend` alternates A→B→A→B (10 each) |

---

## 6. Task E — HTTPS / TLS (`evidence/task-e/`)

| File | Description |
|:---|:---|
| `Mac2-TaskE-Certificate.png` | Certificate inspection showing SAN `app.cn-capstone.test` and TLS issuer |
| `Mac2-TaskE-HTTPS.png` | `curl --cacert` with strict hostname verification succeeds (no `-k` flag) |

---

## 7. Task F / D — HTTP Caching & Failure Demonstration (`evidence/task-f/`)

| File | Description |
|:---|:---|
| `Mac2-TaskF-Cache-200.png` | Initial request: `200 OK` with `ETag: "B-v1"` and `Cache-Control: max-age=60` |
| `Mac2-TaskF-Public-304.png` | Conditional request from Mac 2 returning `304 Not Modified` |
| `Mac4-TaskF-Cache-304.png` | `curl -H 'If-None-Match: "B-v1"'` from Mac 4 → `304 Not Modified` |
| `34-cache-headers.txt` | Raw HTTP response headers showing `Cache-Control: max-age=60` and `ETag: "B-v1"` |
| `35-cache-explanation.txt` | Explanation of `Cache-Control`, `ETag`, and `304 Not Modified` behaviour |
| `36-failure-demonstration.txt` | Narrative description of Backend A failure and recovery |
| `37-failure-before.txt` | Request outputs before Backend A was stopped (A and B alternating) |
| `38-failure-after.txt` | Request outputs after Backend A stopped (all X-Backend: B) |
| `39-failure-restored.txt` | Request outputs after Backend A was restarted (A and B resuming) |

---

## 8. Task G — Wireshark Protocol Flow (`evidence/task-g/`)

| File | Description |
|:---|:---|
| `Mac4-TaskG-DNS-Wireshark.png` | Wireshark DNS filter: query → DNS server `10.7.9.245`, response `app.cn-capstone.test A 10.7.5.53` |
| `Mac4-TaskG-TCP-Handshake.png` | Wireshark `tcp.port == 8443`: SYN, SYN-ACK, ACK between Mac 4 (`10.7.7.25`) and Nginx (`10.7.5.53`) |
| `Mac4-TaskG-TLS-Handshake.png` | Wireshark TLS filter: ClientHello (SNI=`app.cn-capstone.test`) → ServerHello → Application Data |
| `Mac4-TaskG-Encrypted-AppData.png` | Encrypted Application Data packets — payload not readable, proving confidentiality |
| `31-wireshark-dns.txt` | DNS capture annotation: UDP 53, A record, `app.cn-capstone.test → 10.7.5.53`, TTL 30 |
| `32-wireshark-tcp-handshake.txt` | TCP handshake annotation: SYN `10.7.9.245:52166 → 10.7.5.53:8443`, SYN-ACK, ACK |
| `33-wireshark-tls.txt` | TLS capture annotation: ClientHello with SNI, ServerHello, encrypted Application Data |

> **Tip for evaluator demo**: `Mac4-TaskG-TCP-Handshake.png` shows the full connection flow in one screenshot (TCP SYN/SYN-ACK/ACK + TLS negotiation).

---

## 9. Documentation (`documentation/`)

| File | Description |
|:---|:---|
| `CN_Phase_1_MAC1_DNS_Server_FULL_EVIDENCE_COMPACT.pdf` | Mac 1 (Aditya Rana) — DNS Server full evidence PDF |
| `CN_Phase_1_MAC4.pdf` | Mac 4 (Saumya Mishra) — Backend B full evidence PDF |

---

## 10. Quick Re-verification Commands (Eval Day)

```bash
# DNS
dig @10.7.9.245 app.cn-capstone.test

# Full stack health
curl -i https://app.cn-capstone.test:8443/api/status

# Cache 304
curl -i -H 'If-None-Match: "B-v1"' https://app.cn-capstone.test:8443/api/status

# Load balancing (6 requests)
for i in {1..6}; do
  curl -sk -D - https://app.cn-capstone.test:8443/ -o /dev/null | grep X-Backend
done
```

---

## 11. Evidence Integrity Notice

> All text evidence files contain exact command outputs captured during live evaluation preparation.
> IP addresses, HTTP headers, TLS parameters, and packet descriptions are not altered.
> Screenshots are unmodified captures from Wireshark and macOS terminal sessions.
> No `-k` / `--insecure` flag was used for any HTTPS verification.

---

*All evidence corresponds to the CN Phase 1 form and project requirements.*
