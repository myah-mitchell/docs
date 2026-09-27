| Key | Reads | Kind | Described under |
| --- | --- | --- | --- |
| `AUTHENTIK_SECRET_KEY` | `AUTHENTIK_SECRET_KEY` | Secret | [Authentik](../concepts/variables-and-secrets.md#authentik) |
| `AUTHENTIK_EMAIL__HOST` | `GLOBAL_EMAIL_HOST` | Variable | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `AUTHENTIK_EMAIL__PORT` | `GLOBAL_EMAIL_PORT` | Variable | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `AUTHENTIK_EMAIL__USERNAME` | `GLOBAL_EMAIL_USER` | Variable | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `AUTHENTIK_EMAIL__PASSWORD` | `GLOBAL_EMAIL_PASS` | Secret | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `AUTHENTIK_EMAIL__USE_TLS` | `GLOBAL_EMAIL_TLS` | Variable | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `AUTHENTIK_EMAIL__USE_SSL` | `GLOBAL_EMAIL_SSL` | Variable | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `AUTHENTIK_EMAIL__FROM` | `GLOBAL_EMAIL_FROM` | Variable | [Mail](../concepts/variables-and-secrets.md#mail-relay) |
| `POSTGRES_USER` | `AUTHENTIK_POSTGRES_USER` | Secret | [Authentik](../concepts/variables-and-secrets.md#authentik) |
| `POSTGRES_PASSWORD` | `AUTHENTIK_POSTGRES_PASSWORD` | Secret | [Authentik](../concepts/variables-and-secrets.md#authentik) |
| `GEOIPUPDATE_ACCOUNT_ID` | `GLOBAL_GEOIPUPDATE_ACCOUNT_ID` | Secret | [Authentik](../concepts/variables-and-secrets.md#authentik) |
| `GEOIPUPDATE_LICENSE_KEY` | `GLOBAL_GEOIPUPDATE_LICENSE_KEY` | Secret | [Authentik](../concepts/variables-and-secrets.md#authentik) |

It also reads the 19 [operational defaults](../concepts/variables-and-secrets.md#operational), as every stack does.
