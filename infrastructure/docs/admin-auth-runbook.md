# Admin auth runbook (Cognito, Google-only public SPAs)

Student and teacher hosted SPAs use **Cognito Hosted UI / OAuth with Google**. The **`StreamMyCourse-Auth-*`** CloudFormation stack ([`auth-stack.yaml`](../templates/auth-stack.yaml)) always provisions the **Google** identity provider and sets app clients **`streammycourse-student-<env>`** and **`streammycourse-teacher-<env>`** to **`SupportedIdentityProviders: [Google]`** only — there is **no** native Cognito username/password path on those clients. **Deploy** workflows and **`deploy.ps1 -Template auth`** require **Google OAuth** credentials (see below).

## Deprecated workflows

The following paths are obsolete for MVP public SPAs and must not be reintroduced in code or operator expectations:

- **Hybrid SPA app clients + native Amplify sign-up/password** flows on hosted student or teacher bundles.
- Amplify **`loginWith.email`** in the SPA codebase — sign-in configures **Hosted UI OAuth only**, and **`VITE_COGNITO_USER_POOL_ID`**, **`VITE_COGNITO_USER_POOL_CLIENT_ID`**, and **`VITE_COGNITO_DOMAIN`** must all be set for Amplify auth to initialize (parity with SPA build checker [`scripts/check-cognito-spa-env.mjs`](../../scripts/check-cognito-spa-env.mjs)).

**Forks / lab without Google OAuth:** Do **not** run the **`Deploy`** workflow’s **full dev/prod backend** jobs that provision auth until **`GOOGLE_OAUTH_CLIENT_ID`** and **`GOOGLE_OAUTH_CLIENT_SECRET`** exist on each GitHub **Environment**. Local **`deploy.ps1 -Template auth`** also refuses empty Google parameters. SPA builds might still compile with pool ids from stacks created under an older template; that combination is unsupported for this repo’s **mainline** pipelines.

