# Unison Deployment Guide

This document summarizes the current deployment posture for UnisonOS.

## Supported Milestone 1 Path

The supported Milestone 1 installation target is:

- Ubuntu 24.04 native
- x86_64 hardware

Use:

- [Ubuntu Native Installation](ubuntu-native.md)

This is the only install path that should be treated as the production-track reference.

## Evaluation Channels

These channels remain useful for testing, demos, packaging work, and documentation validation:

- WSL2 images
- Linux VM images
- bare-metal installer images

They are evaluation channels, not the primary supported install contract.

## Developer Path

For multi-service development and integration work, the compose/devstack path remains relevant:

- repository root README
- `make up`
- `make health`

That path is for contributors and engineering work. It is not the same as the end-user installation path.

## Install Behavior

Current installer behavior is intentionally conservative:

- the installer seeds `/etc/unison/platform.env` if needed
- the installer installs `unison-platform.service`
- the installer pulls images
- the installer does not start the platform if template or development defaults remain in the environment file

Before first start, operators must replace at least:

- `UNISON_ENV=development`
- `POSTGRES_PASSWORD=unison_password`
- `JWT_SECRET_KEY=your-super-secret-jwt-key-change-in-production`

Then start:

```bash
sudo unisonctl start
sudo unisonctl status
```

Operational commands after install:

```bash
sudo unisonctl health
sudo unisonctl logs
sudo unisonctl doctor
sudo unisonctl recover
```

## Choosing A Path

Choose native Ubuntu when:

- you want the intended Milestone 1 product experience
- you are validating installability and first boot
- you are preparing a real user-facing environment

Choose WSL2, VM, or bare metal evaluation artifacts when:

- you are testing packaging
- you are validating evaluator flows
- you need a disposable environment

Choose the compose/dev path when:

- you are developing services
- you need faster iteration
- you are working on integration or debugging
