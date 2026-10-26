# Deploy CodeLens AI (beginner path)

The website goes on Vercel. The API and the database are two EC2 instances in the AWS default VPC, in **Asia Pacific (Mumbai), `ap-south-1`**. Use that default VPC as it is: no new VPC, private subnet, or NAT gateway.

```text
browser
  │
  ▼
Vercel  (React app, HTTPS)
  │  VITE_API_URL = https://<elastic-ip-with-dashes>.sslip.io
  ▼
codelens-backend   t3.small, Elastic IP, Caddy + FastAPI
  │  private IP, port 27017
  ▼
codelens-mongo     t3.micro, MongoDB
```

Caddy gets a free HTTPS certificate. With no domain of your own, the API address is the Elastic IP written with dashes, for example `13.234.56.78` becomes `https://13-234-56-78.sslip.io`. Vercel can call that address. Every `https://*.vercel.app` site is allowed. A custom site is allowed too if you set `FRONTEND_ORIGIN`.

The three-server layout (its own VPC, Nginx, a private database) is the advanced option: [DEPLOY_AWS.md](DEPLOY_AWS.md).

## What you need

- An AWS account.
- A Groq API key from [console.groq.com](https://console.groq.com).
- A GitHub account. Vercel deploys from the GitHub repository.
- About 30 minutes the first time. The API image download is the slow part.

Leave the instances running only while you are using them. A `t3.micro` plus a `t3.small` in Mumbai is on the order of **$20–25 a month** if they stay on, plus a few dollars for the disks. Vercel’s hobby plan is free. An Elastic IP is free while it is attached to a **running** instance. It is billed (about $3.60 a month) while the instance is stopped, so release it when you are finished. See [Stop the bill](#stop-the-bill).

## 1. Stay in Mumbai

In the AWS console, set the region (top right) to **Asia Pacific (Mumbai)**. Do this before every step below. A security group created in another region cannot be attached to these instances.

## 2. Create a key pair

1. EC2 → **Key pairs** → **Create key pair**.
2. Name: `codelens-key`. Type: RSA. Format: `.pem`.
3. Create. The browser downloads `codelens-key.pem`. Keep that file. You cannot download it again.

## 3. Create the two security groups

EC2 → **Security groups** → **Create security group**. Leave the VPC on the **default** VPC. Leave the outbound rule as **All traffic**.

Create the backend group first, then the database group (the database rule points at the backend group).

**`codelens-backend`**

| Type | Port | Source |
| --- | --- | --- |
| SSH | 22 | My IP |
| HTTP | 80 | Anywhere (`0.0.0.0/0`) |
| HTTPS | 443 | Anywhere (`0.0.0.0/0`) |

**`codelens-mongo`**

| Type | Port | Source |
| --- | --- | --- |
| SSH | 22 | My IP |
| Custom TCP | 27017 | Security group `codelens-backend` |

Leave port 27017 closed to the internet. The database accepts connections only from the API instance.

## 4. Launch the database instance

EC2 → **Launch instance**.

1. Name: `codelens-mongo`.
2. AMI: **Ubuntu Server 24.04 LTS** or **26.04 LTS**. A newer Ubuntu LTS also works; the script warns and continues.
3. Instance type: **t3.micro**.
4. Key pair: `codelens-key`.
5. Network: the **default** VPC and a default subnet. Auto-assign public IP: **Enable** (this address is for SSH only).
6. Firewall: **Select existing security group** → `codelens-mongo`.
7. Storage: **20 GiB gp3**.
8. Launch.

## 5. Launch the API instance and attach an Elastic IP

EC2 → **Launch instance**.

1. Name: `codelens-backend`.
2. AMI: **Ubuntu Server 24.04 LTS** or **26.04 LTS**.
3. Instance type: **t3.small**.
4. Key pair: `codelens-key`.
5. Network: the **default** VPC and a default subnet. Auto-assign public IP: **Enable**.
6. Firewall: **Select existing security group** → `codelens-backend`.
7. Storage: **30 GiB gp3**. The API image does not fit on the 8 GiB default disk.
8. Launch.

Then give it a stable address:

1. EC2 → **Elastic IPs** → **Allocate Elastic IP address** → Allocate.
2. Actions → **Associate Elastic IP address**.
3. Resource type: Instance. Instance: `codelens-backend`. Associate.

Use this Elastic IP from here on. The old public IP stops working.

## 6. Connect from Windows PowerShell

Move the key somewhere stable, then restrict it. OpenSSH refuses a key that everyone can read.

```powershell
New-Item -ItemType Directory -Force "$env:USERPROFILE\.ssh" | Out-Null
Move-Item "$env:USERPROFILE\Downloads\codelens-key.pem" "$env:USERPROFILE\.ssh\codelens-key.pem"
icacls "$env:USERPROFILE\.ssh\codelens-key.pem" /inheritance:r
icacls "$env:USERPROFILE\.ssh\codelens-key.pem" /grant:r "${env:USERNAME}:(R)"
```

In EC2 → Instances, select `codelens-mongo` and copy its **Public IPv4 address**. Then:

```powershell
ssh -i "$env:USERPROFILE\.ssh\codelens-key.pem" ubuntu@MONGO_PUBLIC_IP
```

Type `yes` if it asks you to trust the host. You should see an `ubuntu@...` prompt. For the API instance, use the **Elastic IP** in that same command.

If your IP changes (a different network, or your ISP), SSH will hang. EC2 → Security groups → `codelens-mongo` and `codelens-backend` → edit the SSH rule → **My IP** again.

## 7. Set up MongoDB (one command)

On `codelens-mongo`:

```bash
sudo apt-get update
sudo apt-get install -y git tmux
git clone https://github.com/Ayyaji/Codelens-AI.git
cd Codelens-AI
git checkout cursor/aws-deploy-407f
tmux new -s setup
sudo bash deploy/simple/mongo-setup.sh
```

`tmux` keeps the command running if the laptop sleeps. To get back in: SSH again, then `tmux attach -t setup`. Detach without stopping it with `Ctrl-b` then `d`.

If `git checkout` says the branch does not exist, check out the branch your team merged this guide into. If `deploy/simple/mongo-setup.sh` is missing, you are on the wrong branch.

The script installs Docker and runs the official **`mongo:7.0`** image. MongoDB 8.x refuses to start on Linux kernels 6.19 through 7.0.13 ([SERVER-121912](https://jira.mongodb.org/browse/SERVER-121912), [SERVER-125742](https://jira.mongodb.org/browse/SERVER-125742)). Ubuntu 24.04 and 26.04 AMIs ship those kernels. MongoDB 7.0 is supported on them. The Python client is already in range: Motor 3.6+ and PyMongo 4.9+ both speak to 7.0.

The container turns on authentication and publishes port 27017 on the instance’s **private** IP only. Data stays in `/var/lib/codelens-mongo`. It prints a line like:

```text
mongodb://codelens:PASSWORD@172.31.10.20:27017/codelens?authSource=admin
```

Copy that whole line. It is `MONGODB_URI`. A copy is also in `/root/codelens-mongodb.uri` on that instance (`sudo cat /root/codelens-mongodb.uri`). The root password is in `/root/codelens-mongodb.admin`, which only root can read. Running the script again prints the same URI and does not rotate the password.

A failed MongoDB 8 start can leave WiredTiger files in `/var/lib/codelens-mongo` before any application data exists. If `/root/codelens-mongodb.uri` was never written, the script deletes that directory and starts 7.0. If the script stops because a MongoDB 8 directory is still there, wipe it and run the command again:

```bash
sudo docker rm -f codelens-mongo
sudo rm -rf /var/lib/codelens-mongo
sudo bash deploy/simple/mongo-setup.sh
```

Leave this SSH session open so you can copy the URI. Open a **second** PowerShell window for the next step.

## 8. Set up the API (one command)

SSH to the **Elastic IP** of `codelens-backend` with the same `ssh -i` command, then:

```bash
sudo apt-get update
sudo apt-get install -y git tmux
git clone https://github.com/Ayyaji/Codelens-AI.git
cd Codelens-AI
git checkout cursor/aws-deploy-407f
tmux new -s setup
sudo bash deploy/simple/backend-setup.sh
```

Answer the prompts:

1. **MONGODB_URI** — paste the line from the database instance. It must contain the private IP, not the MongoDB public IP.
2. **Groq API keys** — paste one key, or 3 to 5 keys separated by commas. The cursor does not move. Press Enter. The script saves them as `GROQ_API_KEYS` and also keeps the first key in `GROQ_API_KEY`.
3. **Domain** — press Enter. The script uses `<elastic-ip-with-dashes>.sslip.io`.
4. **Custom site origin** — press Enter. Every `https://*.vercel.app` site is already allowed. Fill this in only for a site that is not on `vercel.app`, for example `https://codelens.example.edu`.
5. **Build the knowledge base** — press Enter (Yes). Answers stay empty until this finishes.
6. **Create a teacher** — type `y`, then a name, an email, and a password of at least 8 characters.

You can skip the prompts by setting the variables yourself:

```bash
sudo MONGODB_URI='mongodb://codelens:PASSWORD@172.31.10.20:27017/codelens?authSource=admin' \
  GROQ_API_KEYS='gsk_one,gsk_two,gsk_three' \
  BUILD_KB=1 \
  CREATE_TEACHER=1 \
  TEACHER_NAME='Ada' \
  TEACHER_EMAIL='ada@example.com' \
  TEACHER_PASSWORD='a-long-password' \
  bash deploy/simple/backend-setup.sh
```

`BUILD_KB=0` and `CREATE_TEACHER=0` skip those steps when the shell is not interactive.

What the command does:

- Adds 4 GiB of swap, so the 2 GiB instance can load the embedding model.
- Installs Docker.
- Writes `/opt/codelens/backend.env` (mode `600`) with a generated `JWT_SECRET`, `GROQ_API_KEY`, `GROQ_API_KEYS` (the comma-separated pool, passed into the API container through that file), the MongoDB URI, and a CORS rule for `https://*.vercel.app`. A single `GROQ_API_KEY` still works. The script prints how many keys it saved, not the key values.
- Starts the API container with `unless-stopped` and keeps Chroma and the model cache on disk.
- Puts Caddy in front of it for HTTPS on ports 80 and 443. Port 8000 stays on the instance itself.

The first build downloads PyTorch. Leave the window open. When it finishes, the script prints:

```text
API address: https://13-234-56-78.sslip.io
```

That is the value for Vercel. A second run reuses the saved key, URI, and JWT secret. Add `REBUILD=1` after a `git pull` so the image is rebuilt. Add `DOMAIN=api.example.com` to use your own name instead of sslip.io (point the DNS A record at the Elastic IP first).

## 9. Put the frontend on Vercel

1. Sign in at [vercel.com](https://vercel.com) with GitHub.
2. **Add New…** → **Project** → import `Codelens-AI`.
3. **Root Directory**: choose `frontend`. This is required. The React app is not in the repository root.
4. Framework preset: **Vite**. Leave the build command (`npm run build`) and output directory (`dist`) as detected.
5. **Environment variables**: name `VITE_API_URL`, value `https://13-234-56-78.sslip.io` (the address the API script printed). No slash at the end.
6. Deploy.

`frontend/vercel.json` rewrites unknown paths to `index.html`, so a refresh on `/teacher` or a student route still loads the app. Vercel serves real files (JavaScript, CSS) before that rewrite.

Vite reads `VITE_API_URL` at **build** time. If you change it, open the Vercel project → **Deployments** → redeploy. Saving the variable alone does not update the site.

Leave `VITE_USE_MOCKS` unset. The mock client would not talk to your API.

## 10. Test

In PowerShell, using the API address from step 8:

```powershell
curl https://13-234-56-78.sslip.io/health
```

You want:

```json
{"status":"ok","mongo":"ok"}
```

`mongo` other than `ok` means the API cannot reach the database. Check that `MONGODB_URI` uses the private IP and that port 27017 on `codelens-mongo` allows the `codelens-backend` security group.

Then open the `*.vercel.app` URL Vercel shows:

1. Register a student and sign in.
2. Sign out. Sign in as the teacher you created.
3. Open a student page, refresh the browser, and confirm it stays on that page.

A local `npm run dev` can also call this API. The Vite origins (`http://localhost:5173` and the preview port) stay allowed.

## Stop the bill

- **Pause:** EC2 → Instances → select both → **Stop**. The disks are kept. The Elastic IP is **not** free while the API instance is stopped.
- **Finished:** Terminate both instances. EC2 → Elastic IPs → Release the address. Delete the security groups if you want a clean account. Vercel → Project → Settings → Delete Project.

## If something fails

| What you see | What to do |
| --- | --- |
| SSH times out | The SSH rule is not your current IP. Set the source to **My IP** again. You are using `ubuntu`, the `.pem` key, and (for the API) the Elastic IP. |
| `mongo-setup.sh` cannot start MongoDB | `sudo docker logs codelens-mongo --tail 50`. The image is `mongo:7.0` because MongoDB 8 exits on kernel 6.19+. If a failed 8.0 data directory is still in the way: `sudo docker rm -f codelens-mongo && sudo rm -rf /var/lib/codelens-mongo` and run the script again. |
| API logs show exit 137 | The model ran out of memory. The script adds swap; re-run it. Do not start a second API container. |
| `https://…sslip.io/health` fails, local health works | The Elastic IP must be associated **before** you run the API script. Ports 80 and 443 must be open to anywhere. Re-run `sudo bash deploy/simple/backend-setup.sh` so the sslip.io name matches the current IP. |
| The Vercel site loads but login fails | `VITE_API_URL` must be the `https` API address with no trailing slash, and you must redeploy after changing it. |
| Browser console says CORS | The site is not on `*.vercel.app` and `FRONTEND_ORIGIN` was left empty. Re-run the API script and enter `https://your-real-site` at the origin prompt. |

## Advanced option

[DEPLOY_AWS.md](DEPLOY_AWS.md) is the three-server layout: a custom VPC, Nginx on its own instance, and MongoDB on a private subnet. Use it when you outgrow this setup. The scripts in `deploy/frontend`, `deploy/backend`, and `deploy/mongo` belong to that layout. This guide uses only `deploy/simple`.
