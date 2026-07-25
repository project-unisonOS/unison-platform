# Adaptive maintenance operations

## Support boundary

The supported default is Recommend. You may issue a narrow, revocable grant
for a listed reversible action class and maintenance window. No community
source, model output, administrator role, or recommendation can issue it.

Firmware maintenance, physical changes, purchases, and any action without
verified rollback always require a separate owner procedure.

## Before execution

1. Verify the device, action class, time window, action count, and downtime
   budget on the grant.
2. Verify the artifact signature, compatibility record, and authoritative
   evidence.
3. Create and verify the checkpoint.
4. Confirm the circuit breaker is closed.
5. Stage the canary without replacing the active known-good state.

## Health failure and rollback

If the post-action health gate fails, stop promotion, restore the checkpoint,
record the before and after observations, and emit the receipt. A second
consecutive failure opens the circuit breaker. Do not retry until you review
the receipt and reset the breaker.

For boot failure, firmware failure, power interruption, or restore failure,
follow the Phase 9 recovery procedure and preserve the failed state for
diagnosis. These scenarios remain hardware-validation requirements.

## Source incident

Disable the registry entry, retain hashes and URLs, invalidate derived test
proposals, and compare against authoritative sources. External content never
authorizes rollback or another corrective action.

## Pilot stop conditions

Stop the pilot on cross-person disclosure, unauthorized maintenance,
uncontained artifact execution, an unrecoverable update, excessive alert
burden, or rollback below the approved target. Human review is required before
promoting each automatic action class.
