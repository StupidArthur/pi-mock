$ErrorActionPreference = "Stop"
$Base = if ($env:BASE) { $env:BASE } else { "http://127.0.0.1:8080" }
$Pi = "$Base/piwebapi"
$Mock = "$Base/mock"

function Pass($name) { Write-Host "[PASS] $name" }
function Fail($name) { Write-Host "[FAIL] $name"; exit 1 }

Write-Host "== Mock PI Server smoke test =="
Write-Host "BASE=$Base"

if ((Invoke-RestMethod "$Base/health").status -eq "ok") { Pass "health" } else { Fail "health" }

$servers = Invoke-RestMethod "$Pi/dataservers"
if ($servers.Items[0].WebId -eq "SERVER_TEST_PI") { Pass "dataserver" } else { Fail "dataserver" }

$point = Invoke-RestMethod "$Pi/points?path=%5C%5CTEST-PI%5Ctemperature"
if ($point.Name -eq "temperature") { Pass "point" } else { Fail "point" }
$webId = $point.WebId

$value = Invoke-RestMethod "$Pi/streams/$webId/value"
if ($null -ne $value.Value) { Pass "current value" } else { Fail "current value" }

$gen = Invoke-RestMethod -Method Post "$Mock/data/generate" -ContentType "application/json" `
  -Body '{"tag":"temperature","start":"2026-01-01T00:00:00Z","count":60,"interval_ms":60000,"generator":"sin"}'
if ($gen.Generated -eq 60) { Pass "generate" } else { Fail "generate" }

$history = Invoke-RestMethod "$Pi/streams/$webId/recorded?maxCount=10"
if ($history.Items.Count -gt 0) { Pass "history" } else { Fail "history" }

Invoke-RestMethod -Method Post "$Pi/streams/$webId/value" -ContentType "application/json" `
  -Body '{"Timestamp":"2026-09-18T11:00:00Z","Value":66.6}' | Out-Null
Pass "write"

$after = Invoke-RestMethod "$Pi/streams/$webId/value"
if ($after.Value -eq 66.6) { Pass "read-after-write" } else { Fail "read-after-write" }

Invoke-RestMethod -Method Post "$Mock/config" -ContentType "application/json" `
  -Body '{"force_status":500}' | Out-Null
try {
  Invoke-RestMethod "$Pi/dataservers" | Out-Null
  Fail "fault force_status"
} catch {
  if ($_.Exception.Response.StatusCode.value__ -eq 500) { Pass "fault force_status" } else { Fail "fault force_status" }
}
$mockStatus = (Invoke-WebRequest "$Mock/config" -UseBasicParsing).StatusCode
if ($mockStatus -eq 200) { Pass "mock isolation" } else { Fail "mock isolation" }

Invoke-RestMethod -Method Post "$Mock/reset" | Out-Null
Pass "reset"

$post = (Invoke-WebRequest "$Pi/dataservers" -UseBasicParsing).StatusCode
if ($post -eq 200) { Pass "post-reset" } else { Fail "post-reset" }

Write-Host "Mock PI Server smoke test PASSED"
