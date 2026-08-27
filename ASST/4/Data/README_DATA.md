# Sample Awareness Data

`calendar.json`, `emails.json`, and `contacts.json` are **sample fixture files
written for this workstream**.

They are not a live mailbox, not a real calendar, and not real contacts. No
Outlook, Exchange, or Microsoft Graph connection exists in this component.

They exist so Assistant Outlook runs and is testable with no credentials and no
network. To point the component at different fixture data, use `--data-root` or
set `ASSISTANT_OUTLOOK_DATA`.
