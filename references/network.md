# Network behavior: curl, Clash Verge, and TUN

## Default policy

This Skill uses curl/curl.exe for both Agnes API requests and generated-file downloads. It keeps HTTP/1.1 enabled but does not force either direct access or proxy access.

In particular, the Skill does not add:

```text
--noproxy "*"
```

Therefore, the connection path is left to the current environment and routing configuration.

## Clash Verge system-proxy mode

The Skill does not override proxy-related environment variables or curl configuration. When curl is configured to use a proxy, that proxy remains effective. When curl is not configured to use one, the request follows the normal network route.

The Windows graphical “system proxy” and curl's own proxy configuration are not guaranteed to be identical. `urllib.request.getproxies()` is displayed only as diagnostic information; it does not prove that curl is using the same proxy. The actual curl request result is the source of truth.

No `--noproxy "*"` flag is injected. Likewise, the Skill does not inject `--proxy`. This is intentional: the default mode does not force either direct access or proxy access.

## TUN mode

Clash TUN works below the HTTP client, so routing rules continue to apply automatically. The Skill does not attempt to bypass TUN.

If Agnes should be proxied or direct-routed under TUN, configure that choice in Clash Verge rules. Relevant domains include:

- `apihub.agnes-ai.com`
- `*.agnes-ai.com`
- `*.agnes-ai.space`

The output domain is commonly `platform-outputs.agnes-ai.space`.

## Diagnostic

```powershell
& "$env:USERPROFILE\.workbuddy\skills\agnes-image-video-generator\scripts\agnes.ps1" diagnose
```

The report shows:

- the curl executable;
- resolved API addresses;
- proxy settings visible to Python, for reference;
- API-key presence without displaying the key;
- the HTTP status returned through curl's current routing path.
