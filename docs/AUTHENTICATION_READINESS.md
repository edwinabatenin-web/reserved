# Google and Apple authentication readiness

Status: **foundations present; neither provider is launch-verified**  
Reviewed: 13 August 2026

## Current architecture

Reserved does not integrate directly with Google Identity Services or Sign in
with Apple. The login page embeds Clerk, then sends a short-lived Clerk session
token to the Reserved server. Reserved verifies the token using Clerk's JWKS and
creates its own signed, HTTP-only session.

This architecture can support Google and Apple, but the presence of
`CLERK_PUBLISHABLE_KEY` proves only that a Clerk instance is configured. It does
not prove that either social provider is enabled, correctly registered, policy
compliant or tested.

`reserved.providers.identity.readiness` therefore fails closed. A provider is
reported ready only when all of the following deployment evidence exists:

- `IDENTITY_BROKER=clerk`;
- a recognisable Clerk publishable key;
- a non-default `SESSION_SECRET` of at least 32 characters;
- one clean HTTPS `AUTH_PUBLIC_ORIGIN`; and
- a provider-specific post-test attestation: `GOOGLE_SIGN_IN_CONFIGURED=1` or
  `APPLE_SIGN_IN_CONFIGURED=1`.

The attestation variables are not credentials. They must be set only after the
corresponding checklist below passes with synthetic accounts. No provider
secret should be copied into the repository or sprint evidence.

## Google gate

Official requirements relevant to Reserved:

- Use Google Identity Services for a new website integration; the legacy Google
  Sign-In platform library is deprecated and FedCM affects current browser
  behaviour.
- Register the exact authorised origin and redirect URI in Google Cloud.
- Use HTTPS outside localhost.
- Validate the anti-forgery `state`; use `nonce` for replay protection where an
  OpenID Connect authorization request is managed directly.
- Validate signed-token issuer, audience, expiry and subject server-side. In the
  brokered architecture, evidence is required that Clerk performs the upstream
  Google validation and that Reserved validates the resulting Clerk token.
- Use the stable provider subject as identity. Email must not be treated as the
  cross-provider account key.

Synthetic acceptance evidence required before attestation:

1. Confirm Google is enabled in the correct Clerk instance and uses the intended
   Google OAuth application, authorised origin and callback.
2. Complete new-account, returning-account, cancelled-consent and denied/error
   journeys in supported desktop and mobile browsers, including a FedCM-capable
   browser.
3. Confirm a forged, expired or wrong-instance Clerk token is rejected and that
   logout clears the Reserved session.
4. Confirm duplicate email addresses do not silently link Google to another
   provider account without an explicit, tested account-linking policy.
5. Record dates, browser versions, non-secret configuration identifiers and
   redacted results.

## Apple gate

Official requirements relevant to Reserved:

- Web authentication requires a Sign in with Apple-enabled primary App ID, an
  associated Services ID, registered domains/return URLs and a private key.
- Registered return URLs are absolute HTTPS URLs containing scheme, host and
  path. The configured values must exactly match the broker callback.
- Preserve and verify `state` against CSRF; associate the client session with a
  `nonce` to prevent replay.
- Apple returns the `user` name/email object only on the first authorization.
  Persist it during that first successful journey; do not require it later.
- Support private-relay addresses. If Reserved emails those users, register the
  outbound source and configure SPF/DKIM for Apple's Private Email Relay.
- Register and authenticate a TLS 1.2+ server-to-server notification endpoint
  before relying on account-change/deletion signals.
- Use Apple's required button presentation and Sign in with Apple usage rules.

Synthetic acceptance evidence required before attestation:

1. Confirm Apple Developer enrolment, the primary App ID, Services ID, domain,
   return URL and broker-held key are configured; record identifiers only, never
   the private key.
2. Complete first authorization with shared email, first authorization with
   Hide My Email, returning sign-in (where name is absent), cancellation and
   error journeys.
3. Confirm forged/replayed responses and wrong-instance Clerk tokens fail.
4. Confirm relay email delivery from an authenticated registered source.
5. Confirm account deletion/revocation handling and data-retention consequences
   before relying on the provider in production.

## Current blockers and decisions

- No repository evidence proves that Google or Apple is enabled in the Clerk
  dashboard or that its callback/origin registrations match Reserved.
- No end-to-end synthetic evidence has been captured for either provider.
- Apple requires Apple Developer account assets, including a primary App ID;
  confirm that these exist and that the intended Reserved web service is eligible.
- ClerkJS is pinned to the exact `6.25.12` package version audited on 13 August
  2026 rather than a moving `@latest` URL. A deliberate dependency-review and
  regression process is required for upgrades. First-party loading and the
  related Content Security Policy remain production-hardening decisions.
- Reserved now verifies that `iss` is the Frontend API derived from its Clerk
  publishable key, requires Clerk's default `sub` and `sid` claims, and validates
  any present `azp` against `CLERK_AUTHORIZED_PARTIES` (or the single
  `AUTH_PUBLIC_ORIGIN`). Verification fails closed if no permitted origin is
  configured. If a custom JWT template supplies `aud`, configure
  `CLERK_JWT_AUDIENCE` to require it; Clerk session tokens do not include `aud`
  by default, so Reserved does not invent one.
- Define an explicit account-linking policy. Never merge accounts solely because
  Google and Apple return the same email address.

## Primary sources

- Google, OpenID Connect: https://developers.google.com/identity/openid-connect/openid-connect
- Google, FedCM migration: https://developers.google.com/identity/sign-in/web/gsi-with-fedcm
- Apple, configuring the environment: https://developer.apple.com/documentation/signinwithapple/configuring-your-environment-for-sign-in-with-apple
- Apple, configuring a webpage: https://developer.apple.com/documentation/signinwithapple/configuring-your-webpage-for-sign-in-with-apple
- Apple, authenticating users: https://developer.apple.com/documentation/signinwithapple/authenticating-users-with-sign-in-with-apple
- Apple, web usage guidelines: https://developer.apple.com/sign-in-with-apple/usage-guidelines-for-websites-and-other-platforms/
