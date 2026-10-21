# Deploy CodeLens AI on AWS

This is the production layout for the VTU project. Three EC2 instances share one VPC in **Asia Pacific (Mumbai), `ap-south-1`**. The browser talks only to the frontend. The API and the database accept traffic only from the security group in front of them.

You need an AWS account, a Groq API key, and a domain name if you want HTTPS from Let's Encrypt. A domain is a few dollars a year from any registrar, or a subdomain your college already owns. The site also runs over plain HTTP on the frontend's public address for a local demo.

S3, CloudFront, and MongoDB Atlas are real options and they cost less. They are documented at the end. They are not the layout this chapter builds.

## Architecture

```mermaid
flowchart TB
  user["Student or teacher browser"]
  groq["Groq API"]

  subgraph vpc["VPC 10.0.0.0/16 — ap-south-1"]
    subgraph pub["Public subnet 10.0.1.0/24 — ap-south-1a"]
      fe["Frontend EC2 t3.micro<br/>Nginx, Vite build, HTTPS"]
      be["Backend EC2 t3.small<br/>Docker: FastAPI, Chroma, embeddings"]
    end
    subgraph priv["Private subnet 10.0.2.0/24 — ap-south-1a"]
      db["Database EC2 t3.micro<br/>MongoDB with authentication<br/>20 GB gp3, daily snapshots"]
    end
  end

  user -->|"HTTPS 443"| fe
  fe -->|"HTTP /api to private IP port 8000<br/>source: frontend security group"| be
  be -->|"MongoDB port 27017<br/>source: backend security group"| db
  be -->|"HTTPS outbound"| groq
```

