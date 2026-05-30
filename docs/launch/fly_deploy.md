# Deploying to Fly.io

Streamlit Community Cloud cannot run the full pipeline because the container has no Docker daemon. Fly.io can, on the paid tier (privileged mode is required for Docker-in-Docker). On the free tier the deployment still works, but it falls back to preview mode just like the Streamlit Cloud build does.

## One-time setup

1. Install the Fly CLI on your laptop:

   ```bash
   curl -L https://fly.io/install.sh | sh
   ```

2. Sign up and authenticate:

   ```bash
   fly auth signup     # or: fly auth login
   ```

3. Pick a unique app name (the `fly.toml` defaults to `auto-dock-it`; if that name is taken, edit the file).

## First deploy (preview mode, free tier)

From the project root:

```bash
fly launch --no-deploy --copy-config --name <your-app-name>   # creates the app
fly secrets set GROQ_API_KEY=<your_key>
fly secrets set GEMINI_API_KEY=<your_key>
fly deploy
```

After about three minutes you get a URL like `https://your-app-name.fly.dev`. It runs the dry-run pipeline (ingest, analyze, generate) because the Docker daemon inside the Fly container is not running.

## Upgrading to the full pipeline (paid tier)

Docker-in-Docker requires privileged containers. On Fly that means a paid plan ($1.94 per month for the smallest VM, or covered by the $5 monthly credit on the launch plan).

1. Edit `fly.toml`, uncomment the `[experimental]` block:

   ```toml
   [experimental]
     privileged = true
   ```

2. Edit the `Dockerfile`, add a startup script that launches the Docker daemon before Streamlit:

   ```dockerfile
   COPY docker-entrypoint.sh /usr/local/bin/
   RUN chmod +x /usr/local/bin/docker-entrypoint.sh
   CMD ["/usr/local/bin/docker-entrypoint.sh"]
   ```

   where `docker-entrypoint.sh` is:

   ```bash
   #!/bin/sh
   set -e
   dockerd-rootless.sh --experimental &
   sleep 3
   exec streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
   ```

   (Note: install `docker-ce-rootless-extras` in the Dockerfile alongside `docker-ce-cli` to use rootless mode.)

3. Redeploy:

   ```bash
   fly deploy
   ```

## Custom domain

Once the `*.fly.dev` URL works:

```bash
fly certs add autodock.example.com
```

Fly prints the DNS records to add at your registrar. Allow up to one hour for the cert to issue.

## Tearing it down

```bash
fly apps destroy <your-app-name>
```
