# Muffled Minds — Website

Static one-page site for the Muffled Minds podcast, built from the YouTube channel and social profiles.

## Local preview

```
python3 -m http.server 8765
```

Then open http://localhost:8765

## Deploy on GitHub Pages

1. Push this repo to GitHub (already done if you used the assistant to create it).
2. In the repo, go to **Settings → Pages**.
3. Under "Build and deployment", set Source to **Deploy from a branch**, branch `main`, folder `/ (root)`.
4. Under "Custom domain", enter `muffledminds.com` and save (this repo already includes a `CNAME` file with that value).

## Point muffledminds.com (GoDaddy) at GitHub Pages

In GoDaddy → your domain → **DNS Management**, add/edit these records:

| Type  | Name | Value                  |
|-------|------|-------------------------|
| A     | @    | 185.199.108.153         |
| A     | @    | 185.199.109.153         |
| A     | @    | 185.199.110.153         |
| A     | @    | 185.199.111.153         |
| CNAME | www  | `<your-github-username>.github.io` |

Remove any existing `A`/`CNAME`/parking records on `@` and `www` first. DNS propagation can take up to a few hours. Once it resolves, check "Enforce HTTPS" in the repo's Pages settings.

## Updating content

Everything lives in `index.html` (content + episode cards), `css/style.css` (styling), and `assets/logo.svg` (logo — swap in your real logo file and update the `src`/`href` references if you'd rather use the original PNG).