Figure 1. CodeLens AI in AWS Mumbai. Paste the block into [mermaid.live](https://mermaid.live) if the report tool does not draw it.

The backend stays in the **public** subnet. FastAPI calls Groq on every explanation, and the instance also downloads the embedding model. A private subnet without a NAT gateway cannot make those calls. A NAT gateway is about $33 a month before data charges, which is more than the database server itself. The security group is what closes port 8000: the public address does not answer unless the packet comes from the frontend.

The database ends in the **private** subnet. It has no public address. Both subnets are in `ap-south-1a` so the 20 GB data volume can be detached and attached again. A volume cannot move across availability zones.

Nginx on the frontend serves the React build and forwards `/api/...` to the backend with the `/api` prefix removed. The Vite build uses `VITE_API_URL=/api`, so the browser stays on one origin and does not need CORS.

| Instance | Type | Subnet | Private IP to assign | Disk |
| --- | --- | --- | --- | --- |
| Frontend | t3.micro | public `10.0.1.0/24` | `10.0.1.10` | 10 GB gp3 root |
| Backend | t3.small | public `10.0.1.0/24` | `10.0.1.20` | 20 GB gp3 root |
| Database, first boot | t3.micro | public `10.0.1.0/24` | `10.0.1.30` | 10 GB gp3 root + 20 GB gp3 data |
| Database, after the move | t3.micro | private `10.0.2.0/24` | `10.0.2.10` | same 20 GB data volume |

The first database address is temporary. You install Docker there, because that subnet can reach the internet, then you replace the instance with one in the private subnet and keep the data volume. Turning on `WITH_NAT=1` skips that move and costs the NAT gateway.

## Security groups

`deploy/vpc/setup-network.sh` creates these groups. Outbound is open on all three. The private subnet still has no internet route unless you created a NAT gateway, so outbound from the database goes nowhere after the move.

| Security group | Port | Source | Purpose |
| --- | --- | --- | --- |
| `codelens-frontend` | 22 | Your public IP `/32` | SSH. Omit this rule when you use Session Manager only. |
| `codelens-frontend` | 80 | `0.0.0.0/0` | HTTP, and the Let's Encrypt challenge |
| `codelens-frontend` | 443 | `0.0.0.0/0` | HTTPS |
| `codelens-backend` | 22 | Your public IP `/32` | SSH |
| `codelens-backend` | 22 | `codelens-frontend` | SSH jump from the frontend |
| `codelens-backend` | 8000 | `codelens-frontend` | FastAPI. No other source can connect. |
| `codelens-mongo` | 22 | `codelens-frontend` | SSH jump. There is no SSH rule from the internet. |
| `codelens-mongo` | 27017 | `codelens-backend` | MongoDB. No other source can connect. |

Security-group references match when the connection uses the **private** IP. Use `10.0.1.20` and `10.0.2.10` in SSH config and in `MONGODB_URI`. A connection to a public IP does not match the group-to-group rule.

Session Manager is the alternative to port 22 on the frontend and the backend. Both have public addresses, and the instance profile includes `AmazonSSMManagedInstanceCore`. The database instance, once it is private, cannot reach Session Manager. Use the frontend as a jump host, or pay for a NAT gateway. Three interface VPC endpoints (SSM, SSM Messages, EC2 Messages) cost more than the database server, so this guide does not use them.

## What you pay

Prices are on-demand Linux in Mumbai, about 730 hours in a month, as published in 2026. Check the EC2 pricing page before you leave anything running. Groq is a separate account and is not in this table.

| Piece | Approx. USD / month |
| --- | --- |
| Frontend t3.micro | $8 |
| Frontend public IPv4 | $3.65 |
| Frontend disk, 10 GB gp3 | $0.90 |
| Backend t3.small | $16 |
| Backend public IPv4 | $3.65 |
| Backend disk, 20 GB gp3 | $1.80 |
| Database t3.micro | $8 |
| Database root disk, 10 GB gp3 | $0.90 |
| Database data disk, 20 GB gp3 | $1.80 |
| Daily snapshots, 7 kept, small database | $1 to $2 |
| **Total, left on all month** | **about $46** |
| NAT gateway, only if you set `WITH_NAT=1` | about $33 plus $0.045 per GB |
| S3 + CloudFront instead of the frontend EC2 | usually under $1, often inside the free tier |
| Atlas M0 instead of the database EC2 | $0 |

A public IPv4 address is about $0.005 an hour whether or not the instance is doing work. Stopping an instance stops the compute charge. The disk and any address you keep are still billed.

Accounts created on or after 15 July 2025 receive a $100 sign-up credit and can earn up to $100 more, for six months or until the credit runs out. `t3.micro` and `t3.small` draw from that credit. At about $46 a month this layout uses a $100 credit in a little over two months if the instances stay on. Older accounts get 750 hours a month of `t3.micro` for 12 months. Two micro instances plus a small instance do not fit in that allowance.

The cheaper shape, with S3, CloudFront, and Atlas, is one `t3.small` plus its address and disk: **about $22 a month**.

## 1. Create the AWS account, MFA, and a budget

1. Open [aws.amazon.com](https://aws.amazon.com) and create an account. Use an email you control. The account name can be `codelens`.
2. Choose the Basic support plan. It has no fee.
3. A card is required. The free credit does not remove the card check.
4. Sign in as the **root** user.
5. Open the account menu (your name, top right) → **Security credentials** → **Multi-factor authentication** → **Assign MFA device**. Use an authenticator app. Save the recovery codes somewhere outside the laptop.
6. Open **Billing and Cost Management** → **Billing preferences**. Turn on free-tier alerts and the invoice email.
7. Open **Budgets** → **Create budget** → **Monthly cost budget**. Set the amount to **$25**. Add email alerts at 50% and at 100%. Use the root email. A second budget at $10 is useful if you want an earlier warning.
8. In the same Billing page, confirm the payer is this account and you can see the credits under **Credits**.

After this section, sign out of the root user. The root user is for billing and for closing the account.

## 2. Create the IAM user you will use day to day

1. Sign in as root once more. Open **IAM** → **Users** → **Create user**. Name it `codelens-cli`. Turn on console access and choose a password.
2. Open **IAM** → **Policies** → **Create policy** → **JSON**. Paste `deploy/iam/codelens-cli-policy.json`. Name the policy `codelens-cli`.
3. Attach that policy to `codelens-cli`. Do not attach `AdministratorAccess`.
4. Open the user → **Security credentials** → assign an MFA device here too.
5. **Create access key** → **Command Line Interface**. Download the CSV. This is the only time AWS shows the secret. It does not go in the git repository.
6. On your laptop:

```bash
aws configure
# Access key and secret from the CSV
# Default region: ap-south-1
# Default output: json
aws sts get-caller-identity
```

The identity should be `codelens-cli`, and the region you pass on later commands is `ap-south-1`. The console region menu (top right) must say **Asia Pacific (Mumbai)** whenever you click through EC2, SSM, or VPC.

Every secret the application reads lives in SSM Parameter Store or in a mode-600 file on one instance. The names are:

| Parameter | Type | Where it is used |
| --- | --- | --- |
| `/codelens/prod/GROQ_API_KEY` | SecureString | Backend |
| `/codelens/prod/JWT_SECRET` | SecureString | Backend |
| `/codelens/prod/MONGO_ROOT_PASSWORD` | SecureString | Database |
| `/codelens/prod/MONGO_APP_PASSWORD` | SecureString | Database, and inside `MONGODB_URI` |
| `/codelens/prod/MONGODB_URI` | SecureString | Backend, after the database has its final private IP |
| `/codelens/prod/MONGODB_DB` | String, optional | Backend. Default `codelens` |
| `/codelens/prod/CORS_ORIGINS` | String, optional | Backend, only for the S3 alternative |

Create the first four now. Create `MONGODB_URI` after the database move, when you know `10.0.2.10` is the address.

Console path: **Systems Manager** → **Parameter Store** → **Create parameter**. Tier **Standard**. Type **SecureString**. The Groq key comes from [console.groq.com](https://console.groq.com). Generate the others on your laptop and paste them:

```bash
openssl rand -base64 48
openssl rand -hex 24
openssl rand -hex 24
```

The hex values are the MongoDB root password and the application password. Hex keeps the URI and the init script free of characters that need escaping. The JWT value must be at least 32 characters. The sample `change-me-to-a-long-random-string` is rejected by the deploy script.

## 3. Create the instance role

From a clone of this repository, on the laptop:

```bash
bash deploy/iam/setup-roles.sh
```

This creates the instance profile `codelens-ec2`. It can open a Session Manager shell and read `/codelens/prod/*`. It cannot create instances or change security groups. Select this profile on all three instances. A new profile can take a minute to show up in the launch screen.

## 4. Create the VPC

```bash
ADMIN_CIDR="$(curl -fsS https://checkip.amazonaws.com)/32"
echo "$ADMIN_CIDR"
ADMIN_CIDR="$ADMIN_CIDR" bash deploy/vpc/setup-network.sh
```

The script writes `codelens-network.txt` and `codelens-key.pem` in the current directory. `chmod 400` is applied to the key. Both files are gitignored. Do not commit them. If your IP changes, add the new `/32` to ports 22 on the frontend and backend groups in the EC2 console. Running the script again prints the existing ids and does not create a second VPC.

To skip SSH from your IP and use Session Manager for the public instances:

```bash
SKIP_SSH=1 bash deploy/vpc/setup-network.sh
```

The jump-host SSH rules stay, because that is how you reach the private database. Add a NAT gateway only if you have decided to pay for it:

```bash
WITH_NAT=1 ADMIN_CIDR="$(curl -fsS https://checkip.amazonaws.com)/32" bash deploy/vpc/setup-network.sh
```

## 5. Launch the three instances

In the EC2 console, region Mumbai, **Launch instance**. The AMI is **Ubuntu Server 24.04 LTS**, 64-bit (x86), not ARM. The key pair is `codelens-key`. Under **Advanced details**, the IAM instance profile is `codelens-ec2`.

Launch the frontend first, then the backend, then the database. Use the subnet and security group ids from `codelens-network.txt`.

**Frontend**

- Name: `codelens-frontend`
- Type: `t3.micro`
- Network: VPC `codelens`, subnet `codelens-public`, auto-assign public IP **Enable**
- Security group: existing `codelens-frontend`
- Advanced network: primary private IP `10.0.1.10`
- Storage: 10 GB gp3
- Tag `Project` = `codelens`

Then **Elastic IPs** → **Allocate** → associate it with this instance. An Elastic IP costs the same as an auto-assigned public address while it is attached to a running instance, and it stays put when you stop and start the instance. Point the domain's A record at this address. Let's Encrypt fails if the A record is missing or points somewhere else.

**Backend**

- Name: `codelens-backend`
- Type: `t3.small`
- Same public subnet, auto-assign public IP **Enable**
- Security group: `codelens-backend`
- Primary private IP: `10.0.1.20`
- Storage: **20 GB gp3**. The CPU torch image and the build cache need the room. An 8 GB root disk fills up during `docker compose build`.
- Tag `Project` = `codelens`

**Database, temporary public boot**

- Name: `codelens-mongo`
- Type: `t3.micro`
- Public subnet, auto-assign public IP **Enable**. This address is only so `apt` and `docker pull` can run. The security group still refuses SSH and port 27017 from the internet.
- Security group: `codelens-mongo`
- Primary private IP: `10.0.1.30`
- Root disk: 10 GB gp3
- **Add a second volume**: 20 GB gp3, device `/dev/sdf`, **Delete on termination off**. This is the data disk. Tag it `Project=codelens` and `Role=mongo-data` if the launch screen lets you tag volumes. Otherwise the snapshot script tags it later.
- Tag `Project` = `codelens`

If you set `WITH_NAT=1`, launch this instance in `codelens-private` with no public IP and private IP `10.0.2.10` instead, and skip the move in section 8.

## 6. SSH, or Session Manager

On the laptop, `~/.ssh/config`:

```text
Host codelens-frontend
  HostName FRONTEND_ELASTIC_IP
  User ubuntu
  IdentityFile ~/path/codelens-key.pem

Host codelens-backend
  HostName 10.0.1.20
  User ubuntu
  ProxyJump codelens-frontend
  IdentityFile ~/path/codelens-key.pem

Host codelens-mongo
  HostName 10.0.1.30
  User ubuntu
  ProxyJump codelens-frontend
  IdentityFile ~/path/codelens-key.pem
```

`chmod 400` the pem. `ssh codelens-frontend` should land on Ubuntu. After the database moves, change the mongo `HostName` to `10.0.2.10`.

Session Manager, for the frontend and the backend: EC2 → the instance → **Connect** → **Session Manager**. The agent is already on the Ubuntu AMI. The instance profile must be `codelens-ec2`, and the instance needs outbound HTTPS, which the public subnet provides.

On each instance, clone the branch that contains this guide. Until this work is merged, that branch is `cursor/aws-deploy-407f`. After it is merged, use `cursor/mongodb-auth-backend-3267`.

```bash
sudo git clone -b cursor/aws-deploy-407f https://github.com/Ayyaji/Codelens-AI.git /opt/codelens/app
```

## 7. Database

SSH to `codelens-mongo` through the frontend. Confirm the extra disk exists (`lsblk` shows a disk of about 20 GB that is not mounted on `/`). Then:

```bash
cd /opt/codelens/app
sudo bash deploy/mongo/setup.sh
```

The script formats that disk as ext4 if it has no filesystem, mounts it at `/opt/codelens/mongo` by UUID, installs Docker, and starts MongoDB 7 with authentication. The cache is capped at 0.25 GB so a 1 GB instance has memory left for the operating system. The application user is created the first time the data directory is empty. Passwords come from SSM (`deploy/mongo/fetch-env.sh`, which `setup.sh` calls when the instance role works) or from `/opt/codelens/mongo.env` if you write it by hand:

```text
MONGO_INITDB_ROOT_USERNAME='root'
MONGO_INITDB_ROOT_PASSWORD='hex-from-openssl'
MONGO_APP_USERNAME='codelens'
MONGO_APP_PASSWORD='other-hex-from-openssl'
```

Mode 600, owned by root. A successful run writes `/opt/codelens/mongodb.uri`, also mode 600. Leave that file in place until section 8 has finished. The private IP in it is still `10.0.1.30`.

Port 27017 on the host listens on `127.0.0.1` and on the private IP only.

## 8. Move the database into the private subnet

You cannot change an instance's subnet. The cheap path is: install while a public address exists, then launch a new instance from an AMI in the private subnet and reattach the same data volume.

1. On the database instance: `cd /opt/codelens/app && sudo docker compose -f deploy/mongo/docker-compose.yml stop`.
2. EC2 → **Stop** the instance. Wait until it is stopped.
3. **Detach** the 20 GB data volume. Write down the volume id (`vol-...`).
4. **Actions** → **Image and templates** → **Create image**. The root disk is the only volume still attached, so the AMI does not copy the database. Name it `codelens-mongo`.
5. **Launch instance from AMI**. Type `t3.micro`. Subnet `codelens-private`. Auto-assign public IP **Disable**. Security group `codelens-mongo`. Primary private IP `10.0.2.10`. Key `codelens-key`. Instance profile `codelens-ec2`. Root disk 10 GB is already in the AMI.
6. After it is running, **Attach** the original 20 GB volume as `/dev/sdf`.
7. Update the SSH config host to `10.0.2.10` and connect through the frontend.
8. `lsblk` and `findmnt /opt/codelens/mongo` should show the same UUID. If it is not mounted: `sudo mount -a`.
9. Refresh the address and start MongoDB:

```bash
cd /opt/codelens/app
sudo bash deploy/mongo/refresh-ip.sh
sudo cat /opt/codelens/mongodb.uri
```

10. Store that single line as SSM `/codelens/prod/MONGODB_URI`. Then delete the file:

```bash
sudo shred -u /opt/codelens/mongodb.uri
```

11. Terminate the old public database instance. If it had an Elastic IP, release it. The new instance has no public address.

The URI looks like:

```text
mongodb://codelens:HEX@10.0.2.10:27017/codelens?authSource=admin
```

From the backend, a later health check is the proof that the security group and the URI agree. There is no reason to open 27017 to your laptop.

## 9. Snapshots

On the laptop, after the data volume id is known:

```bash
VOLUME_ID=vol-0123456789abcdef0 bash deploy/mongo/setup-snapshots.sh
```

The script tags the volume `Project=codelens` and `Role=mongo-data`, creates an IAM role `codelens-dlm`, and a Lifecycle Manager policy. Snapshots run at **18:30 UTC**, which is midnight in India, and **7** are kept. Lifecycle Manager has no fee. Snapshot storage does, which is the $1 to $2 line in the cost table while the database is small.

Confirm the next day: EC2 → **Lifecycle Manager** → the policy → **Snapshots**, or EC2 → **Snapshots** filtered by the tag `Project=codelens`.

## 10. Backend

SSH to `codelens-backend`.

```bash
cd /opt/codelens/app
sudo bash deploy/backend/setup.sh
```

This installs Docker, creates a **2 GiB swap file** at `/swapfile`, and builds the API image.

The swap file matters. `t3.small` has 2 GiB of RAM. Loading the CPU build of PyTorch and `all-MiniLM-L6-v2` spikes above that for a short time. Without the swap file the kernel kills the container and Docker shows exit code **137**. Swap lives on the EBS disk, so that first load is slow. Check it with:

```bash
swapon --show
free -h
```

The image installs the CPU wheel of torch on purpose. The default PyPI wheel is the CUDA build, about 2 GB, and it will not load on this instance. The Dockerfile aborts the build if a CUDA wheel replaced it. One uvicorn worker is started. A second worker would load the model twice.

Chroma is stored at `/opt/codelens/data/chroma`. The model cache is `/opt/codelens/cache/huggingface`. Both are bind mounts, so `docker compose down` does not delete them. The process inside the container is uid **10001**. The setup script gives that uid the two directories.

The first start downloads the embedding model. `deploy.sh` waits up to about ten minutes for `http://127.0.0.1:8000/health`. A healthy body is:

```json
{"status":"ok","mongo":"ok"}
```

`503` with `"mongo":"error"` means the URI, the security group, or the private IP is wrong. The body never includes the URI. `sudo docker compose -f deploy/backend/docker-compose.yml logs --tail 80 api` shows the connection error on the server.

### First teacher

Students register in the browser. Teachers do not. On the backend:

```bash
cd /opt/codelens/app
sudo bash -lc 'set -a; source /opt/codelens/backend.env; set +a; docker compose -f deploy/backend/docker-compose.yml exec -T api python -m rag_core.create_teacher --name "Ada Rao" --email ada@school.edu --password "replace-with-8-to-72-characters"'
```

The password is 8 to 72 characters. It is written to the shell history of root. Run `history -c` afterwards if this shell is shared. The command prints the new teacher id. Sign in on the site with that email.

### Knowledge base

Build the debugging notes once. The script stops the API first, because a second copy of the embedding model is enough to get the instance killed.

```bash
sudo bash deploy/backend/build-kb.sh
```

The index is kept under `/opt/codelens/data/chroma`. Running the script again appends duplicate chunks. To rebuild, stop the stack, delete the files in that directory, and run it again.

## 11. Frontend

Building the Vite app on the `t3.micro` is possible (the setup script adds 2 GiB of swap because Monaco's bundle is large) and slow. Building on the laptop is the better path.

On the laptop, from the repository:

```bash
cd frontend
npm ci
VITE_API_URL=/api VITE_USE_MOCKS=false npm run build
scp -i codelens-key.pem -r dist ubuntu@FRONTEND_ELASTIC_IP:/tmp/codelens-dist
```

On the frontend instance:

```bash
cd /opt/codelens/app
sudo DIST_SRC=/tmp/codelens-dist BACKEND_PRIVATE_IP=10.0.1.20 bash deploy/frontend/setup.sh
```

Nginx serves `/var/www/codelens` and proxies `/api/` to `10.0.1.20:8000`. React Router paths such as `/login` fall back to `index.html`. Hashed files under `/assets/` are cached. `index.html` is not.

Check from the frontend box:

```bash
curl -fsS -o /dev/null -w '%{http_code}\n' http://127.0.0.1/
curl -fsS http://127.0.0.1/api/health
```

The second command must return `{"status":"ok","mongo":"ok"}`.

### HTTPS

Create an A record for the name you will use, for example `app.yourdomain.edu`, pointing at the frontend Elastic IP. Wait until `dig +short app.yourdomain.edu` shows that address. Then, on the frontend:

```bash
sudo bash deploy/frontend/issue-cert.sh you@college.edu app.yourdomain.edu
```

Port 80 must stay open. Let's Encrypt uses it for the challenge, and after the certificate exists Nginx redirects port 80 to HTTPS except for that challenge path. Renew with:

```bash
sudo bash deploy/frontend/issue-cert.sh --renew
```

A weekly cron entry is enough:

```bash
echo '15 3 * * 1 root bash /opt/codelens/app/deploy/frontend/issue-cert.sh --renew' | sudo tee /etc/cron.d/codelens-certbot
```

Open `https://app.yourdomain.edu`. Register a student, sign in as the teacher, upload a short job description, and ask one debugging question so you know Groq and Chroma are both live.

Let's Encrypt does not issue a certificate for a bare IP address. Without a domain, use `http://` and the Elastic IP for a viva on a network you trust. The S3 section below is the other way to get HTTPS without buying a name, and it replaces this instance.

## 12. Optional GitHub Actions deploy

The workflow `.github/workflows/deploy.yml` does nothing on push. You run it by hand from the Actions tab. It updates the frontend and the backend over Session Manager. It does not deploy the database, because the private instance has no Session Manager path.

1. IAM → create user `codelens-github` with policy `deploy/iam/codelens-github-policy.json`. Create an access key. This user cannot read the SSM parameters.
2. GitHub → **Settings** → **Secrets and variables** → **Actions**.
   - Secrets: `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`
   - Variables: `FRONTEND_INSTANCE_ID` (`i-...`), `BACKEND_INSTANCE_ID`, `DEPLOY_REF` (the branch name, such as `cursor/mongodb-auth-backend-3267`)
3. Actions → **Deploy** → **Run workflow**. Choose `frontend`, `backend`, or `both`.

The instance runs `git pull` in `/opt/codelens/app` and then `deploy/frontend/deploy.sh` or `deploy/backend/deploy.sh`. A frontend run that does not find a `dist/` folder builds on the instance.

## 13. Lower-cost alternatives

### MongoDB Atlas M0 instead of the database instance

This removes the database EC2 instance, the 20 GB volume, the snapshots, and the private-subnet move. The free M0 tier is 512 MB, which is enough for a class.

1. Create a project at [mongodb.com/atlas](https://www.mongodb.com/atlas).
2. **Create a deployment** → **M0** → provider **AWS** → region **Mumbai (`ap-south-1`)**.
3. Add a database user. Use **Autogenerate Secure Password** and save it. If the password contains `@`, `:`, `/`, or `#`, URL-encode it when you build the URI.
4. **Network access** → add the **backend instance's public IPv4** as a `/32`. Atlas sees the public address, not `10.0.1.20`. When you stop and start the backend, an auto-assigned public IP changes and you must update this list. An Elastic IP on the backend avoids that.
5. **Connect** → **Drivers** → copy the `mongodb+srv://` string. Put it in SSM as `/codelens/prod/MONGODB_URI`. Set `MONGODB_DB` to `codelens` if the URI has no database name.
6. On the backend, `sudo bash deploy/backend/fetch-env.sh` and `sudo bash deploy/backend/deploy.sh`.
7. Skip sections 7, 8, and 9. The private subnet can stay empty.

`/health` returning `"mongo":"ok"` means the allow list and the URI are right.

### S3 and CloudFront instead of the frontend instance

This removes the frontend `t3.micro` and its public IPv4. The API then needs its own HTTPS name, because a CloudFront site is HTTPS and the browser blocks calls to plain HTTP.

1. S3 → **Create bucket**. Name `codelens-frontend-` plus your 12-digit account id. Region Mumbai. **Block all public access** stays on.
2. CloudFront → **Create distribution**.
   - Origin: the bucket.
   - Origin access: **Origin access control**. Create a new control and let CloudFront sign requests. After you create the distribution, copy the bucket policy from the banner onto the bucket. The bucket stays private.
   - Viewer protocol: **Redirect HTTP to HTTPS**.
   - Default root object: `index.html`.
   - Cache policy: **CachingOptimized**.
3. Open the distribution → **Error pages**. Add two custom responses, for **403** and **404**. Response page path `/index.html`, response code **200**. React Router needs this, or `/login` returns the bucket's XML error.
4. Second distribution, for the API:
   - Origin domain: the backend public DNS name. Protocol **HTTP only**, port **8000**.
   - Allowed methods: **GET, HEAD, OPTIONS, PUT, POST, PATCH, DELETE**.
   - Cache policy: **CachingDisabled**.
   - Origin request policy: **AllViewerExceptHostHeader** (this forwards `Authorization`).
   - Viewer protocol: **Redirect HTTP to HTTPS**.
   - Raise the origin response timeout to 60 seconds. Job-description calls to Groq can exceed the 30 second default.
5. On the backend security group, allow port 8000 from the managed prefix list `com.amazonaws.global.cloudfront.origin-facing` (region is global, the list is available in Mumbai). Remove the frontend-group rule after the frontend instance is gone.
6. Set SSM `/codelens/prod/CORS_ORIGINS` to the frontend distribution origin, for example `https://d111111abcdef8.cloudfront.net`, with no trailing slash. Restart the backend so the process reads it.
7. From the laptop:

```bash
export VITE_API_URL=https://dAPI.cloudfront.net
export S3_BUCKET=codelens-frontend-123456789012
export CLOUDFRONT_DISTRIBUTION_ID=E1234567890ABC
export AWS_REGION=ap-south-1
bash deploy/frontend/upload-s3.sh
```

The script refuses a `localhost` or plain `http://` API URL. `index.html` is uploaded with `no-cache`. Hashed assets are cached for a year. The CloudFront invalidation clears the old `index.html`.

Using both alternatives leaves one server: the backend `t3.small`.

## 14. Day-to-day updates

Frontend, after a new build:

```bash
sudo DIST_SRC=/tmp/codelens-dist bash /opt/codelens/app/deploy/frontend/deploy.sh
```

Backend, after a git pull:

```bash
cd /opt/codelens/app
sudo bash deploy/backend/deploy.sh
```

Database image updates are rare. With no NAT gateway, launch a temporary public address only if you must pull a new MongoDB image, or pull the image on the frontend and `docker save` / `docker load` it across the jump host. The data volume is not involved.

## 15. Tear it down

Do this when the project is over, or the credit will keep falling.

1. Empty and delete the S3 bucket and disable then delete the CloudFront distributions, if you created them. A distribution must be disabled and finished deploying before it can be deleted.
2. Terminate the three EC2 instances.
3. Delete the 20 GB data volume after you have copied anything you want to keep. Delete the snapshots tagged `Project=codelens`, or they keep costing money.
4. Release every Elastic IP. An address left allocated and unattached is billed.
5. EC2 → **Lifecycle Manager** → delete the snapshot policy. IAM → delete role `codelens-dlm` after detaching its policy.
6. From the laptop:

```bash
CONFIRM=delete bash deploy/vpc/teardown-network.sh
```

7. Systems Manager → Parameter Store → delete `/codelens/prod/*`.
8. IAM → delete the access keys, then the users `codelens-cli` and `codelens-github`, then the instance profile and role `codelens-ec2`.
9. If you created an Atlas cluster, Atlas → the cluster → **Terminate**.
10. The next day, Billing → **Bills** should show no EC2, EBS, EIP, or snapshot lines still growing. The $25 budget email is the backstop if something was left behind.

## Troubleshooting

| What you see | What it usually means |
| --- | --- |
| Container exit **137** during the first backend start | The model load was killed. `swapon --show` must list `/swapfile`. Re-run `sudo bash deploy/backend/setup.sh` if the file is missing. |
| `/api/health` returns 502 from Nginx | The backend is down, or `BACKEND_PRIVATE_IP` in `/etc/codelens/frontend.env` is not `10.0.1.20`. `sudo bash deploy/frontend/render-nginx.sh` after you fix the file. |
| `/api/health` returns 503 `"mongo":"error"` | Security group on 27017, wrong private IP after the move, or the URI user. The backend log has the driver error. The HTTP body does not. |
| Browser calls `localhost:8000` | The build was made without `VITE_API_URL=/api`. Rebuild and copy `dist` again. |
| HTTPS page, requests blocked | The build's API URL is `http://...`. Use `/api` on this layout, or `https://` on the S3 layout. |
| `docker compose build` dies with "no space left" | The root disk is under 20 GB, or old build cache is still there. `sudo docker builder prune -af` and rebuild. Do not prune volumes. |
| Let's Encrypt fails | The A record does not point at the Elastic IP yet, or port 80 is not open to the world. |
| SSH to the database times out | You used its public IP, or the frontend security group is not the source. Use `ProxyJump` and the private IP. |
| Teacher command says the email exists | The account is already there. Sign in, or pick another email. |
