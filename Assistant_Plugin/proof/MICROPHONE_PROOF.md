# JOE - Microphone Test and Diagnostics

**Run:** 2026-08-27T16:42:04+00:00

No raw audio is retained. Only recognized text and outcomes.

## What JOE records from

| | |
| --- | --- |
| Device in use | Internal Microphone |
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
| Internal Microphone | connected and available | **JOE records from this one** |
| Line In | not connected | - |
| External Microphone | not connected | - |
| Headset | connected and available | bluetooth |

## Live test

**PASS - JOE heard Mike, and did not hear itself.**

| | |
| --- | --- |
| Device | Internal Microphone |
| Expected phrase | Joe can you hear me through the headset |
| Recognized text | Hear me through the headset |
| Word match | 62% |
| JOE heard itself | False |
