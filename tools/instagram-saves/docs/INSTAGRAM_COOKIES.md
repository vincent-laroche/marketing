# Instagram Cookies

This project uses your own logged-in browser session cookies to read your saved Instagram posts locally. Treat these cookies like passwords.

## Required Values

Store these in `.env`:

- `INSTAGRAM_SESSIONID`
- `INSTAGRAM_CSRFTOKEN`
- `INSTAGRAM_DS_USER_ID`
- `INSTAGRAM_MID`
- `INSTAGRAM_IG_DID`

`SESSIONID`, `CSRFTOKEN`, and `DS_USER_ID` are required for sync. The others help make the browser-session request look normal.

## Rules

- Do not commit `.env`.
- Do not paste cookies into chat, docs, screenshots, or logs.
- Replace cookies when Instagram logs you out or expires the session.
- If Instagram challenges, blocks, or rate-limits access, stop and review in the browser.
- The script does not try to bypass CAPTCHA, account locks, private access restrictions, or security checks.

## Behavior

The client only reads saved posts. It does not post, comment, DM, follow, unfollow, delete, publish, or modify Instagram content.
