# Reserved™

A Replit-ready preview of Reserved's October-launch product structure and design.

For the next independent reviewing agent, begin with
[`RESERVED_NEW_AGENT_HANDOVER.md`](RESERVED_NEW_AGENT_HANDOVER.md). It identifies
the governing evidence, superseded material, known limitations, reproduction
steps and remaining launch evidence. The review is not an official audit or
certification exercise.

## Run

1. Add the files to a new Replit Python project.
2. Install dependencies:
   `pip install -r requirements.txt`
3. Set `SESSION_SECRET` in Replit Secrets.
4. Run:
   `python run.py`

The default is demonstration mode. No bank account is connected and no money is moved.

## Reuse from the earlier pack

Do not copy the earlier `app.py`, `database.py`, `oauth_handshake.py`,
`stripe_transfers.py` or root-level Yapily file into this project unchanged.

The earlier reviewed tax and provider work remains useful as reference, but this
pack establishes the new canonical locations and interfaces. Insert hardened
provider implementations only into `reserved/providers/`.

## Design system

The design system is the shared visual language in:

- `reserved/static/css/design-system.css`: colours, typography, controls, surfaces.
- `reserved/static/css/app.css`: page layouts and product components.
- `reserved/templates/base.html`: shared shell, navigation and account chrome.

This prevents every template from inventing its own colours, spacing and buttons.
