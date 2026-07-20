# CoreEdge remote integration

CoreEdge is not a Python dependency of EduEdge. EduEdge connects to CoreEdge as a remote platform service.

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

Remote contract paths are separate so CoreEdge can version and govern the service endpoints centrally:

```json
{
  "coreedge_health_path": "api/method/coreedge.api.runtime.health",
  "coreedge_runtime_context_path": "api/method/coreedge.api.runtime.get_context",
  "coreedge_access_decision_path": "api/method/coreedge.api.runtime.get_access_decision"
}
```

When `coreedge_required` is enabled, both runtime-context and access-decision contracts are production blockers.

## Product identity inheritance

The EduEdge product name, logo and product code are managed by CoreEdge. Tenants cannot upload or replace the EduEdge product logo from EduEdge Settings.

The CoreEdge runtime-context response may provide identity using either a nested product object or a product-branding object:

```json
{
  "tenant_key": "tenant-001",
  "product": {
    "code": "EduEdge",
    "display_name": "EduEdge",
    "logo": "https://platform.example.com/files/eduedge-mark.svg"
  },
  "product_branding": {
    "name": "EduEdge",
    "logo": "https://platform.example.com/files/eduedge-mark.svg"
  }
}
```

EduEdge caches the normalized runtime identity. If CoreEdge is temporarily unavailable, the last cached identity is used; a new standalone site falls back to the packaged EduEdge mark. School identity and school logo remain on ERPNext Company because those belong to the tenant, not to the product app.

## Secret safety

- Credentials remain in site configuration.
- Public APIs return only whether a value is configured.
- Client secrets must never be logged.
- Browser code never receives authentication credentials.
- CoreEdge product identity is normalized before it is exposed in Frappe boot data.

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

The adapter rejects malformed responses rather than guessing. Mutating resource-page, quick-entry, settings and branch-context actions must pass through the CoreEdge access decision when remote mode is enabled.

## Recommended SaaS topology

For the current EduEdge architecture, each subscribed school should run on a separate Frappe site. The site may contain multiple ERPNext Companies only when they belong to the same subscribed school group. `coreedge_tenant_key` identifies the subscribed tenant in CoreEdge, while EduEdge School Branch controls operational campus scope inside that tenant.

Do not use one shared EduEdge site with unrelated schools separated only by ERPNext Company. The current permission and branch model is strong for branches within one tenant, but it is not a substitute for database-level isolation between unrelated SaaS customers.