**Legacy data (pre-Google-only):** Clearing code is not enough. Before the first Google-only cutover per environment, run **[Pre-launch clean slate](#pre-launch-clean-slate-dev-then-prod)** (ordered **DynamoDB → S3 video bucket (full prefix sweep or lifecycle) → Cognito users last**) so old native users and catalog rows cannot collide.

## Pre-launch clean slate (dev then prod)

**Policy:** Before the first Google-only production cutover, wipe legacy native users and course state so native-vs-Google identity collision cannot occur. **Not launched — no retention requirement.** Double-check **AWS account, region, stack names, and environment** before destructive steps.

**Order (mandatory):** **DynamoDB catalog → S3 uploads → Cognito users last.** Clearing Cognito first loses the ability to correlate enrollments with identities for audit.

### 1) DynamoDB — empty catalog table

Table name pattern: **`StreamMyCourse-Catalog-<env>`** (see [`api-stack.yaml`](../templates/api-stack.yaml) `CatalogTable`). Items use prefixes **`COURSE#`**, **`USER#`**, **`LESSON#`**.

- **Verify table name** from CloudFormation stack **`StreamMyCourse-Api-<env>`** output or AWS Console.
- **Goal:** item count **0** (or table deleted and recreated only if your process allows — prefer scan + batch delete to keep the table).
- Prefer a **repeatable script** or documented `aws dynamodb scan` + `batch-write-item` delete loop; avoid typos on prod.

**Confirmation:** `aws dynamodb describe-table --table-name <name>` / Console **Explore items** shows no items.

### 2) S3 — empty course upload prefix

Bucket from **`StreamMyCourse-Video-<env>`** (stack output **`BucketName`**). Course media keys are **`{courseId}/lessons/{lessonId}/video|thumbnail/...`** and **`{courseId}/thumbnail/...`** (see Lambda `CourseMediaStorage`).

```bash
# Replace <bucket> from stack output — never guess the bucket name.
aws s3 rm "s3://<bucket>/uploads" --recursive
```

**Confirmation:** `aws s3 ls "s3://<bucket>/"` returns nothing (or only expected non-test prefixes).

### 3) Cognito — delete all pool users

Pool name pattern: **`StreamMyCourse-Auth-<env>-users`** (see [`auth-stack.yaml`](../templates/auth-stack.yaml)).

- Console: User pools → users → delete (bulk if available), **or**
- CLI loop: `aws cognito-idp list-users --user-pool-id <id>` + `admin-delete-user` per username/sub.

**Confirmation:** user count **0** before deploying Google-only template changes.

### 4) Deploy

Push **`main`** (or run your deploy pipeline) so **auth**, **API**, and **SPAs** pick up Google-only settings. If CloudFormation fails on IdP ordering, **retry the auth stack deploy once**.

---

## First admin / break-glass (Google-only)

There is **no** `create-first-admin.py` script: public app clients do not support native sign-up.

**Break-glass path:**

1. Open the **student** or **teacher** dev/prod site and complete **Sign in with Google** so a pool user exists.
2. In **AWS Console** → **Cognito** → user pool → **Users** → select that user → **Edit** attributes.
3. Set **`custom:role`** to **`admin`** or **`teacher`** as needed.
4. Ask the user to **sign out and sign in again** so JWTs carry the new claim.

MVP has **no** self-service teacher request API; promotion stays Console-based.

---

## Google Cloud (per environment)

1. Create a **Google Cloud OAuth 2.0 Client ID** of type **Web application** for **dev** and a **separate** client for **prod** (never share client secrets across envs).
2. **Authorized redirect URIs:** exactly the Cognito hosted UI callback for that env, e.g.  
   `https://<COGNITO_DOMAIN_PREFIX>.auth.<region>.amazoncognito.com/oauth2/idpresponse`  
   (use the real prefix and region from the deployed auth stack.)
3. **Authorized JavaScript origins:** your student and teacher site origins (and localhost only for local dev if you use it).
4. Complete **OAuth consent screen**; note **Testing** mode user limits until Google verification.

---

## GitHub Environment secrets / vars

Set **`GOOGLE_OAUTH_CLIENT_ID`** and **`GOOGLE_OAUTH_CLIENT_SECRET`** on **both** GitHub **Environments** (`dev` / `prod`) — the **Deploy** workflow’s **Deploy auth** steps fail fast when either secret is missing, and **`parameter-overrides`** always pass **`GoogleClientId`** / **`GoogleClientSecret`** into [`auth-stack.yaml`](../templates/auth-stack.yaml). Also set **`COGNITO_DOMAIN_PREFIX`**, student/teacher **callback** and **logout** URL vars as referenced by [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml) and the reusable web workflows.

SPA build secrets (typical names):

| Secret | Purpose |
|--------|---------|
| `VITE_COGNITO_USER_POOL_ID` | Pool id |
| `VITE_COGNITO_STUDENT_CLIENT_ID` / `VITE_COGNITO_TEACHER_CLIENT_ID` | Mapped per SPA workflow to client env |
| `VITE_COGNITO_DOMAIN` | Hosted UI **host only** (e.g. `prefix.auth.eu-west-1.amazoncognito.com`) |
| `VITE_API_BASE_URL` | API stage URL |

**SPA build contract:** `npm run build:student` / `build:teacher` run [`scripts/check-cognito-spa-env.mjs`](../../scripts/check-cognito-spa-env.mjs) first (npm **`prebuild:*`** hook). If pool id **and** client id are set, **`VITE_COGNITO_DOMAIN`** must be set or the build **fails** (CI and local when vars come from `frontend/.env.production*`). The checker merges **`frontend/.env*`** the same way as Vite production; unit tests set **`COGNITO_SPA_ENV_NO_DOTENV=1`** so only subprocess env is used ([`tests/unit/test_cognito_spa_env_contract.py`](../../tests/unit/test_cognito_spa_env_contract.py)).

---

## Promote a user to instructor

Same as break-glass: Console **`custom:role`** → `teacher`, then re-auth.

---

## Wire API Gateway to the pool

Deploy or update the API stack with the pool ARN so protected routes use the Cognito authorizer and Lambda sets `COGNITO_AUTH_ENABLED=true`:

- **PowerShell:** pass `-CognitoUserPoolArn` to `deploy.ps1` when using template `api`.
- **Bash / CI:** set `COGNITO_USER_POOL_ARN` before `scripts/deploy-backend.sh`.

---

## After the auth stack deploys (copy outputs → secrets → redeploy SPAs)

The backend job passes **`UserPoolArn`** into the API stack automatically on the same run. Student and teacher bundles still need Cognito IDs at **build time**.

1. **Print outputs** (same account/region as deploy, default `eu-west-1`):

   ```powershell
   .\scripts\print-auth-stack-outputs.ps1 -Environment dev
   ```

   ```bash
   ./scripts/print-auth-stack-outputs.sh dev eu-west-1
   ```

2. **Set GitHub Environment secrets** (web reusable workflows use **`environment: dev`** / **`prod`**).

   **Cognito domain prefixes (backend Deploy):** Use **`COGNITO_DOMAIN_PREFIX`** on **both** GitHub Environments with **different** globally unique values for dev vs prod.

   **Automated (AWS CLI + `gh`):** from repo root, after `gh auth login`:

   ```powershell
   .\scripts\set-github-auth-secrets-from-stack.ps1 -Environment dev
   ```

   Preview without writing:

   ```powershell
   .\scripts\set-github-auth-secrets-from-stack.ps1 -Environment dev -WhatIf
   ```

   **Manual map** (same as script):

   | GitHub secret | CloudFormation output key |
   |---------------|---------------------------|
   | `VITE_COGNITO_USER_POOL_ID` | `UserPoolId` |
   | `VITE_COGNITO_STUDENT_CLIENT_ID` | `StudentUserPoolClientId` |
   | `VITE_COGNITO_TEACHER_CLIENT_ID` | `TeacherUserPoolClientId` |
   | `VITE_COGNITO_DOMAIN` | `HostedUIDomain` |
   | `VITE_API_BASE_URL` | **`ApiEndpoint`** from **`streammycourse-api`** (dev) or **`StreamMyCourse-Api-prod`** (prod) |

   Verify: `gh secret list --env dev`

3. **Redeploy via CI/CD (default):** push to **`main`**. [`.github/workflows/deploy-backend.yml`](../../.github/workflows/deploy-backend.yml) runs integ → dev backend → **student + teacher web** → prod when gates pass.

4. **Local dev:** paste printed `.env` lines into [`frontend/.env`](../../frontend/.env) (never commit). Restart Vite after changes.

---

## Smoke test and deploy verification

After a successful **Deploy** for an environment:

1. Open **student** and **teacher** site URLs (edge stack outputs `StudentSiteUrl` / `TeacherSiteUrl`).
2. Confirm **only Google** sign-in path works for new users; **`GET /users/me`** returns profile when logged in.
3. In Cognito Console, confirm student/teacher app clients list **Google** only under **`Supported identity providers`**.
4. **Callback allowlists:** Google Cloud client + Cognito app client callback URLs must **match exactly** hosted origins (no stray localhost on prod).

---

## Rollback (Google-only issues)

1. Use **git revert** / a prior **`auth-stack.yaml`** revision if policy allows (expect impact on SSO-only users aligned with **`Pre-launch clean slate`**).
2. Redeploy auth stack and SPAs via the **Deploy** workflow as usual.

**Cannot undo** clean-slate deletes of Cognito users, DynamoDB items, or S3 objects — confirm backups are truly unnecessary before wipe steps.

---

## Rotating Google OAuth credentials

Rotate **`GOOGLE_OAUTH_CLIENT_SECRET`** (and **`GOOGLE_OAUTH_CLIENT_ID`** if replacing the Google Cloud client) in GitHub **Environment** secrets; redeploy the **auth** stack so CloudFormation picks up values. Update **Google Cloud** redirect URIs if the Cognito hosted domain prefix or region changed. Removing Google from this pipeline **without** a replacement IdP fork is intentionally **unsupported** — the workflow and **`auth-stack`** template assume Google federation for public SPA clients.

---

## Future IdPs (e.g. Apple)

Add another **`AWS::Cognito::UserPoolIdentityProvider`** in [`auth-stack.yaml`](../templates/auth-stack.yaml) and append the provider name to **`SupportedIdentityProviders`** for student/teacher clients; register redirect URIs and secrets the same way as Google.
