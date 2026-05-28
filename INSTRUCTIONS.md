# SpikesortingLabHub — TrueNAS Deployment Instructions

Steps tested on the test rig. Replicate these exactly on the main TrueNAS.

> **Path difference:** test rig used `user_home`, main TrueNAS uses `users`.
> Every path below already reflects the main TrueNAS convention.

---

## 1. Enable SSH on TrueNAS

TrueNAS UI → System → Services → start **SSH** and set it to auto-start.

---

## 2. Copy the init script from your Mac to TrueNAS

Run from your Mac terminal (not SSH):

```bash
scp /Users/kajalpatel/SpikesortingLabHub-server/truenas_init.sh \
    kajal@128.164.33.182:/mnt/root_data_storage/users/kajal/
```

---

## 3. SSH into TrueNAS

```bash
ssh truenas_admin@128.164.33.182
```

---

## 4. Move the script into the sslh folder

```bash
sudo cp /mnt/root_data_storage/users/kajal/truenas_init.sh \
        /mnt/root_data_storage/users/sslh/truenas_init.sh

sudo chmod +x /mnt/root_data_storage/users/sslh/truenas_init.sh
```

---

## 5. Test-run the script manually

```bash
sudo /mnt/root_data_storage/users/sslh/truenas_init.sh
```

Check the log it generates:

```bash
cat /mnt/root_data_storage/users/sslh/sslh_init.log
```

---

## 6. Pull the Docker image and start the container (first time only)

```bash
docker pull ikajalpatel21/spikesorting-labhub-latestimg:latest

export DJANGO_SECRET_KEY="$(cat /mnt/root_data_storage/users/sslh/secrets/django_secret.key)"

docker compose -f /mnt/root_data_storage/users/sslh/docker-compose.yml up -d
```

> If `secrets/django_secret.key` does not exist yet, generate it first:
> ```bash
> mkdir -p /mnt/root_data_storage/users/sslh/secrets
> openssl rand -hex 50 > /mnt/root_data_storage/users/sslh/secrets/django_secret.key
> chmod 600 /mnt/root_data_storage/users/sslh/secrets/django_secret.key
> ```

---

## 7. Verify the container is running

```bash
docker ps
docker logs spikesorting-labhub-server-spikesorting-labhub-1
```

Open in browser: `https://128.164.33.182:9443`
(self-signed cert warning is expected — click through)

---

## 8. Register the init script in TrueNAS UI

System → Advanced Settings → Init/Shutdown Scripts → **Add**

| Field   | Value                                                   |
|---------|---------------------------------------------------------|
| Type    | Script                                                  |
| Script  | `/mnt/root_data_storage/users/sslh/truenas_init.sh`    |
| When    | Pre Init                                                |
| Timeout | 30                                                      |

---

## What happens on every reboot after this

1. TrueNAS kernel starts → ZFS pool mounts automatically
2. Pre Init script runs → verifies/creates bind-mount directories → bind-mounts experiments and trurnasdata
3. Docker daemon starts → `restart: unless-stopped` brings the container back up with all mounts in place
