# Netman Persian News Video

A free GitHub Actions + FFmpeg pipeline that creates a vertical Persian news video with a Bitcoin 7-day chart, Iran free-market USD quote in toman, crypto/Iran/FX headlines, publisher lead images when available, and Persian narration using the open-source `persian-speech` package.

## Telegram setup

In GitHub: Settings -> Secrets and variables -> Actions -> New repository secret. Add `TELEGRAM_BOT_TOKEN` using the BotFather token. Optionally add `TELEGRAM_CHAT_ID`; otherwise the workflow uses the configured news group chat ID. Never commit the token or paste it into chat.

## Run

Open Actions -> Netman Persian News Video -> Run workflow. The MP4 is uploaded as a workflow artifact even if Telegram credentials are not configured. The workflow is scheduled every six hours.

## Notes

Market data can be delayed or unavailable; missing values are labeled rather than invented. Publisher images are read from article Open Graph metadata when available; otherwise the renderer uses a designed title card. Output is portrait 1080x1920. GitHub Actions usage is subject to the account's current runner-minute policy; check Settings -> Billing and plans -> Actions.
