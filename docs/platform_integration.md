# CoreEdge remote integration

CoreEdge is not a Python dependency of EduEdge.

## Site configuration

```json
{
  "edge_platform_mode": "standalone",
  "edge_platform_product": "EduEdge",
  "coreedge_required": false,
  "coreedge_base_url": "",
  "coreedge_tenant_key": "",
  "coreedge_client_id": "",
  "coreedge_client_secret": "",
  "coreedge_fail_closed": false,
  "coreedge_timeout_seconds": 8,
  "coreedge_access_cache_seconds": 300
}
```

Remote endpoint paths are deliberately separate optional keys until the CoreEdge HTTP service contract is finalized:

```json
{
  "coreedge_health_path": "",
  "coreedge_runtime_context_path": "",
  "coreedge_access_decision_path": ""
}
```

## Secret safety

- Credentials remain in site configuration.
- Public APIs return only whether a value is configured.
- Client secrets must never be logged.
- Browser code never receives authentication credentials.

## Expected remote access response

```json
{
  "allowed": true,
  "enforcement_action": "Allow",
  "primary_reason_code": "ACTIVE",
  "reason": "",
  "warnings": []
}
```

The adapter rejects malformed responses rather than guessing.
