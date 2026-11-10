# Setting up dandelioncircularity.org with the admin section

This is a one-off setup, roughly an hour plus some waiting time for the domain. Afterwards Victor and Audrey can update the site themselves at **dandelioncircularity.org/admin**.

How it fits together:

- **GitHub** stores the website files. Every change made in the admin section is saved there.
- **Cloudflare Pages** (free) hosts the site. After every change it runs `build.py` and publishes the new version, usually within a minute or two. It also runs the small login code in `functions/api/`.
- **Porkbun** stays the registrar of the domain. Cloudflare takes over the domain's DNS settings.
- **Decap CMS** is the admin section itself. Victor and Audrey each log in with their own GitHub account. There is no shared password.

Menu names on these sites change now and then. If a step doesn't match exactly, look for the closest option.

## 1. Put the files on GitHub

1. Create a free account at github.com (for example one for the foundation).
2. Create a new **private** repository called `dandelion-circularity`.
3. Upload everything in this folder **except `_site`**. The easiest way is GitHub Desktop: clone the empty repository, copy the files into it, then commit and push. The web uploader also works: drag the folder contents in. There are about 70 files, within its limit of 100 per upload.

## 2. Tell the admin section where the files are

Open `admin/config.yml` and change this line:

```yaml
  repo: GITHUB-ACCOUNT/dandelion-circularity
```

Replace `GITHUB-ACCOUNT` with the account name from step 1, then commit and push again.

## 3. Move the domain's DNS from Porkbun to Cloudflare

1. In Cloudflare, choose **Add a domain** (sometimes called "Onboard a domain"), enter `dandelioncircularity.org` and pick the **Free** plan.
2. Cloudflare imports the domain's current DNS records:
   - **Delete** any Porkbun parking or forwarding records for `dandelioncircularity.org` and `www` (A, ALIAS or CNAME records). Pages will set up the right ones in step 5.
   - **Keep** any MX and TXT records if you use email on this domain, such as Porkbun email forwarding.
3. Cloudflare shows **two nameservers**. At Porkbun, go to **Domain Management**, open the domain's details and find **Authoritative Nameservers**. Replace Porkbun's nameservers with Cloudflare's two.
   - If **DNSSEC** is switched on at Porkbun, switch it off first. You can turn it on again later from Cloudflare.
4. Wait for Cloudflare to email that the domain is active. This usually takes minutes, sometimes a few hours.

## 4. Create the Pages project

1. In Cloudflare go to **Workers & Pages → Create**. Choose **Pages** (not Workers), then **Connect to Git** (sometimes called "Import an existing Git repository"), and allow access to the `dandelion-circularity` repository.
   - Don't use **Upload assets** (drag and drop). That option doesn't run `build.py` or the login code. It shows "Pages functions are not supported", and a project created that way can't be connected to GitHub later.
2. Use these build settings:
   - Framework preset: **None**
   - Build command: `python3 -m pip install -r requirements.txt && python3 build.py`
   - Build output directory: `_site`
   - Environment variable: `PYTHON_VERSION` = `3.12`
3. **Save and Deploy.** The site appears at a temporary address like `dandelion-circularity.pages.dev`. Check that it looks right. The admin login only works on the real domain, so leave that for step 8.

## 5. Connect the domain to the site

1. In the Pages project, open **Custom domains → Set up a custom domain** and enter `dandelioncircularity.org`. Cloudflare adds the DNS record and the HTTPS certificate itself.
2. Optional but recommended, so `www.dandelioncircularity.org` also works:
   - In **DNS**, add a CNAME record `www` → `dandelioncircularity.org`, with Proxied switched on.
   - In **Rules → Redirect Rules**, use the template **Redirect from WWW to root**.

## 6. Allow logging in with GitHub

1. On GitHub: **Settings → Developer settings → OAuth Apps → New OAuth App**.
   - Application name: `Dandelion Circularity beheer`
   - Homepage URL: `https://dandelioncircularity.org`
   - Authorization callback URL: `https://dandelioncircularity.org/api/callback`
2. Create it, then generate a **client secret**. Copy the Client ID and the secret.
3. In the Pages project, open **Settings → Variables and Secrets** and add, for **Production**:
   - `GITHUB_CLIENT_ID`: the Client ID
   - `GITHUB_CLIENT_SECRET`: the secret (choose the encrypted / Secret type)
4. New variables only take effect after the next deploy. Under **Deployments**, open the latest one and choose **Retry deployment**.

## 7. Give Victor and Audrey access

1. Victor and Audrey each create a free GitHub account.
2. In the repository: **Settings → Collaborators → Add people**. Add both of them. They'll get an email invitation they need to accept.

Only people added here can change the site. To remove someone's access, remove them here.

## 8. Test

Go to `https://dandelioncircularity.org/admin`, click **Inloggen met GitHub** and approve access. Then change something small, for example a photo caption, and publish. Within a couple of minutes it should show on the site, and a new deploy appears under **Deployments**.

If the login window shows an error:
- Check that the callback URL in step 6.1 is exactly right.
- Check that both variables are set under Production.
- Check that you redeployed afterwards.

## Good to know

- **Undoing a mistake:** in the Pages project, under Deployments, you can roll back to an older version. In the admin section you can also simply edit or delete the item.
- **Warnings:** if the build can't use something (an unreadable photo, a link that isn't from YouTube), it skips it and prints a `WARNING` line in the deploy log. The rest of the site still publishes. If a build fails completely, the previous version stays online.
- **Photos:** uploads are stored as originals in the private repository. The public site only gets smaller copies, with camera data such as GPS location removed.
- **Cookies:** visitors get no cookies. Editors get one short-lived cookie while logging in, which protects the login. If you switch on extra Cloudflare features such as Bot Fight Mode, check the cookie policy first, because some of them set cookies.
- **Working on your own computer:** with Python installed, run `python -m pip install -r requirements.txt` once, then `python build.py`. Open `_site/index.html` to view the result. The admin section only works on the live site.
- **Text on the fixed pages** (mission, workshops and so on) is in `src/pages-nl.html` and `src/pages-en.html`. It isn't in the admin section, so changes there still go through whoever edits the files.
