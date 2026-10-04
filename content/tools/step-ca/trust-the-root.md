# Trusting the fleet's root certificate

This page makes a Linux machine of your own, and the browsers on it, accept certificates from the fleet's CA. You do it once for each machine that will reach a service whose certificate comes from step-ca. The fleet's own hosts get the root another way. See [Give the fleet the root certificate](../../fleet-bootstrap/hosts/pk01-certificates.md#trust).

Status: written, not yet run. See [Not yet confirmed](#unconfirmed).

Nothing in the fleet presents a certificate from this CA yet, so today the change has no visible effect. Every name is served with a Let's Encrypt certificate. See [Which certificate a name gets](index.md#which-certificate). The page is here for the day an internal name moves to step-ca.

The change is made on the client alone. Nothing in a repo changes and nothing is deployed.

## Prerequisites

- pk01 is built, and its root key is offline. See [Certificates (pk01)](../../fleet-bootstrap/hosts/pk01-certificates.md#root-key).
- The root certificate's fingerprint, which you stored with the key's backup. See [Copy the key out](../../fleet-bootstrap/hosts/pk01-certificates.md#root-key-copy).
- A client on the internal network that resolves `pki.home.myah-mitchell.com`, with `curl`, `openssl`, and sudo.

## Placeholders

| Placeholder | Value |
| --- | --- |
| `<fingerprint>` | The root certificate's SHA-256 fingerprint from the backup, 64 hexadecimal characters |

## 1. Fetch the root certificate {#fetch}

Download the root from the CA:

```bash
curl -o root_ca.crt https://pki.home.myah-mitchell.com/roots.pem
```

The file starts with the line `-----BEGIN CERTIFICATE-----`. Add `-k` while pk01 is in bootstrap mode, where Traefik serves a self-signed certificate.

If the CA cannot be reached, copy `root_ca.crt` from the place you kept it within reach when the key went offline. The file is public, and how it travels does not matter, because the next step checks it.

## 2. Check its fingerprint {#fingerprint}

Print the SHA-256 fingerprint of the file you fetched:

```bash
openssl x509 -in root_ca.crt -noout -fingerprint -sha256 \
  | tr -d ':' | tr 'A-F' 'a-f'
```

```text
sha256 fingerprint=<fingerprint>
```

Compare the value with the one from the backup, character for character. Stop if they differ, and do not install the file.

The two `tr` commands put the output in the form `step certificate fingerprint` printed it in: lower case with no colons. With the `step` command line on the client, `step certificate fingerprint root_ca.crt` prints that form directly.

<details>
<summary>Background: why the fingerprint and not the download</summary>

A [trusted root](index.md#trust) lets its holder make a certificate for any name that this machine will accept. The download proves little by itself: in bootstrap mode it is fetched with the check turned off, and in normal mode it is vouched for by Let's Encrypt, which says only that the server holds the name.

The fingerprint was taken from the CA's own files on pk01 on the day the root was made, and kept offline since. A file that matches it is that certificate, whatever path it took.

</details>

## 3. Install it in the system store {#install}

Use the section for the client's distribution. Both end with the certificate in the store that `curl`, `openssl`, and most other programs read.

### Debian and Ubuntu {#install-debian}

```bash
sudo cp root_ca.crt /usr/local/share/ca-certificates/home-internal-ca.crt
sudo update-ca-certificates
```

The second command reports `1 added`. The file needs the extension `.crt`, or the command passes over it.

### Fedora and its relatives {#install-fedora}

```bash
sudo cp root_ca.crt /etc/pki/ca-trust/source/anchors/home-internal-ca.crt
sudo update-ca-trust
```

The second command prints nothing when it succeeds.

## 4. Verify {#verify}

Ask openssl to check the root against the system store:

```bash
openssl verify root_ca.crt
```

```text
root_ca.crt: OK
```

Before step 3 the same command fails with a message about a self-signed certificate, so `OK` shows that the store now holds the root.

## 5. Add it to the browsers {#browsers}

A browser may keep a store of its own, apart from the system's.

### Firefox {#firefox}

1. Open *Settings > Privacy & Security*, scroll to *Certificates*, and click **View Certificates**.
2. On the *Authorities* tab, click **Import** and choose `root_ca.crt`.
3. Tick **Trust this CA to identify websites** and click **OK**. The CA's name appears in the *Authorities* list.

### Chrome and Chromium {#chrome}

Chrome on Linux reads the user's NSS database. Add the root to it with `certutil`, which is in the package `libnss3-tools` on Debian and Ubuntu and `nss-tools` on Fedora:

```bash
certutil -d sql:$HOME/.pki/nssdb -A -t "C,," -n "Home Internal CA" -i root_ca.crt
```

List the database to check:

```bash
certutil -d sql:$HOME/.pki/nssdb -L
```

The listing shows `Home Internal CA` with the trust flags `C,,`. Restart the browser.

## Removing it {#remove}

Delete the file you copied in [step 3](#install) and run the same update command again. In Firefox, select the CA on the *Authorities* tab and click **Delete or Distrust**. For Chrome, run `certutil -d sql:$HOME/.pki/nssdb -D -n "Home Internal CA"`.

Remove the root from every client when the CA is replaced, since a client keeps trusting an old root until someone takes it out.

## What's next

Nothing more is needed on the client. A program in a container does not see the system store. See [Trusting the root](index.md#trust).

## Not yet confirmed {#unconfirmed}

No part of this page has been run. pk01 has not been built.

- `/roots.pem` answering through Traefik at `pki.home.myah-mitchell.com`. The path is from step-ca's documentation, and Traefik's rule for the name matches every path.
- The fingerprint from `openssl` matching the one `step certificate fingerprint` prints, after the two `tr` commands.
- The wording of `update-ca-certificates` and `openssl verify` output on a current distribution.
- Firefox's labels: *View Certificates*, *Authorities*, *Import*, *Trust this CA to identify websites*, and *Delete or Distrust*.
- Chrome reading `~/.pki/nssdb` in its current release. Chrome has moved to a root store of its own for public CAs, and its handling of locally added roots has changed between versions.
- A client accepting a leaf from this CA after these steps. Nothing presents one yet.
