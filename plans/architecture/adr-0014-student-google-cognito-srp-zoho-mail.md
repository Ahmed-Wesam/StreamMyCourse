# ADR 0014 — Student Google + Cognito SRP and Zoho Mail (RS-6)

## Status

Accepted (Research Spectrum)

## Context

Teachers already sign in with **Google** via Cognito Hosted UI. Students need **email/password** as well as Google, with verification and forgot-password mail, without:

- Calling Cognito (or Zoho SMTP / SES) from the **in-VPC catalog Lambda**
- Creating duplicate Cognito users when the same email uses Google after native sign-up (or the reverse)
- Introducing Amazon SES when the domain already uses **Zoho** mail (SPF/DKIM)

## Decision

### App clients

| Client | Identity providers | Notes |
|--------|-------------------|--------|
| `streammycourse-student-*` | **COGNITO** + **Google** | `ALLOW_USER_SRP_AUTH` + OAuth code flow; Amplify email login + Hosted UI |
| `streammycourse-teacher-*` | **Google only** | No native password on the public teacher client |

Wired in [`auth-stack.yaml`](../../infrastructure/templates/auth-stack.yaml); student SPA register / verify / forgot-password flows; profile allowlists and terms gate via **`PATCH /users/me`** (migration **016**).

### PreSignUp account linking

Dedicated **PreSignUp** Lambda ([`infrastructure/lambda/cognito_pre_signup/`](../../infrastructure/lambda/cognito_pre_signup/)):

- **ExternalProvider (Google):** link Google identity to an existing **native** user with the same email when appropriate.
- **Native SignUp:** reject duplicate when a verified email already exists (prompt Google / existing account).

### Transactional Cognito email (Zoho, not SES)

- Cognito **CustomEmailSender V1_0** + KMS; Lambda decrypts codes and sends via **Zoho SMTP**.
- Secret: Secrets Manager **`streammycourse/zoho-smtp/prod`** (operator password from GitHub Environment; see deploy scripts — no secrets in git).
- Package: [`infrastructure/lambda/cognito_custom_email_sender/`](../../infrastructure/lambda/cognito_custom_email_sender/).
- Auth stack gates PreSignUp + custom sender deploy with Zoho ARN (`ShouldDeployCustomEmailSender`).

Contact / grade notify mail reuse the same Zoho secret via the **non-VPC** transactional-mail worker + SQS (catalog only enqueues).

### No Cognito calls from VPC catalog

Catalog auth stays at the API Gateway authorizer boundary:

- Controllers extract `sub` / `role` (and related claims) from authorizer context.
- Services authorize with `cognito_sub` + `role` + RDS ownership/enrollment/purchase state.
- **No** `cognito-idp` Admin APIs and **no** Cognito HTTP from `infrastructure/lambda/catalog/**` (see `.cursor/skills/auth-no-cognito-in-vpc/SKILL.md`).

Session supersede and profile sync use **out-of-VPC** Cognito triggers (`cognito_user_profile_sync`), not catalog→Cognito calls.

## Consequences

### Pros

- One student identity story (Google or password) with linking instead of duplicate accounts.
- Mail stays on existing Zoho domain posture; SES identity/DKIM removed from auth stack.
- Preserves no-NAT catalog invariant for auth and SMTP.

### Cons

- CustomEmailSender + KMS + PreSignUp are additional auth-stack moving parts; live verify mail needs Zoho secret + deploy.
- Teachers cannot use native password on the public teacher client by design.

## Alternatives considered

| Alternative | Why not |
|-------------|---------|
| Amazon SES for Cognito mail | Domain already on Zoho; duplicate mail path |
| Catalog AdminGetUser / link in VPC | Requires NAT or Cognito VPC endpoints; violates auth skill |
| Password on teacher client | Out of RS-6 scope; Google-only teacher remains |

## Related

- [`design.md`](../../design.md) §9 Security (student/teacher sign-in), §10 Auth stack
- ADR 0004 — future auth boundary (historical direction)
- [`infrastructure/docs/admin-auth-runbook.md`](../../infrastructure/docs/admin-auth-runbook.md)
- [`module-map.md`](./module-map.md) — `services/auth/`
- ADR 0013 (RS-5) — purchases require signed-in students
