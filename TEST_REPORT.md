# Mock PI Server — Test Report (Re-validation)

## 测试环境

| Item           | Value                                                          |
| -------------- | -------------------------------------------------------------- |
| Git Commit     | 31719212a0102e6f20cbe3f7f07169f7833d848b (fixes on top of bd17150) |
| Python Version | 3.11.9 (tags/v3.11.9:de54cf5, MSC v.1938 64 bit)                |
| OS             | Windows (win32), native Python — no container                   |
| Framework      | FastAPI 0.133.1 / Uvicorn 0.41.0 / Pydantic 2.13 / httpx 0.28.1 |
| 执行时间       | 2026-09-18                                                      |

## 第一轮问题修复摘要

| ID   | 问题                                   | 状态 |
| ---- | -------------------------------------- | ---- |
| P0-1 | SQLite 重启持久化实际失效              | 已修复 |
| P0-2 | DataServer Points API 缺失             | 已修复 |
| P0-2 | DataServer by name / path 缺失         | 已修复 |
| P1-1 | `--config` 未完整作用于运行服务        | 已修复 |
| P1-2 | 启动 auth 配置被忽略 / auth_type fail-open | 已修复 |
| P1-3 | Batch API 非 PI 格式                   | 已修复 |
| P1-4 | 非法 Timestamp 可能 500                | 已修复 |
| P1-5 | drop_connection 无真实网络验收         | 已补测试 |
| P1-6 | 无 Tag/WebId/Path 冲突校验             | 已修复 |
| P1-7 | Point 缺少 Links                       | 已修复 |
| P1-8 | `/mock/tags/{tag}/quality` 对未知 Tag 成功 | 已修复 |
| P2   | Docker / req.txt / README / 本报告     | 已清理 |

### 关键语义变更

- **Server Startup**：打开 SQLite，若为空才 seed 默认数据；已有数据保留。
- **`POST /mock/reset`**：唯一 destructive 操作，删除数据并 seed 默认值。

## 测试分层结果

### 1. Unit / API Test（TestClient，memory）

Command: `pytest -v`（全量）

```text
Total:   89
Passed:  89
Failed:  0
Skipped: 0
```

覆盖：Server List / By WebId / By Name / By Path、Server Points + nameFilter +
maxCount、Point by path/webId/name、Point Links、Current Value、Recorded（范围、
maxCount、时区、排序、重复、异常时间戳）、Write / Batch Write / Read-After-Write、
类型校验、Batch API（keyed dictionary）、Unknown Point、Empty History、Bad Quality、
quality unknown 404、Authentication、Parameter Delay、HTTP 500/503、Invalid JSON、
Omit Fields、Endpoint Fault、Fault times、Reset、Request History、Tag 冲突
（Name/WebId/Path）、auth fail-open、Large History（100,000 点）。

### 2. Process Integration Test（真实 Windows 进程 + 真实 socket）

| File                       | 用例数 | 说明 |
| -------------------------- | ----- | ---- |
| tests/test_process_sqlite.py  | 3 | SQLite 重启持久化、reset 恢复默认、reset 跨重启保持 |
| tests/test_process_config.py  | 4 | 自定义 `--config`、启动 auth、env 覆盖、缺失目录自动创建 |
| tests/test_process_network.py | 4 | drop_connection 真实网络错误、force_status、读写周期、LAN IP |
| tests/test_tcp_fault.py       | 3 | TCP close / reset / hang（真实子进程） |

这些用例 `python -m app.main` 启动真实子进程并抓取真实 TCP 连接，不再是
TestClient + memory。

#### SQLite 重启持久化（自动化断言）

```text
tests/test_process_sqlite.py::test_sqlite_survives_process_restart PASSED
```

#### drop_connection（真实网络层）

```text
tests/test_process_network.py::test_drop_connection_produces_network_error PASSED
```

客户端得到 `RemoteProtocolError` / `ReadError` / 连接中断，而非完整 200 响应。

### 3. 手工 Windows 进程验收（SQLite 重启 + reset）

