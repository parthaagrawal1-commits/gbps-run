# How this repo deploys

- Repo root = the live site (what Hostinger serves from public_html).
- `_src/` holds the generator. `.htaccess` returns 404 for `/_src/` and `/.git/`.
- To change the site: edit `_src/template.html` or `_src/build.py`, then from `_src/` run
  `python3 build.py` and copy `site/*` to the repo root (`cp -r site/. ..`), commit, push.
- Hostinger (hPanel → Advanced → Git) pulls `main` into public_html; the GitHub webhook
  triggers an automatic redeploy on every push.
