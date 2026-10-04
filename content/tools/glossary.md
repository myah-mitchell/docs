# Glossary

The terms the fleet's pages keep using, each in a sentence or two, with a link to the page that explains it in full. The entries are in alphabetical order. A term that belongs to one tool links to that tool's [primer](index.md).

Several tools use the same word for different things. Where that happens, the entry says which meaning these pages intend.

## ACME {#acme}

The protocol a machine uses to ask a certificate authority for a certificate without a person involved. The requester proves it controls a name by passing a challenge. Traefik speaks ACME to Let's Encrypt, and step-ca can answer it inside the fleet. See [ACME in the step-ca primer](step-ca/index.md#acme).

## Age key {#age-key}

A key pair made by the tool age. The public half encrypts and is safe to commit. The private half decrypts and is never committed. sops uses age keys to encrypt the private repo's secrets. See [the age key pair](sops/index.md#age-key) and [the three kinds of key](../fleet-bootstrap/concepts/secrets-with-sops.md#keys).

## Auth chain {#auth-chain}

The named list of Traefik middlewares a route passes through before the request reaches its container. The fleet has two: `chain-authentik@file` asks for a sign-in, and `chain-no-auth@file` does not. See [the two chains](traefik/index.md#chains).

## Bootstrap mode {#bootstrap-mode}

The state the first hosts are built in, before the sign-in on id01, the telemetry store on ci01, and the hub on tf01 exist. A host in bootstrap mode leaves those three out. The whole fleet leaves the mode together. See [Bootstrap mode](../fleet-bootstrap/concepts/bootstrap-mode.md).

## Bouncer {#bouncer}

In CrowdSec, the part that enforces a ban. CrowdSec itself only decides which addresses to ban. A bouncer asks it for the list and blocks them, in a firewall or a proxy. See [bouncers](crowdsec/index.md#bouncers).

## Check mode {#check-mode}

A way of running Ansible that reports what a run would change without changing it. On the command line it is `--check`, and Semaphore calls it *Dry Run*. See [check mode in the Ansible primer](ansible/index.md#check-mode) and [what a check run does](../fleet-bootstrap/concepts/how-a-host-is-built.md#check).

## Cloud-init {#cloud-init}

A standard way to hand a new VM its first settings. Proxmox writes them to a small extra drive, and the VM reads the drive as it boots. The fleet uses it for one thing: giving the installer the VM's address. See [the blank VM](opentofu/index.md#blank-vm).

## Control node {#control-node}

The machine a run starts from. It does the work and reaches out to the hosts, which need nothing installed for it. It is a shell on your own machine during the foundation, and Semaphore's container on ci01 after the handover. See [the control node in the Ansible primer](ansible/index.md#control-node).

## Core and Periphery {#core-and-periphery}

Komodo's two halves. Core is the server on km01, with the web interface and the database. Periphery is the agent on every host that does what Core asks, such as deploying a Stack. Periphery dials out to Core, so Core needs no way in to a host. See [Core and Periphery](komodo/index.md#core-and-periphery).

## Deploy key {#deploy-key}

The age key that automation decrypts secrets with. The control shell and Semaphore hold its private half. It opens every secrets file, so treat it as able to take over the fleet. It is not an SSH key, and it is not a GitHub deploy key. See [the three kinds of key](../fleet-bootstrap/concepts/secrets-with-sops.md#keys).

## DMZ {#dmz}

A second network for the hosts that take traffic from the internet. The router's firewall decides what may pass between it and the internal network, the Servers VLAN, so a break-in on a DMZ host does not reach everything else. bh01 and mx01 are on it. See [The network and DNS the fleet expects](../fleet-bootstrap/concepts/the-network.md#networks).

## DNS-01 {#dns-01}

An ACME challenge in which the requester proves it controls a name by creating a DNS record. It works for a host the internet cannot reach, and it is the only challenge that can issue a wildcard certificate. Traefik uses it with Cloudflare's API. See [ACME in the step-ca primer](step-ca/index.md#acme) and [TLS in the Traefik primer](traefik/index.md#tls).

## Exporter {#exporter}

A small program that publishes measurements about something as a web page of numbers, for a collector to read on a schedule. Each host runs a node exporter for the machine itself. See [scraping and exporters](victoriametrics/index.md#scraping).

## Flake {#flake}

A Nix project with a fixed layout: a `flake.nix` that names its inputs and outputs, and a `flake.lock` that pins every input to an exact version. The fleet-nixos repo is a flake, and every host's operating system is one of its outputs. See [flakes and the lock file](nixos/index.md#flakes) and [The NixOS flake](../fleet-bootstrap/concepts/nixos-flake.md).

## Forward auth {#forward-auth}

A way for a proxy to ask another service whether to let a request through. Traefik asks Authentik before it passes a request on. Authentik answers yes, or sends the browser to a sign-in page. The application behind it needs no sign-in code of its own. See [forward auth in the Authentik primer](authentik/index.md#forward-auth).

## Generation {#generation}

One complete build of a NixOS system. Every deploy makes a new generation and keeps the earlier ones, so a host can go back to the one before. See [the system and its generations](nixos/index.md#generations).

## Guest agent {#guest-agent}

A small service inside a VM that answers questions from Proxmox, such as which addresses the VM has. OpenTofu waits for it to report an address, and the install reads the installer's host key through it. See [the blank VM](opentofu/index.md#blank-vm).

## Host key {#host-key}

The SSH key pair that identifies a machine, as opposed to a person. A client checks it to know it has reached the right host. The fleet makes each host's key before the host exists and keeps it encrypted in the private repo, so a rebuilt host keeps its identity. See [the host's SSH keys](../fleet-bootstrap/concepts/secrets-with-sops.md#host-keys).

## Hub {#hub}

The Traefik on tf01. It learns every route the other hosts publish and forwards requests to the host that serves them, so one address can answer for the whole fleet. See [the hub on tf01](traefik/index.md#hub).

## Idempotent {#idempotent}

Safe to repeat. An idempotent step checks what exists and changes only what differs, so running it a second time does nothing. Every stage of a run is built this way. See [idempotence in the Ansible primer](ansible/index.md#idempotence).

## Installer ISO {#installer-iso}

A disk image a blank VM boots from. It is a small NixOS system that waits for the run to log in and install the real one. You build it once from the flake and upload it to Proxmox. See [Proxmox and the installer ISO](../fleet-bootstrap/foundation/proxmox-and-installer.md).

## Inventory {#inventory}

The list of hosts Ansible manages, with the values that belong to each. In the fleet it is `hosts.yml` in the private repo. Semaphore also has an object called an Inventory, which only points at that file. See [the inventory in the Ansible primer](ansible/index.md#inventory) and [describing a host](../fleet-bootstrap/concepts/fleet-private.md#describe).

## Middleware {#middleware}

In Traefik, a step a request passes through between the router and the container, such as adding headers or asking for a sign-in. A chain is a named list of middlewares. See [middlewares](traefik/index.md#middlewares).

## Onboarding key {#onboarding-key}

A secret a new host's Periphery shows to Komodo Core the first time it connects, to prove it belongs to the fleet. A rebuilt host that keeps its disk does not need it again. See [the onboarding key](komodo/index.md#onboarding-key).

## Outpost {#outpost}

The part of Authentik that answers a proxy's forward auth questions. The fleet uses the embedded outpost, which runs inside Authentik's own server container. See [the outpost](authentik/index.md#outpost).

## Persistent disk {#persistent-disk}

The disk that holds a host's data: its containers' files and the few system files that must outlive a rebuild. A rebuild wipes the system disk and leaves this one alone. See [the persistent disk](../fleet-bootstrap/concepts/host-layout.md#persist).

## Private repo {#private-repo}

The one git repo that holds what makes the fleet yours: which hosts exist, their addresses, and their secrets, encrypted. The other four repos are public and hold no fact about your fleet. See [The private repo](../fleet-bootstrap/concepts/fleet-private.md).

## Project {#project}

Two tools use this word. A Compose project is one set of containers that Compose starts and stops together, and its name prefixes their networks and volumes. A Semaphore Project is the container for everything Semaphore needs to run the fleet's playbooks. See [projects in the Compose primer](docker-compose/index.md#project) and [the Project in the Semaphore primer](semaphore/index.md#project).

## Provisioner {#provisioner}

In step-ca, one configured way of asking the authority for a certificate, with its own rules for who may ask. ACME is one kind. See [provisioners](step-ca/index.md#provisioners).

## Proxmox {#proxmox}

Proxmox VE, the hypervisor: the operating system on the physical machine, which runs the VMs. The fleet never configures a VM in its web interface. OpenTofu does that through Proxmox's API. See [Proxmox and the installer ISO](../fleet-bootstrap/foundation/proxmox-and-installer.md).

## Relay {#relay}

A mail server that accepts a message only to pass it on. ci01 runs one so that every service in the fleet can send mail through a single place. See [the relay in the Stalwart primer](stalwart/index.md#relay).

## Resource Sync {#resource-sync}

The Komodo feature that reads resource definitions from files in git and makes Komodo match them. The fleet's Servers and Stacks are defined this way, in `komodo/` in the private repo, and never by hand in the interface. See [Resource Sync](komodo/index.md#resource-sync).

## Route {#route}

A rule in Traefik that sends requests for one hostname to one container. Traefik calls the rule a router and the destination a service. A container declares its route with labels in its compose file. See [routers in the Traefik primer](traefik/index.md#routers).

## Run {#run}

One execution of `site.yml` for the hosts you name. It has four stages: create the VM, wait for it, install and configure NixOS, and sync its Stacks in Komodo. See [How a host is built](../fleet-bootstrap/concepts/how-a-host-is-built.md).

## Server {#server}

In Komodo, a host that Core manages through its Periphery. Written with a capital in these pages when it means Komodo's object. See [Server](komodo/index.md#server).

## Stack {#stack}

A set of containers deployed together from one compose file. In fleet-stacks a stack is a folder under `stacks/`. In Komodo a Stack, with a capital, is the resource that deploys that folder to one Server. See [Stack in the Komodo primer](komodo/index.md#stack) and [the three layers](docker-compose/index.md#layers).

## State {#state}

Two tools use this word. OpenTofu's state is its record of what it has created, which it compares with your files to decide what to change. On a NixOS host, state is the data the configuration does not describe, which is what the persistent disk is for. See [state in the OpenTofu primer](opentofu/index.md#state) and [state in the NixOS primer](nixos/index.md#state).

## Target {#target}

The variable that names which hosts a run acts on. Every run of `site.yml` must be given one. See [Running part of a run](ansible/run-part-of-a-run.md#target).

## Telemetry {#telemetry}

The measurements and logs a host sends away to be stored and searched: metrics, which are numbers over time, and logs, which are lines of text. Every host sends both to ci01. See [metrics, logs, and traces](victoriametrics/index.md#metrics-logs-traces).

## Template {#template}

In Semaphore, a saved description of one job: which playbook, from which repository, against which inventory, with which variables. Starting a Template makes a Task. See [Task Template](semaphore/index.md#task-template).

## tfvars {#tfvars}

A file of values for OpenTofu's variables. The fleet's is `opentofu/prod.tfvars` in the private repo, and it holds one entry for each VM. See [variables and tfvars files](opentofu/index.md#variables) and [a VM's entry, field by field](opentofu/index.md#vm-entry).

## Tunnel {#tunnel}

A connection bh01 opens outward to Cloudflare and keeps open. Requests from the internet arrive at Cloudflare and travel back down it, so the router needs no inbound port open. See [the edge on bh01](traefik/index.md#edge).

## User namespace {#user-namespace}

A Linux feature that gives a container its own range of user IDs. Root inside the container is an unprivileged user on the host, so files the container writes belong to a high-numbered ID. See [why 100000 and 101000](../fleet-bootstrap/concepts/host-layout.md#uid-offsets).

## Variable Group {#variable-group}

In Semaphore, a named set of variables and secrets that a Template hands to its runs. The fleet keeps one, and it holds what the control shell keeps in its environment. See [Variable Group](semaphore/index.md#variable-group).

## Variables and Secrets {#variables-and-secrets}

In Komodo, values stored once in Core and filled in to a Stack's environment wherever `[[NAME]]` appears. A Secret is a Variable whose value the interface hides. See [Variables and Secrets in the Komodo primer](komodo/index.md#variables-and-secrets) and [the full list](../fleet-bootstrap/concepts/variables-and-secrets.md).

## VLAN {#vlan}

A virtual LAN: a way to run several separate networks over the same switches and cables by tagging each frame with a number. The fleet's internal network is VLAN 7, named Servers, and its DMZ is VLAN 8. The Proxmox host's address is on MGMT, VLAN 1, and your own machine is on Users, VLAN 4. See [The network and DNS the fleet expects](../fleet-bootstrap/concepts/the-network.md#networks).

## vmauth {#vmauth}

A small proxy from the VictoriaMetrics project. It gives the agents on every host one address to send to, and passes each request to the right store by its path. See [vmauth](victoriametrics/index.md#vmauth).
