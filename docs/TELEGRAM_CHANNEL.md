# Telegram Channel Gateway deployment

The Phase 5 Telegram worker uses outbound HTTPS long polling and opens no inbound listener. The comms API is exposed only on the private Compose network; the experience renderer remains the authenticated local control surface. Do not add a host `ports` mapping to either `comms` or `telegram-channel-worker`.

Before enabling the worker:

1. Generate independent random values of at least 32 bytes for `data/keys/channel-root` and `data/keys/channel-workload-secret`; restrict both files to the appliance service account.
2. From an authenticated local admin surface, register workload `unison-comms-channel-gateway` in auth with audience `auth` and the sole scope `channel:bind`, using the exact workload secret.
3. Start the stack, then let each person add an independent bot token and complete pairing from the trusted local renderer.
4. Verify the host firewall exposes no auth or comms port to LAN or WAN. Only outbound TCP 443 to `api.telegram.org` is needed.

The shared `comms_data` volume holds the encrypted credential store, replay cursor, content-free audit records, and encrypted outbound drafts. Back it up only through the encrypted device backup path. Revoking a provider account clears its ciphertext and revokes the auth-owned channel binding, so reconnect requires a fresh pairing.

See the comms repository's `docs/telegram-channel.md` for provider disclosure, failure modes, rotation, and the fake-provider conformance suite.
