| Key | Reads | Kind | Described under |
| --- | --- | --- | --- |
| `CF_API_EMAIL` | `CF_API_EMAIL` | Secret | [Traefik](../concepts/variables-and-secrets.md#traefik) |
| `CF_DNS_API_TOKEN` | `CF_DNS_API_TOKEN` | Secret | [Traefik](../concepts/variables-and-secrets.md#traefik) |
| `LE_EMAIL` | `LE_EMAIL` | Secret | [Traefik](../concepts/variables-and-secrets.md#traefik) |
| `CROWDSEC_LAPI_HOST` | `GLOBAL_CROWDSEC_LAPI_HOST` | Variable | [Traefik](../concepts/variables-and-secrets.md#traefik) |
| `AUTHENTIK_HOST` | `GLOBAL_AUTHENTIK_HOST` | Variable | [Traefik](../concepts/variables-and-secrets.md#traefik) |
| `REDIS_PASSWORD` | `TRAEFIK_KOP_REDIS_PASSWORD` | Secret | [Traefik](../concepts/variables-and-secrets.md#traefik) |
| `REDIS_SERVER` | `TRAEFIK_KOP_REDIS_SERVER` | Secret | [Traefik](../concepts/variables-and-secrets.md#traefik) |

It also reads the 19 [operational defaults](../concepts/variables-and-secrets.md#operational), as every stack does.
