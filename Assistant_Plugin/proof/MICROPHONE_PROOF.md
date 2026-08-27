# JOE - Microphone Test and Diagnostics

**Run:** 2026-08-27T17:34:54+00:00

No raw audio is retained. Only recognized text and outcomes.

## What JOE records from

| | |
| --- | --- |
| Device in use | Headset |
| Status | connected and available |
| Preference | (none - Windows default) |
| Preference honoured | True |
| Bluetooth headset known | True |
| Bluetooth headset connected | True |

> JOE records from the Windows default input device. Windows Speech Recognition offers no way to bind to a chosen device, so a preference here is remembered and reported, not enforced.

## Recording devices Windows knows about

| Device | Status | Notes |
| --- | --- | --- |
| Stereo Mix | disabled in Windows | loopback - never used, it would hear JOE's own output |
| Internal Microphone | connected and available | - |
| Line In | not connected | - |
| External Microphone | not connected | - |
| Headset | connected and available | **JOE records from this one**, bluetooth |

## Live test

**PASS - JOE heard Mike, and did not hear itself.**

| | |
| --- | --- |
| Device | Headset |
| Expected phrase | Joe can you hear me through the headset |
| Recognized text | This is the headset. Can you hear me through the headset, Joe? |
| Word match | 100% |
| JOE heard itself | False |