命令序列（真实 Uvicorn 进程，独立临时 SQLite）：

```text
POST /piwebapi/streams/POINT_TEMP_001/value  {"Value":424.2}   -> 202
GET  /piwebapi/streams/POINT_TEMP_001/value                    -> Value 424.2
（终止进程）
（用同一 DB 重新启动）
GET  /piwebapi/streams/POINT_TEMP_001/value                    -> Value 424.2  (持久化 PASS)
POST /mock/reset                                               -> {"success":true}
GET  /piwebapi/streams/POINT_TEMP_001/value                    -> Value 25.5   (reset PASS)
GET  /piwebapi/streams/POINT_TEMP_001/recorded                 -> {"Items":[]} (history PASS)
```

### 4. PowerShell Smoke Test

Command: `powershell -ExecutionPolicy Bypass -File scripts\smoke_test.ps1`

```text
[PASS] health
[PASS] dataserver
[PASS] dataserver discovery
[PASS] dataserver points
[PASS] point
[PASS] point links
[PASS] current value
[PASS] generate
[PASS] history
[PASS] write
[PASS] read-after-write
[PASS] fault force_status
[PASS] mock isolation
[PASS] reset
[PASS] post-reset
Mock PI Server smoke test PASSED
```

### 5. LAN 访问验收

```text
localhost:8080      -> health 200  PASS
127.0.0.1:8080      -> health 200  PASS
LAN IPv4:8091       -> health 200  PASS
```

自动检测到的 LAN 接口地址：

```text
LAN IPv4 tested: 198.18.0.1
Server machine: 本机 (Windows)
Client machine: 本机（经 LAN 接口地址访问）
Result: PASS
```

说明：本机通过 `socket.connect` 探测到的出口地址为 `198.18.0.1`（RFC 2544
benchmark 保留段，通常为 VPN/虚拟适配器地址）。该地址对本机可达，测试证明
`--host 0.0.0.0` 下非回环接口可访问。**跨物理机 LAN 验收未执行**，需在目标
测试网络中由测试人员按 README 步骤复核。

### 6. TCP 5450 Fault Server

```text
mode=close -> 客户端 recv 得到 EOF (b'')                  PASS
mode=reset -> 客户端得到 RST 异常                          PASS
mode=hang  -> 客户端 recv 超时 (socket.timeout)           PASS
```

### 7. Performance（Large History）

```text
POST /mock/data/generate count=100000 -> Generated 100000
GET  /piwebapi/streams/POINT_TEMP_001/recorded?maxCount=100000 -> HTTP 200, 100000 items
Server 不 crash / 不 OOM
```

## 未执行 / 超出范围项

| 项目             | 说明 |
| ---------------- | ---- |
| HTTPS            | Optional；启动参数已支持，未做端到端证书验收 |
| 100 concurrent   | Optional；未执行 |
| Docker / Linux   | Out of Scope；相关文件已删除 |

## 已知限制

- 跨物理机 LAN 验收未执行（本机无第二台设备）。本机 LAN 接口访问已 PASS。
- 检测到的 LAN 地址 `198.18.0.1` 属保留段，若非目标环境真实网段，请在部署
  网络中用 `ipconfig` 获取实际 IPv4 并复核。
- HTTPS 仅验证配置路径，未做证书链端到端测试。
- TCP 5450 不模拟任何 PI 协议，仅网络故障。
- AF SDK / PI SDK / AF 数据模型不实现（按规格为非目标）。

## 最终判定

第一轮全部 Mandatory 缺陷已修复，并补充真实进程 / SQLite / 网络层测试。

```text
pytest = 0 failed (89 passed)
PowerShell Smoke Test = PASS
Windows native startup = PASS
SQLite persistence = PASS
SQLite reset = PASS
Custom config = PASS
DataServer discovery = PASS
Point discovery = PASS
Read = PASS
Write = PASS
History = PASS
Fault Injection = PASS
Authentication = PASS
drop_connection = PASS
Request History = PASS
TCP 5450 fault server = PASS
LAN IP access (本机) = PASS

FINAL RESULT = PASS
```
