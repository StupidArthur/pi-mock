# Mock PI Server — Test Report

## 测试环境

| Item           | Value                                             |
| -------------- | ------------------------------------------------- |
| Git Commit     | n/a (not a git repository)                        |
| Python Version | 3.11.9 (MSC v.1938 64 bit)                        |
| OS             | Windows (win32)                                   |
| Framework      | FastAPI 0.133.1 / Uvicorn 0.41.0 / Pydantic 2.13 |
| Storage        | memory (pytest), sqlite (runtime verification)    |
| 执行时间       | 2026-09-18                                        |

## pytest 结果

Command: `pytest -v`

```text
Total:   59
Passed:  59
Failed:  0
Skipped: 0

Result: PASS
```

### 覆盖范围

| 区域              | 测试                                                                 |
| ----------------- | -------------------------------------------------------------------- |
| Server List       | test_list_dataservers, test_root, test_health                        |
| Server By WebId   | test_dataserver_by_web_id, test_dataserver_not_found                 |
| Point By Path     | test_point_by_path, test_point_not_found                             |
| Point By WebId    | test_point_by_web_id, test_point_by_name_fallback, test_unknown_point_never_500 |
| Current Value     | test_current_value, test_current_value_not_found, test_empty_tag_current_value |
| Historical Value  | test_recorded_range_and_max_count, test_recorded_default_ascending, test_recorded_accepts_timezone_offsets, test_history_order_desc, test_duplicate_timestamps, test_timestamp_modes |
| Write Value       | test_write_then_read, test_write_no_content_mode, test_type_error_returns_400, test_string_point_type, test_int_point_accepts_integer, test_int_point_rejects_string |
| Batch Write       | test_batch_write, test_batch_api                                     |
| Unknown Point     | test_point_not_found, test_write_unknown_point                       |
| Empty History     | test_empty_tag_history_is_empty_list                                 |
| Bad Quality       | test_bad_quality_tag, test_set_quality                               |
| Authentication    | test_auth.py (6 cases)                                               |
| Delay             | test_delay, test_delay_bounds                                        |
| HTTP 500 / 503    | test_force_status, test_force_status_503, test_mock_api_not_affected_by_faults |
| Invalid JSON      | test_invalid_json                                                    |
| Omit Fields       | test_omit_fields                                                     |
| Endpoint Fault    | test_endpoint_fault, test_endpoint_fault_delay_and_times             |
| Reset             | test_reset_clears_faults, test_reset_restores_quality_and_data, test_reset_disables_auth |
| Request History   | test_request_history, test_clear_request_history                     |
| Large History     | test_large_history (100,000 points)                                  |
| TCP close/reset/hang | test_tcp_close, test_tcp_reset, test_tcp_hang                     |

## Smoke Test 结果

Command: `powershell -ExecutionPolicy Bypass -File scripts/smoke_test.ps1`
(server running via `python -m app.main --port 8080`)

```text
[PASS] health
[PASS] dataserver
[PASS] point
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

## Performance Result

| Scenario            | Result                                             |
| ------------------- | -------------------------------------------------- |
| 100,000 point history | `recorded?maxCount=100000` returned HTTP 200 with all 100,000 items; no crash/OOM |
| Concurrent clients  | FastAPI/Uvicorn async stack; no blocking global lock on read paths |

Note: performance is validated only for tooling stability, not production parity.

## 部署验证

| Item            | Result                                                       |
| --------------- | ------------------------------------------------------------ |
| Windows run     | `python -m app.main` serves `/health` = `{"status":"ok"}`    |
| SQLite restart  | Written value 424.2 survived process restart                  |
| TCP Fault Server| `--mode close` accepts then returns EOF (`recv == b''`)       |
| HTTPS           | Supported via `--ssl-keyfile/--ssl-certfile` (instructions in README) |
| Docker          | Dockerfile + docker-compose.yml + healthcheck provided; Docker CLI unavailable on this machine so not executed |

## 已知限制

- Docker Compose was not executed on this build machine (no Docker CLI available);
  configuration and healthcheck are provided and follow the spec.
- `scripts/smoke_test.sh` requires a POSIX shell. WSL was unavailable on this Windows
  host, so the provided PowerShell smoke test was used for verification.
- HTTPS acceptance was verified by configuration/startup path only; certificate
  generation requires `openssl` and was not exercised end-to-end on this machine.
- AF SDK / PI SDK / AF data model are intentionally not implemented.
- TCP 5450 does not emulate any PI protocol; network faults only.

## 最终判定

```text
FINAL RESULT = PASS
```
