# GitHub Profile Setup Checklist (`Xylus` / `@xtreame-x`)

GitHub displays the `README.md` from a special repository with the exact same name as your username: **`xtreame-x/xtreame-x`**.

---

## Step 1 — Create Your Profile Repo & Push

1. Open [github.com/new?name=xtreame-x&visibility=public](https://github.com/new?name=xtreame-x&visibility=public) (leave README, `.gitignore`, and license **unchecked**) and click **Create repository**.
2. Push this local repo's `main` branch (`origin` is already configured to `https://github.com/xtreame-x/xtreame-x.git`):
   ```bash
   git push -u origin main
   ```

---

## Step 2 — Phase 3: Enable & Run the Contribution Snake Action

> **Do NOT skip this order:** The `output` branch does not exist until the Action runs green for the first time. Enable the workflow permissions right after pushing, trigger the Action once, and verify the green checkmark before expecting the snake graphic to render.

1. Open **`https://github.com/xtreame-x/xtreame-x/settings/actions`** (⚠️ **this repository's Settings**, *not* your personal GitHub account Settings).
2. Scroll down to **Workflow permissions**, select **Read and write permissions**, and click **Save**.
3. Go to the **Actions** tab → **Generate Contribution Snake** → click **Run workflow**.
4. Once it turns **green**, the `output` branch is created and your dark/light snake SVGs (`#2d3343` dark grid cells) will appear automatically in `README.md`.

---

## Step 3 — Phase 2: Self-Host `github-readme-stats` (Vercel)

Public instances of `github-readme-stats` are shared by thousands of users and constantly hit `"API rate limit exceeded"`. Self-hosting on Vercel's free Hobby tier gives you your own private quota:

1. **Create a GitHub Classic Token:**
   - Go to **GitHub Account Settings** → **Developer settings** → **Personal access tokens** → **Tokens (classic)** → **Generate new token (classic)**.
   - Check the **`repo`** scope.
   - Set Expiration to **No expiration**.
   - **IMPORTANT:** Copy the token immediately and **never paste it publicly or commit it to any repo**.
2. **Fork the Stats Repo:**
   - Open [`anuraghazra/github-readme-stats`](https://github.com/anuraghazra/github-readme-stats) and click **Fork**.
3. **Deploy on Vercel:**
   - Go to [vercel.com](https://vercel.com), sign up / log in with GitHub (**Hobby — Free**).
   - Click **Add New... → Project** and import your forked `github-readme-stats` repo.
   - Expand **Environment Variables**, add:
     - Name: `PAT_1`
     - Value: *(paste your GitHub classic token)*
   - Click **Deploy**.
4. **Enable the Stats Cards in `README.md`:**
   - Uncomment the stats `<p align="center">` block in `README.md` and replace `YOUR_VERCEL_URL` with your deployed domain (e.g. `github-readme-stats-xyz.vercel.app`).

> **Why `hide_rank=true` is kept:** GitHub Stats' letter rank (`A+`, `S`, etc.) is heavily weighted toward public repository **stars** rather than actual learning, private commits, or problem-solving—making it misleading for newer or focused accounts.

---

## Step 4 — Phase 4: Social Badges Notes

- **Email badge** is already wired to `xtreame.1825@gmail.com` so anyone with Physics, Math, or Logic ideas can reach out with one click.
- **Warning if you add a LinkedIn badge later:** Shields.io has a known bug where the LinkedIn icon silently disappears if you override `&logoColor=` with anything other than LinkedIn's brand blue (`0A66C2`). Either keep `logoColor=0A66C2` or embed the glyph as a base64 `data:image/svg+xml` URI.
- **No GitHub badge:** Intentionally skipped because visitors are already on your GitHub profile.

---

## Updating the Animated Banner Later

The source of truth for your animated banner is [`scripts/build_banner.py`](./scripts/build_banner.py). If you ever change your role, tools, or email, edit `info_rows` inside `scripts/build_banner.py` and re-run:

```bash
python scripts/build_banner.py
```

*(Note: GitHub's Camo/CDN caches assets aggressively. If you push an update and something "didn't change", inspect the raw file directly with `?v=999` — e.g. `https://raw.githubusercontent.com/xtreame-x/xtreame-x/output/github-snake-dark.svg?v=999` — and double-check you're testing in the matching GitHub appearance theme: dark assets only render in dark mode, light assets only in light mode.)*
