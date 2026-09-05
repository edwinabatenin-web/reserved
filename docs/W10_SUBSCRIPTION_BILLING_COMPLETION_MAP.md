# W10 subscription and billing completion map

## Status and authority

**Current accepted-evidence update (5 September 2026):** the disposable-local
S3D transactional repository is independently accepted and integrated at
`26831400fcb0ee638761b589b3bbbf0e239427dd`; see the final reconciliation section
for its exact source and limits. Current paid-route inventory is 46 always /
55 HICBC-enabled routes and 28 paid classifications, not active paid guarding.
The earlier reconciliation-9 register and its status/next-action narrative below
remain historical snapshots; their absence-of-durability statements must not
erase the subsequently accepted local primitive. No authenticated production
billing persistence or custody is established. Strict completion stays 0/8,
terminal 0/13, W9 0/5; October remains not_ready with 18 blockers.

**Evidence cut-off:** 4 September 2026

**Original planning commit:** `b15d3fcfa423192e1a8a2e8d0a49851b366518f4`

**Current integration reconciliation point:**
`5e6ea885a371bb15aaba3bf8abb5bb81a99f6c2e` (tree
`585c3364cfb7bafeecdaf7c1af7a2b804202e6df`)

**Current status:** **S1 independently reviewed and integrated; S2A's
provider/runtime-neutral authority, S2B's four fail-closed engineering defaults,
S2C's historical specialist-evidence/decision classification, S2D's
disabled-first owner-bound recovery contract and S2F's bounded Q1 refund and Q2
paid-surface engineering policies,
S3A's provider-neutral entitlement transition policy, S3B's detached event-inbox
contract, the hardened detached entitlement lifecycle and S3C's owner-bound
route-less non-durable runtime-entitlement admission seam compatible with S5D,
S4A's disabled-first
Stripe edge contract, S4B's disabled Checkout intent and S4C's disabled Customer
Portal intent, S5A's exact paid-surface
inventory, S5B's exact eleven-route reconciliation evidence, S5C's five
bounded route-hardening treatments and S5D's route-less provider-neutral
paid-access guard kernel are independently reviewed and integrated;
S6E's explicit seven-calendar-day `payment_recovery` presentation, S6F's
detached cancellation/end-of-paid-period presentation, S6G's initial-payment
pending/failure presentation and S6H's initial-paid presentation, plus early-W8
local lifecycle-composition evidence, S7A's
post-convergence reconciliation and S2E's detached tax/invoice prerequisite
contract are independently reviewed and integrated. `FD-W10-004` now settles
Q3's verified full-withdrawal suspension/restoration policy; tax/invoice and
billing-account recovery remain the two unresolved specialist/engineering policy
keys, while post-settlement implementation and specialist acceptance remain open; all 21
threats remain open; S2 partially implemented;
S3, S4, S5, S6 and S7 remain partial;
0/8 slices complete on the strict accepted-evidence denominator and 0/13 terminal
checks complete; W9 remains 0/5; not launch-ready.**

This map gives the October-launch subscription and billing workstream a finite
endpoint. It is a planning and assurance control, not a provider decision,
billing policy, implementation approval, production-access request or launch
approval. `FOUNDER_DECISIONS.md` is authoritative where older material differs.

### Reconciliation provenance

This mutable map is not self-hashed. The block below binds this reconciliation
to its exact clean integration base and to immutable historical component blobs.
Later truthful map updates may preserve this block without pretending that an
older review inspected the later map text. Existing live product-source guards
remain live; this record neither replaces nor weakens them.

<!-- W10-COMPLETION-MAP-RECONCILIATION-BEGIN -->
```json
{
  "schema_version": "W10-completion-map/2026-09-04/reconciliation-9",
  "reconciliation_base": {
    "commit": "5e6ea885a371bb15aaba3bf8abb5bb81a99f6c2e",
    "tree": "585c3364cfb7bafeecdaf7c1af7a2b804202e6df",
    "parents": [
      "e145e43631f9a03df70a378ac1eafbdf3974afa9"
    ]
  },
  "components": {
    "Founder-Decisions-W10-002-003": {
      "accepted_checkpoint": "14d5a253d6993044e026c4b862fa4a18708712da",
      "accepted_tree": "fc86cd3ffbb7279624763307ea2498be78521c84",
      "integration_commit": "10fb93e2e6ab567a72d2370c1603768a7ac04bb5",
      "integration_tree": "fc86cd3ffbb7279624763307ea2498be78521c84",
      "paths_sha256": {
        "FOUNDER_DECISIONS.md": "03765242c39354ffe57834da8a4a4e5b0dbbdacf5278731e560dea55ae3722d4"
      }
    },
    "Founder-Decision-W10-004": {
      "accepted_checkpoint": "ab4f8d4d34aa4b80022018b2b15315d5ff72ebb5",
      "accepted_tree": "155ac33d0ee11b8f7836ff82c0055d694313f57c",
      "integration_commit": "22512f29ed17dbc9a13a8741891345eb54513d05",
      "integration_tree": "155ac33d0ee11b8f7836ff82c0055d694313f57c",
      "paths_sha256": {
        "FOUNDER_DECISIONS.md": "78d0cbafe38e266b77c38198012b37d74042ee274a8f892bfca456f4a3ef584f"
      }
    },
    "W10-S2D": {
      "accepted_checkpoint": "1d70e550f685b9c1a4636caf3be75debce500219",
      "accepted_tree": "d6cad612d010baa3a311a8ecd2eabd5f9f37c37e",
      "integration_commit": "509c5360d453e23a0732e4e9d4637385eef20ef6",
      "integration_tree": "f2c35dfaaad2bf408d39b23e84716d25a0794c74",
      "paths_sha256": {
        "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md": "214e6fab5dcea9776faa8dc1cb425cbcd622698b8d62d1e0b710e11ec859f445",
        "reserved/billing/billing_account_recovery_contract.py": "b3bfc4501bdb3631bd87c9dc4aea0984b899fdd3afb535f1414cedd721f4ae06",
        "tests/test_w10_billing_account_recovery_contract.py": "7220d1d13b362d9c0c83d3e1ee37baae1fe83dc9bf3950605b919ff2d76213ee"
      }
    },
    "W10-S5C-product": {
      "accepted_checkpoint": "3c63e64e478957ce04ee1154363c2eae94b82b30",
      "accepted_tree": "ac3eb6f3028ef2e60bbd1543c1ee92f94655a0b7",
      "integration_commit": "85e1250f53180bb3c1aff111c17101b9e59df080",
      "integration_tree": "89a96da31b7a5dbe9bf55c01e875a0d611829e01",
      "paths_sha256": {
        "reserved/web/routes.py": "f1d8f6ea3730c8962899a0ffa4d7a78b8c8791693ca03c0d19e0feb8cec42bed",
        "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
        "tests/test_auth.py": "5dd2284eeb57dbed40119936ada5bde9c3902b21d0c0bf44cb61e55275d7b974",
        "tests/test_tax_year_context.py": "f01625359c365ca0085064e264d747e6d9d4007db0c6a34281f7666fff1d37fd",
        "tests/test_unsupported_plan_rendering.py": "5e2eae15e80a876a17bd0339526a798def1c238fbf84457178822710ef196c49",
        "tests/test_w10_internal_route_hardening.py": "20a754059b817eb33e5c83ae3edbe551c92c2bafbbbeeca39ed2c709900db3c8"
      }
    },
    "W10-S5C-evidence": {
      "accepted_checkpoint": "e3959964ca08bd5afb6f75feab4ec0fdc83a9423",
      "accepted_tree": "6e2705c4948b3b843d034beec05aef36ffb8c8ba",
      "integration_commit": "85e1250f53180bb3c1aff111c17101b9e59df080",
      "integration_tree": "89a96da31b7a5dbe9bf55c01e875a0d611829e01",
      "merge_resolution_paths": [
        "tests/test_w10_internal_route_reconciliation.py",
        "tests/test_w10_s2c_policy_evidence.py"
      ],
      "paths_sha256": {
        "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": "5d1d957f53edf04898df8064ee5825a5ab9a55091daf2fed8b292f54db596601",
        "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md": "4ba7324883e6aa27081e47ffa6f1c0a1fde99a5f175375a4aae289ce5b7a5917",
        "docs/W10_S5C_INTERNAL_ROUTE_HARDENING_EVIDENCE.md": "221b244e687611dfa3e55e67051cb9ffab59ef6fcd9f02d8c5c865611439d1f5",
        "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md": "301b5e882473703acc0b0415bb492139c5ebd9dd8fcb82380517772675098ec9",
        "docs/W9_SECURITY_DECISION_DOSSIER.md": "86a2f5280786571f3afe887b5a5dcbfb6e8d37fc26b9a702d3cba4bc33cc07d6",
        "tests/test_w10_internal_route_reconciliation.py": "72574710e3d1b1f94014bf5f23eadc87f2bc4c6c80041c133e08c4190e5c6982",
        "tests/test_w10_paid_surface_inventory.py": "adf2044d4c72bb7985e4fed90ecb771aa1d88719bb39aac9ce47c70c4371b512",
        "tests/test_w10_s2c_policy_evidence.py": "3073b21cf5fdef1aaaa2178cde3dbed0b90656269fb4fe817bcb02ad2d46a781",
        "tests/test_w9_security_evidence.py": "4f114c70dd8f93d868f8a81fa2c71fcb326c63a2bbf7460671536248d7ce5397"
      }
    },
    "W10-S5A-HICBC-refresh": {
      "accepted_checkpoint": "8480264e664a91a26c062e371b12192f9a628a4a",
      "accepted_tree": "559bfe4c77c5e5f3bf59553d91c78c614ac060ff",
      "integration_commit": "95dd628e27f7261282f2ecf55d4cf29720329b91",
      "integration_tree": "559bfe4c77c5e5f3bf59553d91c78c614ac060ff",
      "paths_sha256": {
        "docs/W10_S5A_PAID_SURFACE_INVENTORY.md": "8a2ee7d91eb20e29bcdd20ebd5d2f6b98e9dd559501140303937e99e1bd1e747",
        "tests/test_w10_paid_surface_inventory.py": "4ae3e0b6867248b1adaaedd8a9fcdfed60fdb63b70f76df40ff0d2889396f137"
      }
    },
    "W10-S5B-HICBC-downstream-reconciliation": {
      "accepted_checkpoint": "d954ddcc88466967cc16efcaba02778e03a0f9a2",
      "accepted_tree": "c72ff560e5f931f9f539114846d9f3d0cc5ced53",
      "integration_commit": "d954ddcc88466967cc16efcaba02778e03a0f9a2",
      "integration_tree": "c72ff560e5f931f9f539114846d9f3d0cc5ced53",
      "paths_sha256": {
        "docs/W10_S5B_INTERNAL_ROUTE_RECONCILIATION.md": "96f1ed01298604a283b791131ba43daf8c6b82582dd2ed822663d4b4a385daa8",
        "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md": "c1bd0cfaf68657995f92b2732f3b5bcc187cdbdc2a48461a04c27ec24bb0ac84",
        "tests/test_w10_internal_route_reconciliation.py": "5606c34bf60dbe508bc3761f466e2297d0a0ac1edbd748326fb728b654afa446",
        "tests/test_w9_security_evidence.py": "502c057ea6f1ddc9eab0898bcedc3713c1799d796dfe182da1231e2bf53a2e4d"
      }
    },
    "W10-S5B-HICBC-lineage-sentinel": {
      "accepted_checkpoint": "05134e536d0428e0bcdfab96a109d64f46d2d9a4",
      "accepted_tree": "60a30a3ad50bfdd6682b5ba95b19d3bb303272e4",
      "integration_commit": "05134e536d0428e0bcdfab96a109d64f46d2d9a4",
      "integration_tree": "60a30a3ad50bfdd6682b5ba95b19d3bb303272e4",
      "paths_sha256": {
        "tests/test_w9_security_evidence.py": "ea2aa3ae64274baa176b853755739e112cb1a11a5e6404975653aede21439e60"
      }
    },
    "W10-S5D-product": {
      "accepted_checkpoint": "88a3c879fbacad9e3f9feebe02764499f1f53daa",
      "accepted_tree": "24f83e9560588676b1c89cd87194245a2f24580b",
      "integration_commit": "824b3060c950ce7f623d29aeadc53ede34b6c565",
      "integration_tree": "531790238038eee6f8bcea284dec2ee46f3ee443",
      "paths_sha256": {
        "docs/W10_S5D_PAID_ACCESS_GUARD.md": "1b52332259919403394c2fc5129c05da5c35b7e2f6af9df5f6be026e6d6d9b2d",
        "reserved/billing/paid_access_guard.py": "ffd789ceea316dd7ff2f6fea35f6383b623e8a71fa9ed937d90219cff5b0dd5d",
        "tests/test_w10_paid_access_guard.py": "3e0142887f5e7436eeabb77fd7cfb53e845d0d5f72e97901bd441ff35cfc2914"
      }
    },
    "W10-S5D-lineage-correction": {
      "accepted_checkpoint": "64600d9764209e2bdae8b2d72350c3a424fe4c98",
      "accepted_tree": "64463d3d586c31fd8757907399132f73caa2455f",
      "integration_commit": "7a1dbdbb27b2132d62c92ea4b965e81436f72f85",
      "integration_tree": "64463d3d586c31fd8757907399132f73caa2455f",
      "paths_sha256": {
        "tests/test_w10_paid_access_guard.py": "af06fce5f545a8718fcc7e01646097a36649c8674b9c4b12e6e3552e39f45530"
      }
    },
    "W10-S3C-runtime-entitlement-admission": {
      "accepted_checkpoint": "b458f2df20aa29aa73b1cc56de2126cb1c26405a",
      "accepted_tree": "3d56de032c2602e4804f71b36aa23e059d2f46de",
      "integration_commit": "be417aed05a99199ee2bc54679ca598551947f95",
      "integration_tree": "22da632b2e2e3de815f291bb6e06d80a849d038d",
      "paths_sha256": {
        "docs/W10_S3C_RUNTIME_ENTITLEMENT_ADMISSION.md": "f3f301a4063285f59957cb7189b56cf209a5cb85d939ccbd09dd39eff5289bd8",
        "reserved/billing/runtime_entitlement_admission.py": "cf6e6fa53d3c101ab239a64f23edd4dad92dda49b09874e5cf990b2de758118d",
        "tests/test_w10_runtime_entitlement_admission.py": "30fd92fcc81a9d466e1efc343a1d9871ede390b8dde6ab5d483ae3f5986c6621"
      }
    },
    "W10-S3C-source-sentinel-correction": {
      "accepted_checkpoint": "3111556b3b3f93c84c024303c1845e9b3d808dff",
      "accepted_tree": "9444d4be49b21031076a91640a25995fe5b954c7",
      "integration_commit": "e145e43631f9a03df70a378ac1eafbdf3974afa9",
      "integration_tree": "c2d3ae3d3cbcacfd28b57980951c781ecb2fa4ee",
      "paths_sha256": {
        "tests/test_w10_runtime_entitlement_admission.py": "6d8ce58988028b049c8f7946b9c02b85610c2e399ce2fc506155c5467f97063e"
      }
    },
    "W10-S3C-integration-lineage-correction": {
      "accepted_checkpoint": "5e6ea885a371bb15aaba3bf8abb5bb81a99f6c2e",
      "accepted_tree": "585c3364cfb7bafeecdaf7c1af7a2b804202e6df",
      "integration_commit": "5e6ea885a371bb15aaba3bf8abb5bb81a99f6c2e",
      "integration_tree": "585c3364cfb7bafeecdaf7c1af7a2b804202e6df",
      "paths_sha256": {
        "tests/test_w10_runtime_entitlement_admission.py": "9689394f29f2abe019ce6aa4b4fd7593a36ddfabd71008757d2f19252e7fa4b2"
      }
    },
    "W10-S7A": {
      "accepted_checkpoint": "699aba7facddf935b0b71797bca0abf17628dff9",
      "accepted_tree": "24771275bdea2c24bec6768c88f6206677a5bd47",
      "integration_commit": "54a82476939dce8f75af62d73aeb477e11a1260c",
      "integration_tree": "26b1aa6a1302195770534dc41caf099bcdd7cb06",
      "paths_sha256": {
        "docs/W10_S7A_BILLING_THREAT_MODEL.md": "7a5fc31ac4569e57e91784d70a7584f7fe8f4cd702e9d2363b12b008bca38a5b",
        "tests/test_w10_billing_threat_model.py": "77b9ec4feffecd0acd8383165da8e92faffa200122479fd94a8da00879e1355b"
      },
      "post_merge_live_binding_values_requiring_reconciliation": {
        "docs/W10_S7A_BILLING_THREAT_MODEL.md": "d40a84890ae8b244d86501efda5a47e0ad51e98975139ec9000d0d7202ca8eee",
        "reserved/web/v2.py": "dd4bcc1ec49793065da525fefd26709522ce12f5560fd3ee6af7b72ca27ae228",
        "tests/test_w10_billing_threat_model.py": "89bc0d0e53d7d9eed292b7e3c351c2441722598f3a2dbcb7eb248ebe01f5b270"
      }
    },
    "W10-S7A-reconciliation": {
      "accepted_checkpoint": "06eec249369cd71c1b6ff8dfaec94bf32b4fbb67",
      "accepted_tree": "f942f27a7aae169c9fb6cbdf4797a80bd3df7288",
      "integration_commit": "1d91526d11b5291d5388c78940682ca02edeb61e",
      "integration_tree": "e2fc725961f816d80eed9e5373d738e5e21a024c",
      "paths_sha256": {
        "docs/W10_S7A_BILLING_THREAT_MODEL.md": "85303c4d1ed36b974d67bec38622d19586e8b478d8321b48b8035970c61f679b",
        "tests/test_w10_billing_threat_model.py": "d7aa986064f828b77f2dfa493e28e8cb0cd46033808245ecf22f030b2211f8fa"
      }
    },
    "W10-S2E": {
      "accepted_checkpoint": "4511e45297dfcae980c606e4bb09b549510ea23f",
      "accepted_tree": "cd6bdf2f66878aa4baecd79d5e7c504dd13a4007",
      "integration_commit": "251deb1c39bbc4f5b4c7c3b1356a380cb0b9df04",
      "integration_tree": "ec382c130c4120fcab8b87a1711c696c0b661015",
      "paths_sha256": {
        "docs/W10_S2E_TAX_INVOICE_PREREQUISITE.md": "3b2535493bd39dc25ff879f4eb2dfd901e52dc2df65a1c46dee4fa5e4e88f04b",
        "reserved/billing/tax_invoice_prerequisite_contract.py": "325401be223975383bc80f5b4d0c0b8ab679fbae8127200ef294066a8dfe3bc0",
        "tests/test_w10_tax_invoice_prerequisite_contract.py": "541498152bf7f63cf525d646a1d72495a9698c0d7068f6a46198783d29588ca7"
      }
    },
    "W10-S2F-Q1-Q2-policy-closure": {
      "accepted_checkpoint": "2f0e8f0bb3377341b97dbfa760f9fb6aa529d3c9",
      "accepted_tree": "526ff18bf883e4643fd18fe7d2865c486c2d468b",
      "integration_commit": "e78a3a4bfaef16357512ec01f4e7c9619932e95f",
      "integration_tree": "2958a81e0acbbe8d11afc3e65e8d9033fdce642b",
      "paths_sha256": {
        "docs/W10_S2F_Q1_Q2_POLICY_CLOSURE.md": "3ba4450408637677f490ff62d3e940cda5d5c2a8570ff8640fdc6d9327fa8f78",
        "reserved/billing/q1_q2_policy_closure.py": "c758bedb6dd6812c7625a9e49f97eaa6c0440b9ef8e1a78219323f6167f14e04",
        "tests/test_w10_q1_q2_policy_closure.py": "6d4e60977b824f711676d6a4eef4ccfeedbdc55928c26073fdd381e916b6b5e4"
      }
    },
    "W9-S3C": {
      "accepted_checkpoint": "c9bdaa6538d68c0c64b2dcde97f224a69c089d30",
      "accepted_tree": "6d851e6010b8c143c57e63aea61afb8911b1bab1",
      "integration_commit": "5f5a948891e1e812a5c74ff6c7266d153bb492fa",
      "integration_tree": "639369d06a8da75e8318bec7933993c26e39ace6",
      "paths_sha256": {
        "docs/W9_S3C_PROJECTION_REPOSITORY_ADAPTER.md": "240046f6fb7ebb06a94ec1d235998071938e28112aa46bd20367c363b5a22a03",
        "reserved/annual_position_projection_repository_adapter.py": "052712341ab06ca1cdabd407bfacc1ee4cd1603ba3c49f7fc95575465311d9dd",
        "tests/test_annual_position_projection_repository_adapter.py": "6451b194b671ae1dfdbf9977a8dbb8c56665cf975fa84f87c886a52ac78d9523"
      }
    },
    "W10-S4B": {
      "accepted_checkpoint": "e5ba0ed4f5e3832fe4ef58af8009cc17217bc85d",
      "accepted_tree": "d697bf4af962e459f3ce43e146192c82e8d8b1d6",
      "integration_commit": "23f4d3dc742474d3a672388a1ebe99962505b234",
      "integration_tree": "b85207f9c7dd50042206a0aa43391300f69374b6",
      "paths_sha256": {
        "docs/W10_S4B_CHECKOUT_INTENT_CONTRACT.md": "86e8aac7ae306b0971afd7f9938831f4e7cae97800b966ce58d6e3952bd69a72",
        "reserved/billing/checkout_intent_contract.py": "ff805233b46aabc1f18a1b3def0b849ecd88f6f86e2b5d4b35ae96729b6fb7e0",
        "tests/test_w10_checkout_intent_contract.py": "482ce9ff7b70f1b8a9c66961db5133504f3fbd90d6f419ef3385d39056ce89fd"
      }
    },
    "W10-S4C": {
      "accepted_checkpoint": "b197c987b96dd9fca6296c41bb002baf74099e55",
      "accepted_tree": "4c43bd2afcfe40d18f58f3ac85e531f81477f7b8",
      "integration_commit": "67b52a66805e9d5c1317330b9f7b1f2a19d4172c",
      "integration_tree": "80406ea9aab57c0a3bebc55752ef60977a9de2b0",
      "paths_sha256": {
        "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md": "53509b94d9004fc76f724e8b99d932c9dd8ba22af6723c105d69673897b30313",
        "reserved/billing/portal_intent_contract.py": "f3f021bc05233cd5c4714c68e6eb57127f7722cc6685ea56e8c7a6e6de008d33",
        "tests/test_w10_portal_intent_contract.py": "00f2b6f64d169bb59842c3e506c209747c6697a550d32d911588fd4dde3c6984"
      }
    },
    "W10-S6E": {
      "accepted_checkpoint": "ddd9dd298eb8c495402d06ca4ac921a34d885549",
      "accepted_tree": "83035e65132091bce86ed652a3d2970ada44804c",
      "integration_commit": "11ea4cfea78ae31b633a9ac8d99477eb358e7f3b",
      "integration_tree": "e6dc561505058e45cddb27bab4ad9d3c1605e4f9",
      "paths_sha256": {
        "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md": "d48c47463f1db9411ba291d8e26cfe3c71bbd6f23e49f636789c099c271f63ae",
        "reserved/billing/payment_recovery_presentation.py": "48d49f28136690f5be8a6cdf0dd927f9e3f0d0ffa0972d1daa0b60f5f23c42e8",
        "tests/test_w10_payment_recovery_presentation.py": "b3fa8047f7818f92a24ca5002d5351021eca259df10591eaff4ca0334320653b"
      }
    },
    "W10-S6F": {
      "accepted_checkpoint": "9c7b5c7b283134a471d5c5d7a720e4c10b1a16a6",
      "accepted_tree": "b2edd687819b5b0f95c44f1a68d746a85f7bd9c1",
      "integration_commit": "fd7f30dcdc3557ef70c9bdfc4b89e046e16c2bd0",
      "integration_tree": "b2edd687819b5b0f95c44f1a68d746a85f7bd9c1",
      "paths_sha256": {
        "docs/W10_S6F_CANCELLATION_PRESENTATION_EVIDENCE.md": "151d1ac3929813d742a1609a2acde66fa920091277caa98cb88f75440a7619f4",
        "reserved/billing/cancellation_presentation.py": "0f8d252f6a5556333187856e527fcdf02197572baebef1a0edc4c71999d0946d",
        "tests/test_w10_cancellation_presentation.py": "f94e00781725f14ae580f5e56bdcff6933158e91c328eceb69b82321ac93caaa"
      }
    },
    "W10-S6G": {
      "accepted_checkpoint": "9ff214418bf42f7877bdabde550df5d2300983de",
      "accepted_tree": "106c09ae1f5ec0f6da64827b4402a75fd02feb1a",
      "integration_commit": "2690c9335ca8073b1723846cccf33c15f9ff727f",
      "integration_tree": "c5ee5ef6cde1272288c6e60325747c6d9752b99c",
      "paths_sha256": {
        "docs/W10_S6G_INITIAL_PAYMENT_PRESENTATION_EVIDENCE.md": "ae5318ddfed40ba11cf0942f248224d89b14f71e2620b9502b67650350f7e267",
        "reserved/billing/initial_payment_presentation.py": "009970f3217bee7dddc59471f02ce801d8992e7d92b951f41a7ee97cc2bd5451",
        "tests/test_w10_initial_payment_presentation.py": "7a3c789a44d14200da92993884cbe5d3d0bf7e9f0305778e93e68b711142f0e5"
      }
    },
    "W10-S6H": {
      "accepted_checkpoint": "b45a8050e728bf457ab2508de4d64d88f40b5253",
      "accepted_tree": "773aea8429967dc086ac0ced2f38302b8998fc7c",
      "integration_commit": "8fdcc0414c72393c4f575f7597bd30850b707d35",
      "integration_tree": "773aea8429967dc086ac0ced2f38302b8998fc7c",
      "paths_sha256": {
        "docs/W10_S6H_INITIAL_PAID_PRESENTATION_EVIDENCE.md": "14346e3020c46f0625bf905565515e9cea68c88ab5920907c72b1630508de19a",
        "reserved/billing/initial_paid_presentation.py": "cdb3d75d109bcaabe281f07f22675b785d40406bca685f6892b3085c45208b6d",
        "tests/test_w10_initial_paid_presentation.py": "ed4bcd6d9667238408da751e8dc41db7b58413d34ec98a329fb7e66a2e00949d"
      }
    },
    "W8-W10-lifecycle-composition": {
      "accepted_checkpoint": "318aca386c960f7993b1ade5cb6b57bcfe28de00",
      "accepted_tree": "1485401624cb59a685678bdc4917513f4915e05e",
      "integration_commit": "584ff7f31009913706d3427c38a986bbfa6799d2",
      "integration_tree": "1485401624cb59a685678bdc4917513f4915e05e",
      "paths_sha256": {
        "docs/W8_W10_SUBSCRIPTION_LIFECYCLE_COMPOSITION_EVIDENCE.md": "d14bcbbcc08dcfe59b8c2380cd53f29378c5efc7e5ef46e9e00fddf2a5cc5556",
        "tests/test_w8_w10_subscription_lifecycle_composition.py": "60c9863bf5aad27b192115e7b990536051848c9721f35ae49d519f6395bce75b"
      }
    },
    "W9-S3D": {
      "accepted_checkpoint": "98e4887e038f9ada1f090b0723837f3cb49eb8af",
      "accepted_tree": "9b2b2fe6d27d7c36759dfbd368f4a764058e58c8",
      "integration_commit": "5f7b76408a5d72b71be71d0e5d6c7a6edde260b7",
      "integration_tree": "c04c45a9ee33788655061d7a9fff7e0e1d953f75",
      "paths_sha256": {
        "docs/W9_S3D_AUTHENTICATED_OWNER_ADAPTER.md": "da71daaa29c7a2ef56270e6b18df49e405d7518c54297c774290bde642af768c",
        "reserved/annual_position_authenticated_owner_adapter.py": "1eb19a1ae55caeb03b8e0ee2f2f05d8917546c844cf5610c9c7371b30e8dc16a",
        "tests/test_annual_position_authenticated_owner_adapter.py": "d2b58aaa56949654f419088ec52f500af3630068202a65e11bc0a1884cbd2f63"
      }
    },
    "W9-S3D-source-ancestry-correction": {
      "accepted_checkpoint": "2ccafb00047583979e55e0ebb4fb193f17abe659",
      "accepted_tree": "536c13528733794fe9ad5c3fd27f44812170fae9",
      "integration_commit": "b8ce971f4dc6b8a1ced10e9b490be68d481752de",
      "integration_tree": "7fcc5be531c5a4331e6a7ff65ce18a33e1772766",
      "paths_sha256": {
        "tests/test_annual_position_authenticated_owner_adapter.py": "d81f068dd95adfcca35b933caabc3dffbddf0600cbb06b24b62c3b3cbd3b4c92"
      }
    },
    "W10-S6E-test-scope-correction": {
      "accepted_checkpoint": "cd6f94bc5109d18cb229fa65396bb66677960543",
      "accepted_tree": "3c259ae83571fffbfbc3ba3591eedfdf5b3bb3ce",
      "integration_commit": "8043051a38f367ef66fd63034bc7a4fcbc7c9f3c",
      "integration_tree": "664955b5bc5a5604396a88e7f7bc6355aafc230c",
      "paths_sha256": {
        "tests/test_w10_payment_recovery_presentation.py": "0741f05750a9063894175a942f387f372c4e7d26176b5119ee0f37611783f048"
      }
    },
    "W10-S3A-hardening": {
      "accepted_checkpoint": "b990d514a929c37b3f999137a0e383d05c37f0df",
      "accepted_tree": "78a9f59a238eea1316855ccef1784a2588ffb961",
      "integration_commit": "48a97042fc0e17997bf2d23a4687e79c20b74b9e",
      "integration_tree": "dbed2a8e3803325c952d822ad68477eecf837001",
      "paths_sha256": {
        "docs/W10_S3A_ENTITLEMENT_TRANSITION_EVIDENCE.md": "fafd93c1a8fa65428bd3af19c1f35e9b47b10f38f68312721e6f2a5e14943f0d",
        "reserved/billing/entitlement_core.py": "201c92c1093b663b786a5e49a1c2ca0d714f3fe6fdaebf18c0c7d486ef25f415",
        "tests/test_w10_entitlement_core.py": "25b44fe0d580a72aedf4791463feecf5ea150d8c72d45b1b00e39f400df74a2a"
      }
    },
    "W9-W10-entitlement-evidence-reconciliation": {
      "accepted_checkpoint": "cd3f043e77b724d3f20b520e488b99d8514e5e3d",
      "accepted_tree": "47480505b30bd4fd90ce0ce23fb70587613374f3",
      "integration_commit": "4e1f226e2109257e46e5865fe471564df1758246",
      "integration_tree": "47480505b30bd4fd90ce0ce23fb70587613374f3",
      "paths_sha256": {
        "docs/W10_S2B_FAIL_CLOSED_LAUNCH_DEFAULTS.md": "617ca21d3555bef8944f9d4173c0dc432816817fb2a73d9f1566380bbf8b9703",
        "docs/W10_S2C_POLICY_EVIDENCE_DOSSIER.md": "838e6c649f9925e86aca280da6917cc7e650860880204cf06b34a8fc4aa2572f",
        "docs/W10_S2D_BILLING_ACCOUNT_RECOVERY_CONTRACT.md": "2d7f542851e94e00596d33a686412be86de32049edde5a867bca9d1b5b61778b",
        "docs/W10_S4B_CHECKOUT_INTENT_CONTRACT.md": "3912255859176ab5ae928d28bb94910a880f11cad32f48745e77f69450c74315",
        "docs/W10_S4C_PORTAL_INTENT_CONTRACT.md": "87f4cc5b95094375008742ff0d4b9e4d4a07c56f1f523f6603820f99375a4217",
        "docs/W10_S6E_PAYMENT_RECOVERY_PRESENTATION_EVIDENCE.md": "d0d9db85d6b0fbde7db9e30d9a7ff2d8a3bfa13d9cc6a94238b4cc5e24860c69",
        "docs/W10_S7A_BILLING_THREAT_MODEL.md": "fcdb3acb21102f06ac6be9691d8e3a25da016b9a800844cddd8df7324db84611",
        "docs/W9_LAUNCH_DATA_FLOW_AND_THREAT_MODEL.md": "7eec83893b05e342b5b4441b0b004499bc739b30c32c115ae752beeb9c2d0ee0",
        "tests/test_w10_billing_account_recovery_contract.py": "ef5e07d5213a0e6724f26d0c5ebc191a762e61f6805e366ec7a98c536d944101",
        "tests/test_w10_billing_threat_model.py": "1db37c6ff1853fde3cfafbc3aee97eb5eca29946c97fa716cae1d2056349d5c9",
        "tests/test_w10_checkout_intent_contract.py": "30752be98567c039f32972179e20a1e56370627b3cd6bb56d5198ae6a1dd6752",
        "tests/test_w10_fail_closed_launch_defaults.py": "cb40ef6f6d6967e6c99a586a87e49c91bf7c1507acf1c869da3220f3db667dab",
        "tests/test_w10_payment_recovery_presentation.py": "382aab611cfe23d8e15d58355e5a553fe739d164f4a737763965960bcf8292ce",
        "tests/test_w10_portal_intent_contract.py": "6817c9f687f19241015e1d57f658c2ddabe0471f796933dc6c7234985155e8f4",
        "tests/test_w10_s2c_policy_evidence.py": "0a36f82a965c2bb205c81752b070d685a271744cf14b212ae4d4070f8b77b5bf",
        "tests/test_w10_tax_invoice_prerequisite_contract.py": "1b71ef96c464eb314e1673803574d6d477203f01c0abf5982e36247f78e62f67",
        "tests/test_w9_security_evidence.py": "972cca0373820706342a5576b4a40c36be77b8223a9bcc9ace3c4e2539271cb7"
      }
    },
    "W9-evidence-package-history-correction": {
      "accepted_checkpoint": "431a859731bc0b480e47feca643c299abbdfb003",
      "accepted_tree": "9d0588c3d6761c21724b27fcc6ff412e6447f285",
      "integration_commit": "109b5ec6e3ace82d8e41c98ece1baf7553eff039",
      "integration_tree": "9d0588c3d6761c21724b27fcc6ff412e6447f285",
      "paths_sha256": {
        "tests/test_w9_security_evidence.py": "26a1e1ab0cce8095cdba93655fe4e0043235e3c6e04b7b0220cee3761cfc4524"
      }
    }
  },
  "historical_map_bindings": [
    {
      "commit": "5612f7a33f27f09d1fa988f15dfdffbe77a72705",
      "tree": "4786614d7ea428e3aea1d61a72dc74d9aad6bd92",
      "sha256": "7af205f420c2cf3a9039fff7aad1af65e55221005231b2fabe3bd99c94f96c4d"
    },
    {
      "commit": "f9412b36adeb75dc7d5d5af56824c87235f28ce7",
      "tree": "1b648be16bdc2bc41311f7968f6d402a63d4c8a9",
      "sha256": "cd17168c04ed5c3b05044322daae2480973d57220f05c0419f539f6fdf14977d"
    },
    {
      "commit": "aaa08d7b541ed49765f9d9c68bf1d91d4f34faf3",
      "tree": "bbd545baba7e93c160716df7246cec8152ca7944",
      "sha256": "f5c3e945e3b77a35c0716f8018deb19a831fbe3b10596236d46cdd5c45e0892e"
    },
    {
      "commit": "47d2ae9c1faf220789bc8ec75f7898c3dca4651a",
      "tree": "5d9ab24a68832482ceb3314ca335b54f102ea4da",
      "sha256": "19628e1c8638356d8250986830697e764be1aa0e9c02df958817607d2544fabf"
    },
    {
      "commit": "15335ad003687b8f6a08020de548fa0c59a45882",
      "tree": "56c443d0ceb1f7bf261e81442f35b8820a78ae6d",
      "sha256": "518947a496aebbcbeaa87db912c12367394fdbccc52c7f7bc4f41a48b5ea105b"
    }
  ]
}
```
<!-- W10-COMPLETION-MAP-RECONCILIATION-END -->

### Settled Founder authority (`FD-W10-001`)

- Reserved is a paid subscription product at the October launch.
- Initial customer-facing prices are **£29 monthly**, **£156 for six months**
  and **£288 yearly**, inclusive of VAT where applicable.
- These are initial, changeable prices rather than permanent price promises; a
  later change requires a later Founder Decision.
- The minimum ability to sell, grant and administer access is in October scope.
- Special discounts and offers must be supportable.
- Unrelated commerce, marketplace and reseller scope is not authorised.

### Settled provisional provider and lifecycle authority (`FD-W10-002` / `FD-W10-003`)

Both decisions are durably recorded in integration ancestor
`10fb93e2e6ab567a72d2370c1603768a7ac04bb5`.

- Stripe Billing, Stripe Checkout and Stripe Customer Portal form the
  provisional disabled-first subscription baseline; Stripe Connect is excluded.
- Paid access starts only after verified successful initial payment and renews
  automatically for the selected paid plan.
- Cancellation stops future renewal while ordinary access continues through the
  already-paid period.
- The first verified failed-renewal observation enters the explicit canonical
  `payment_recovery` state for exactly seven calendar days. Ordinary access may
  continue during that bounded state; duplicate/repeated failures cannot extend
  it; verified recovery returns to ordinary paid state; unresolved expiry
  suspends ordinary access.
- No October free trial or free tier is authorised.
- Provider events and labels are observations, never direct entitlement flags.
- This authority remains provisional and does not accept provider terms, approve
  credentials, activate billing, settle VAT/invoice treatment or authorise a
  charge.

### Settled current-period full-withdrawal authority (`FD-W10-004`)

The independently reviewed authority checkpoint
`ab4f8d4d34aa4b80022018b2b15315d5ff72ebb5` is integrated at
`22512f29ed17dbc9a13a8741891345eb54513d05`.

- A verified full withdrawal attributable to the payment funding the current
  subscription period suspends ordinary paid-product access at the next
  authoritative entitlement evaluation, without another grace period.
- Public, authentication, legal, privacy, data-access/export, billing-recovery,
  cancellation and appropriate support surfaces remain reachable under their
  existing controls; no account or data deletion is implied.
- Open, partial, ambiguous, contradictory, stale or unresolved withdrawal
  evidence does not suspend valid existing derived access solely on that basis
  and can never create, restore, extend, prolong or strengthen entitlement.
- Provider observations have zero direct entitlement authority. Restoration
  requires an authoritatively verified and admitted reinstatement,
  provider-reversal outcome, successful replacement payment or other already
  authorised entitlement-establishing fact.
- This authority does not settle discretionary refunds, exceptional support,
  statutory remedies, wider disputes, data retention or account closure, and
  supplies no provider activation, production, credential, payment, release or
  go-live authority.

### Fail-closed defaults and genuinely unresolved subordinate policy

Six Founder-settled policy keys are explicit. Integrated S2B at
`1033c9fbef008dcd33125a0b14e7fb18b8846d19` closes four further keys only as
ordinary engineering defaults under the accepted fail-closed boundaries:
promotions/discounts remain a reserved capability but inactive; partner offers
are disabled and unsupported; ordinary mid-cycle plan changes, proration and
immediate cancellation are disabled while paid-period-end cancellation and the
mandatory statutory/consumer-rights override are preserved; and no manual
entitlement override exists, with corrections limited to append-only observation
and reconciliation with zero direct entitlement effect. These details are not
represented as separately Founder-settled policy.

For historical continuity, the preceding S2A checkpoint described six settled
policy keys and nine policy keys unresolved. The accepted S2B defaults reduced
that remainder to five without retroactively expanding Founder authority.
Integrated S2C at `a07348976321df65bbd95c9170c906bcddd5baa5`
truthfully records its then-current classification: Q1 refunds, Q2 paid-access
surface and Q3 post-settlement consequences were Founder questions, while
tax/invoice and owner-bound no-transfer recovery were specialist gates. S2C is
historical evidence and is not rewritten to pretend it reviewed later closure.

Accepted S2F checkpoint `2f0e8f0bb3377341b97dbfa760f9fb6aa529d3c9`,
integrated at `e78a3a4bfaef16357512ec01f4e7c9619932e95f`, closes Q1 and
Q2 as bounded ordinary engineering policies under existing `FD-W10-001`,
`FD-W10-003` and `FD-OA-001` authority. Q1 sets a fail-closed October refund
baseline: no discretionary refund promise, no automated refunds and no
support-issued discretionary refunds. Mandatory statutory and consumer rights
continue to override that baseline and still require accepted specialist
treatment and an approved escalation path. No refund action or refund-derived
access consequence is implemented or invented.

Q2 settles the accepted S5A customer-product class
`authenticated_product_candidate_pending_founder_decision` as requiring paid
entitlement because October is a paid subscription without a free tier. The
other accepted S5A classes retain their existing S5A/S5B/S5C treatments. This is
a policy boundary only: client-side hiding is not enforcement, and no
server-side paid-entitlement guard is supplied by S2F.

`FD-W10-004` closes Q3 and the
`post_settlement_dispute_chargeback_reversal_consequences` policy key at the
Founder-policy layer. Exactly two policy keys remain unresolved: tax
invoicing/additional VAT presentation and billing-account recovery. Tax/invoice
requires accepted finance/tax/legal evidence; owner-bound no-transfer recovery
requires accepted security/privacy/operations and target evidence plus durable
authenticated engineering implementation. Those two remain
specialist/engineering evidence gates under existing authority, not new Founder
questions. Post-settlement provider authentication/admission, sandbox event
evidence, legal/finance/support/fraud treatment, target reconciliation, recovery
runbooks and runtime enforcement also remain open completion evidence under the
settled rule. None may be silently inferred from a provider default. S2 remains
incomplete until the two unresolved policy keys and all applicable implementation
and specialist evidence are accepted.

Integrated S2D at `509c5360d453e23a0732e4e9d4637385eef20ef6`
implements only the disabled-first, owner-bound, no-transfer local decision
contract for the recovery baseline. It creates no authenticated adapter, durable
mapping, provider session, network action, entitlement, charge, refund,
transfer, merge, delegation, persistence or activation authority. Its local
contract evidence therefore narrows later implementation but does not satisfy
the remaining security/privacy/operations/target evidence or close the recovery
key.

Integrated S2E at `251deb1c39bbc4f5b4c7c3b1356a380cb0b9df04`
adds a detached, immutable, I/O-free tax/invoice prerequisite contract. Its
validators establish local structural and semantic consistency only; they are
not provenance, authentication, issuance, legal, tax, provider, delivery or
entitlement authority. S2E preserves the settled gross catalogue, the £29/£156
amount limb only (not £288), and every false authority and specialist gate. It
does not accept a VAT registration, rate, customer/location/tax-point fact,
invoice disposition or Stripe Tax configuration. It does not close the VAT/invoice policy key.

## Baseline finding and owned outcome

W10 owns a customer-to-billing-account-to-entitlement path that can quote one
of the three authorised plans, apply an explicitly configured offer, collect
and reconcile subscription payment through a selected provider, and enforce
and administer access according to approved lifecycle policy. It must be
owner-scoped, auditable, replay/idempotency safe, fail closed under ambiguity,
and independently demonstrated in the target environment.

The repository currently has a stable authenticated `users.id` boundary and
owner-isolation tests, but authentication alone grants every protected V2 route.
The integrated S1 catalogue/authority, S2B defaults, S2D local recovery
contract, hardened S3A lifecycle transition policy, S3B event-inbox contract
and S3C runtime-entitlement admission seam now have focused billing tests.
S3C composes exact owner-bound, content-identified admitted facts with S5D's
runtime decision shape, but remains route-less and non-durable. S2D, S3A and
S3B remain detached local contracts and S3C remains a local composition seam,
all with zero provider or persistence authority: there is
still no durable subscription/billing or owner-to-billing-account schema,
implemented event inbox, authenticated recovery adapter, provider authenticity
or persistence, globally latest durable state, global replay/fork prevention,
provider-authenticated entitlement decision, route-wired server-side paid-access enforcement,
provider-backed checkout/customer-portal route, billing webhook or provider SDK.
Authentication itself still lacks target-provider launch evidence.
The accepted S5A inventory provenance at `9c076019...` is refreshed for the
linked-HICBC route shape by checkpoint `8480264...`, integrated at `95dd628...`;
it inventories the exact 44 always-registered and 8 HICBC-conditional routes
and their observed access controls. Integrated S5B at `051ae665...`, with
downstream lineage reconciliation `d954ddc...` and sentinel `05134e5...`, reconciles the
eleven internal/admin/legacy/unknown entries to bounded fail-closed treatments:
preserve five Founder-only routes and the Capital Gains hard-404, retire or
redirect three legacy public paths, and make two internal assurance/provider
pages production-404. Integrated S5C product checkpoint `3c63e64...` plus
evidence checkpoint `e395996...`, preserved through merge `85e1250...`, implements
the five bounded legacy/internal route treatments. It does not decide or enforce
the paid boundary. Accepted S5D checkpoint `88a3c879...`, integrated at
`824b306...` and followed by exact lineage correction `64600d9...` integrated at
`7a1dbdb...`, implements a pure, route-less provider-neutral paid-access guard
kernel for the exact S5A paid endpoints. It fail-closes detached or inconsistent
inputs and models the `FD-W10-003` lifecycle plus `FD-W10-004` withdrawal rule,
but supplies no provider admission, persistence, route wiring or live enforcement.
Accepted S3C source checkpoint `b458f2d...`, source-sentinel correction
`3111556...`, integration commits `be417ae...` / `e145e43...` and integration
lineage correction `5e6ea88...` add the compatible owner-bound route-less
non-durable admission seam. That seam does not authenticate provider evidence,
establish global durability or the latest state, prevent replay/forks across
processes, wire a route or enforce access live. The initial S7A checkpoint integrated at `54a8247...`
recorded 21 open W10 billing threat/control gaps. Its accepted post-S2D/S5C
reconciliation is integrated at `1d91526...`; the later exact evidence-binding
reconciliation at `4e1f226...` and sentinel-history correction at `109b5ec...`
preserve that current lineage without closing any of the 21 threats or supplying security,
provider, target or launch assurance.

`docs/STRIPE_CONNECT_SPEC.md`, `reserved/providers/payments/base.py` and
`reserved/providers/payments/stripe_connect.py` concern the separate movement
of a customer's set-aside money. Stripe Connect is historical and unselected;
the disabled stub neither selects Stripe for subscriptions nor supplies billing
capability. Transaction-classifier uses of the word `subscription` describe a
customer's business expenses and are also unrelated. W10 may reuse general
security lessons such as signed webhooks, idempotency and reconciliation, but
must not reuse either domain contract as if it were subscription billing.

## Finite slices and evidence

| Slice | Smallest coherent outcome | Current state | Dependencies and completion evidence |
|---|---|---|---|
| **W10-S1 — authority and provider-neutral contract** | Encode the versioned initial plan catalogue and a fail-closed inventory of required policy inputs, while representing discounts/offers only as a required capability. | **Independently reviewed, checkpointed and integrated at `9e8f94a...`.** Exact authority, billing boundary, adversarial integrity and affected/full regression evidence passed. The slice remains short of launch-evidence-complete because later provider/target evidence is outside S1. | Preserve the exact integrated S1 authority and its 15-key denominator. S2 must consume its closure-bound validation/projector protocol, never mutable raw attributes or provider defaults. |
| **W10-S2 — provider and policy closure** | Record the selected billing provider and every launch lifecycle/access/promotion/invoice and post-settlement dispute/chargeback/reversal policy needed by later slices, with decision owner and rationale. | **S2A, S2B, S2C, S2D, S2E and S2F are independently reviewed, checkpointed and integrated; S2F's Q1/Q2 checkpoint `2f0e8f0bb3377341b97dbfa760f9fb6aa529d3c9` is integrated at `e78a3a4bfaef16357512ec01f4e7c9619932e95f`; `FD-W10-004` is accepted at `ab4f8d4d34aa4b80022018b2b15315d5ff72ebb5` and integrated at `22512f29ed17dbc9a13a8741891345eb54513d05`.** S2A encodes six Founder-settled keys and the provisional Stripe capability boundary. S2B closes four ordinary fail-closed defaults. S2C preserves the historical five-key classification. S2F closes Q1 refunds and Q2 paid surface as bounded engineering policy; `FD-W10-004` closes Q3's verified full-withdrawal suspension/restoration policy. Exactly two keys remain: tax/invoice and billing-account recovery as specialist/engineering evidence gates. Post-settlement implementation and specialist acceptance remain open under the settled rule. S2D and S2E remain detached, non-authoritative contracts. No S2 component supplies runtime/provider/persistence/refund/enforcement/launch assurance. S2 remains incomplete. | Obtain accepted legal/finance evidence for mandatory refund remedies and post-settlement treatment; finance/tax/legal evidence for VAT/invoices; security/privacy/operations/target evidence plus durable authenticated implementation for owner-bound recovery; and provider-authenticated post-settlement admission, reconciliation and enforcement evidence under `FD-W10-004`. Provider terms/DPA/fees also remain open. Complete only when every key is versioned and accepted and no runtime behaviour relies on an undocumented provider default. |
| **W10-S3 — durable billing and entitlement core** | Implement the owner-bound catalogue/version reference, billing account, subscription and settlement observations, event inbox, audit/reconciliation record and policy-derived entitlement boundary, including post-settlement dispute/chargeback/reversal observations without assuming their access consequence. | **S3A and S3B are independently reviewed, checkpointed and integrated at `94bd87f019dc226ec8c73f32515229189500cf06` and `5bc29bcb30c95ea7a5a9430104653b366d709eb6`; the corrected S3A lifecycle is accepted at `b990d514a929c37b3f999137a0e383d05c37f0df` and integrated at `48a97042fc0e17997bf2d23a4687e79c20b74b9e`; S3C is accepted at `b458f2df20aa29aa73b1cc56de2126cb1c26405a`, integrated at `be417aed05a99199ee2bc54679ca598551947f95`, source-sentinel corrected through `3111556b3b3f93c84c024303c1845e9b3d808dff` / `e145e43631f9a03df70a378ac1eafbdf3974afa9` and integration-lineage corrected at `5e6ea885a371bb15aaba3bf8abb5bb81a99f6c2e`.** The hardened detached entitlement core preserves exact lifecycle history and models the first verified failed renewal as `payment_recovery` for exactly seven calendar days: ordinary access continues during that non-extendable interval, verified recovery restores paid state, and unresolved expiry suspends access. S3C adds an owner-bound route-less non-durable admission seam compatible with S5D's exact decision projection. Provider labels have zero direct authority. S3 remains incomplete: these local contracts/seams supply no database schema, migration, implemented durable inbox, provider authentication, global durability/latest-state ordering, cross-process replay/fork prevention, route wiring, persistence or live enforcement. | S1 and the relevant S2 policies; accepted S3A/S3B/S3C semantics; W9 datastore, retention, encryption/key-custody and erasure decisions. Still required: durable billing-account/subscription/event-inbox/audit/reconciliation records; migrations; exclusive shared-file ownership and concurrency controls; authenticated event source; globally ordered replay/fork-safe admission; dispute/chargeback/reversal and correction/deletion/retention tests; independent schema/security/privacy review. |
| **W10-S4 — provider adapter and collection lifecycle** | Implement disabled-first provider customer/checkout/management, verified webhooks, reconciliation and offer primitives against the provider-neutral core. | **S4A is independently reviewed and integrated at `2ad4a63dd1f10ba38859050b47245c28390667d8`; S4B disabled Checkout intent is accepted at `e5ba0ed4f5e3832fe4ef58af8009cc17217bc85d` and integrated at `23f4d3dc742474d3a672388a1ebe99962505b234`; S4C disabled Customer Portal intent is accepted at `b197c987b96dd9fca6296c41bb002baf74099e55` and integrated at `67b52a66805e9d5c1317330b9f7b1f2a19d4172c`.** They remain network-inert, non-entitling intent/edge contracts. S4 remains incomplete: no SDK, credential, webhook endpoint, persistence, provider session creation, charge or activation is present. | Preserve S4A-C's exact disabled-first boundary. Completion still requires applicable S2 policies, S3B-compatible durable identities/event inbox, approved credential custody, accepted provider terms/security boundary and sandbox access. Synthetic and sandbox tests must cover successful, declined, delayed, duplicate, replayed, out-of-order, forged, refunded, post-settlement disputed/charged-back/reversed and recovered cases. No configuration or credential alone may enable it. |
| **W10-S5 — server-side access and administration** | Apply the approved entitlement decision, including explicitly approved post-settlement dispute/chargeback/reversal consequences, to every in-scope paid surface and supply least-privilege, audited support/admin correction tools. | **S5A and S5B are independently reviewed, checkpointed and integrated at `9c0760192bb2420b90e57ec7313f69bbe52cbf74` and `051ae665a0cc94f6e9cdbbc728c621825c7769fe`; S5A's linked-HICBC refresh `8480264e664a91a26c062e371b12192f9a628a4a` is integrated at `95dd628e27f7261282f2ecf55d4cf29720329b91`, followed by downstream reconciliation `d954ddcc88466967cc16efcaba02778e03a0f9a2` and lineage sentinel `05134e536d0428e0bcdfab96a109d64f46d2d9a4`; S5C product `3c63e64e478957ce04ee1154363c2eae94b82b30` and evidence `e3959964ca08bd5afb6f75feab4ec0fdc83a9423` are preserved through integration merge `85e1250f53180bb3c1aff111c17101b9e59df080`; S5D product `88a3c879fbacad9e3f9feebe02764499f1f53daa` is integrated at `824b3060c950ce7f623d29aeadc53ede34b6c565`, with lineage correction `64600d9764209e2bdae8b2d72350c3a424fe4c98` integrated at `7a1dbdbb27b2132d62c92ea4b965e81436f72f85`.** Refreshed S5A source-binds the exact 44 always-registered and 8 HICBC-conditional routes and their provisional classes. S5B source-binds exact treatment of all 11 internal/admin/legacy/unknown entries. S5C implements five bounded legacy/internal route-hardening treatments. S2F settles the accepted `authenticated_product_candidate_pending_founder_decision` class as paid-entitlement-required. S5D adds the independently reviewed route-less provider-neutral guard kernel for the exact 25 paid endpoints and encodes fail-closed `FD-W10-003` lifecycle and `FD-W10-004` withdrawal consequences. S3C supplies the compatible owner-bound route-less non-durable admission seam, not provider authentication, durable/latest-state authority, route wiring or live enforcement. S5 remains partially implemented but incomplete. | Preserve S5C's route closures, refreshed S5A/S5B evidence, S2F's exact paid-surface classification, S5D's route-less guard boundary and S3C's exact compatible seam. Still implement provider-authenticated durable/latest-state admission and separately wire the accepted guard server-side only against applicable S2/S3 authority. Test cross-user, stale/unknown, revocation, cache, concurrency, replay/fork, direct-URL/API bypass and admin separation; authentication or client-side hiding never substitutes for server enforcement. |
| **W10-S6 — customer billing journeys** | Deliver truthful plan/offer presentation and the approved checkout, success/pending/failure, renewal/cancellation, invoice/receipt/refund, post-settlement dispute/chargeback/reversal and account-management journeys. | **Partial local implementation.** Integrated S6A–D work provides plan presentation, a safe renderer, an authenticated plans preview and an authenticated plan-selection preview (`45ade8e...`, `23d04a6...`, `3e05fb7...`, `46e2141...`). S6E is accepted at `ddd9dd298eb8c495402d06ca4ac921a34d885549`, integrated at `11ea4cfea78ae31b633a9ac8d99477eb358e7f3b`, and followed by the accepted test-scope correction integrated at `8043051a38f367ef66fd63034bc7a4fcbc7c9f3c`: it truthfully presents explicit `payment_recovery`, its exact non-extendable seven-calendar-day window and deadline suspension, with provider observations granting no access authority. S6F is accepted at `9c7b5c7b283134a471d5c5d7a720e4c10b1a16a6` and integrated at `fd7f30dcdc3557ef70c9bdfc4b89e046e16c2bd0`: it presents a detached zero-authority cancellation/end-of-paid-period view and cannot cancel, mutate, persist or grant access. S6G is accepted at `9ff214418bf42f7877bdabde550df5d2300983de` and integrated at `2690c9335ca8073b1723846cccf33c15f9ff727f`: it presents detached initial-payment pending/failure copy and cannot begin paid access. S6H is accepted at `b45a8050e728bf457ab2508de4d64d88f40b5253` and integrated at `8fdcc0414c72393c4f575f7597bd30850b707d35`: it presents a detached initial-paid/automatic-renewal candidate only from exact caller-supplied structural facts and grants no access or provider authority. Early-W8 lifecycle-composition evidence is accepted at `318aca386c960f7993b1ade5cb6b57bcfe28de00` and integrated at `584ff7f31009913706d3427c38a986bbfa6799d2`; it verifies local compatibility across the detached entitlement, S6E, S6F, S6G and S6H contracts through test-only projections, not runtime admission. These packages do not provide provider-backed checkout or complete lifecycle journeys and S6 is not counted complete. | Preserve those components. Completion still requires S1 catalogue; relevant S2 policy; stable S3-S5 contracts; provider-backed checkout/account-management states; admitted event and selected-plan provenance; live access-control integration; exact price/VAT copy review; accessibility/browser evidence; no surprise renewal or invented refund/grace/dispute outcome; and clear recovery/support paths. |
| **W10-S7 — billing security, privacy and operations** | Close W10-specific abuse, privacy, reconciliation, monitoring, support, recovery and incident controls without duplicating W9's general control plane. | **The initial S7A checkpoint was independently reviewed and integrated at `54a82476939dce8f75af62d73aeb477e11a1260c`; its accepted post-S2D/S5C reconciliation is integrated at `1d91526d11b5291d5388c78940682ca02edeb61e`.** S7A remains an open 21-item billing threat/control/gap register only. No threat is accepted closed and no security, privacy, operations, provider, target or launch assurance is supplied; S7 implementation remains not started and the slice is incomplete. | Preserve the reconciled register and close threats only with separately accepted evidence. Closure still requires S2-S6 plus W9 custody, retention, monitoring, incident and target-runtime controls; W9 itself remains 0/5. Exercise webhook/credential rotation, alerting, ledger-provider and dispute/chargeback/reversal reconciliation, outage/backlog recovery, account erasure/retention and support runbooks with redacted evidence. |
| **W10-S8 — integrated target assurance and activation** | Prove the complete paid-access journey in the launch candidate and assemble the W10 release evidence. | **Not started.** | S1-S7, launch identity and target runtime, provider sandbox/production-capable configuration and independent reviewer. End-to-end positive and failure-path evidence, final privacy/security/finance-tax review, residual-risk disposition and separate Founder authorisation for production activation/release/go-live. |

## Assurance states and stable denominator

Each slice is tracked separately as **planned**, **implemented**, **locally
verified**, **independently reviewed**, **integrated**, **launch-evidence-complete**
and **launch-ready**. “Integrated” means present in the exact launch-candidate
lineage with applicable regressions passing; it does not prove provider or
target-runtime behaviour. “Launch-evidence-complete” requires the slice's
applicable target, security/privacy, operational and commercial evidence.
“Launch-ready” additionally requires all dependent slices and the final
activation/release authority.

The stable delivery denominator is the eight slices above. A slice contributes
one only when all of its stated completion evidence is accepted; partial work
does not round up. At this cut-off **0/8 (0%)** are complete. Existing auth and
payment-boundary foundations are dependencies, not partial W10 slices. Terminal
checks are a separate **0/13** and must not be combined with the delivery
percentage. Change either denominator only if authoritative scope changes or
new evidence proves that a launch-critical outcome is absent; record the reason
rather than growing the map for ordinary fixes.

## Dependencies, parallelism and collision boundaries

1. Preserve the independently reviewed integrated S1, S2A, S2B, S2C, S2D, S2E, S2F,
   S3A, S3B, S3C, S4A, S4B, S4C, S5A, S5B, S5C, S5D, S6E, S6F, S6G and S6H
   boundaries, plus the early-W8 lifecycle-composition evidence. Preserve initial S7A provenance
   and its accepted post-convergence reconciliation. S2A encodes the six Founder-settled
   provider/lifecycle inputs;
   S2B closes only four fail-closed engineering defaults. S2C preserves its
   historical five-key classification. S2F closes Q1 refunds and Q2 paid surface
   as bounded engineering policy under existing Founder authority. `FD-W10-004`
   closes Q3's Founder-policy key, leaving exactly two specialist/engineering
   policy keys unresolved. S2D narrows recovery
   to a local owner-bound no-transfer contract but supplies no authenticated
   adapter, durable mapping or specialist/target acceptance. S3A encodes the bounded
   transition policy without claiming provider verification, persistence or enforcement.
   Hardened S3A encodes exact detached lifecycle history, including the
   non-extendable seven-day `payment_recovery` interval, but grants no provider
   or persistence authority. S3B encodes detached structural record and reconciliation invariants, not a
   durable inbox, authenticated source, persistence layer or entitlement
   decision. S3C composes a future independently authenticated and admitted
   owner-bound fact source into S5D's exact runtime projection, but is itself
   route-less and non-durable: it does not authenticate a provider, establish
   globally latest state, prevent replay/forks across processes, persist, wire
   a route or enforce access. S4A-C encode only disabled provider-edge/intent boundaries and
   cannot create a provider session, verify a callback or emit entitlement.
   Refreshed S5A is inventory evidence only; S5B reconciles
   its 11 internal/admin/legacy/unknown entries and its HICBC downstream
   evidence is lineage-bound; S5C implements five bounded
   legacy/internal route treatments. S2F approves the bounded paid-surface
   policy. S5D implements the route-less provider-neutral guard kernel. S3C is
   its compatible admission seam, but neither package supplies provider
   admission, global durability/latest-state authority, route wiring or live
   enforcement.
   S2E preserves tax/invoice prerequisites but supplies no specialist acceptance.
   Reconciled S7A records all 21 threats as open current-lineage gaps.
   Provider diligence, specialist/engineering evidence and the implementation
   unlocked by the Q3 answer may run in parallel, but S2 closes only through
   explicit accepted evidence.
2. Durable S3 implementation follows the relevant S1/S2 contracts and must
   preserve S3A/S3B/S3C. S4 and S5 can then run in parallel: S4 owns authenticated
   provider translation, while S5 consumes only synthetic or canonical billing
   observations and entitlement decisions. Neither may treat S3B structural
   issuance as provider authenticity or durable admission.
3. Preserve S6A–H's integrated presentation and authenticated preview work and
   the local lifecycle-composition evidence through `584ff7f...`.
   Binding customer actions and the remaining provider-backed lifecycle journeys
   wait for stable S2-S5 contracts. S7 develops alongside S3-S6 and is exercised
   against their integrated result. S8 is the final serial gate.
4. One owner at a time controls `reserved/database.py` migrations and shared
   user/account deletion. Billing code should start in a new `reserved/billing/`
   boundary; provider-specific code must translate at its edge and must not
   write access flags directly.
5. Changes to `reserved/auth.py`, `reserved/web/v2.py`, shared templates/nav,
   `reserved/__init__.py`, CSP/configuration, W9 controls or release metadata
   require an enumerated integration package and the relevant workstream owner.
   No parallel package may edit the same route, migration, entitlement contract
   or price-authority record. Provider product/price IDs and secrets remain
   deployment configuration/custody concerns, never Founder authority.

Upstream contracts are the Founder authority snapshot, authenticated stable user
identity and the W9 custody/data-lifecycle/operations boundaries. External
dependencies are acceptance of Stripe terms and onboarding under the provisional
baseline (or an expressly authorised replacement), current provider documentation,
sandbox access, approved credentials/key custody, target hosting, finance/tax
review of billing VAT/invoices and independent target review. W10 is independent
of Yapily PIS/VRP and the tax calculation engine except for shared identity,
security, UI and release surfaces.

## Effort and critical path

These are planning ranges, not delivery promises. They assume two engineers can
work in parallel, prompt policy decisions, one reviewer, an established billing
provider with usable sandbox tooling, and reuse of the existing auth/W9
foundations. “Critical-path” is the likely serial contribution in working days;
external contracting/onboarding queues can extend elapsed time beyond it.

| Slice | Active effort | Likely elapsed | Critical-path contribution |
|---|---:|---:|---:|
| S1 | 2–3 person-days | 2–4 working days | 2–3 days |
| S2 | 2–5 person-days plus decision time | 3–10 working days | 3–10 days |
| S3 | 5–8 person-days | 1–2 weeks | 5–8 days |
| S4 | 6–10 person-days | 2–4 weeks | 6–10 days |
| S5 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S6 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S7 | 4–7 person-days | 1–2 weeks | 2–5 days after parallelism |
| S8 | 5–8 person-days | 1–3 weeks | 7–12 days |

Total active effort is roughly **32–55 person-days**. A conservative elapsed
range is **7–14 weeks** with the assumed parallelism; the serial critical path
is roughly **29–58 working days** before any longer external queue is known.
Provider terms/final acceptance and onboarding, credentials or sandbox queues are the largest
schedule risks and may extend elapsed time beyond fourteen weeks; they are not
disguised inside the engineering estimate.

## Finite terminal W10 gate

W10 is complete only when all thirteen checks pass:

1. The three current plans and customer-facing prices match the applicable
   Founder authority version, use GBP exact-money representation, and show VAT
   inclusion where applicable without inventing a VAT rate or applicability.
2. Every required renewal, cancellation, failed-payment/grace, entitlement,
   refund, post-settlement dispute/chargeback/reversal, invoice, offer/discount,
   partner-offer, access and override behaviour is explicit and approved by its
   appropriate owner.
3. A billing provider is explicitly selected and its commercial, legal,
   technical, security and data-processing boundary is accepted; historical
   Stripe Connect or Yapily payment material is not treated as that selection.
4. Billing accounts, events, subscriptions, settlement reversals/disputes and
   entitlements are owner-bound, versioned, auditable, idempotent, order-safe
   and reconcilable; provider state is never copied directly into an unaudited
   access flag.
5. Signed provider callbacks, checkout/management returns and reconciliation,
   including post-settlement dispute/chargeback/reversal events, resist forgery,
   replay, duplication, delay, reordering, cross-user access and uncertain
   status, and fail closed without losing recoverability.
6. Every paid launch surface is enforced server-side under the approved access
   policy, including the approved consequences of a post-settlement dispute,
   chargeback or reversal and access through direct URLs and APIs; support/admin
   access and corrections are least-privilege and auditable.
7. Purchase, offer, pending, success, renewal, cancellation, failure, recovery,
   invoice/receipt, refund and post-settlement dispute/chargeback/reversal
   journeys behave and communicate exactly according to approved policy across
   supported browsers and accessibility checks.
8. Special discounts/offers are demonstrated without allowing unapproved price,
   duration, stacking, eligibility or entitlement consequences; partner offers
   remain disabled until their handling is explicit.
9. Billing VAT determination, customer presentation, invoice/receipt content,
   finance reconciliation and refund/dispute/chargeback/reversal accounting pass
   the applicable finance/tax review; VAT-inclusive price authority alone is not
   treated as tax advice.
10. Billing personal data, provider identifiers and credentials follow approved
    minimisation, retention, erasure, encryption/custody, log-redaction and
    account-recovery controls.
11. Monitoring, alerting, webhook backlog recovery, provider-ledger and
    post-settlement dispute/chargeback/reversal reconciliation, outage
    degradation, credential rotation and incident/support runbooks are exercised
    in the intended environment.
12. The exact launch candidate passes local regression, provider sandbox,
    end-to-end identity-to-access, negative/failure, privacy, security and
    operational assurance with traceable redacted evidence and independent
    review.
13. Residual risks are explicitly accepted and the separate Founder gates for
    production access, payment authority, activation, merge/release and go-live
    are recorded. No credential, provider dashboard setting or green local test
    can grant launch status by itself.

## Current next action

W10-S1, S2A, S2B, S2C, S2D, S2E, S2F, S3A, S3B, S3C, S4A, S4B, S4C, S5A, S5B, S5C, S5D,
S6E, S6F, S6G and S6H are independently reviewed and integrated. The early-W8
lifecycle-composition evidence and the initial S7A checkpoint plus its
post-S2D/S5C reconciliation are also integrated; the reconciled register keeps
all 21 threats open and is not security or launch assurance.
S2A records the six Founder-settled provider and paid-lifecycle decisions. S2B
closes the four accepted fail-closed engineering defaults. S2C remains immutable
historical evidence of the then-current five-key classification. Accepted S2F
closes Q1 refunds and Q2 paid surface as bounded engineering policy under existing
Founder authority. `FD-W10-004`, accepted at `ab4f8d4...` and integrated at
`22512f2...`, closes Q3's verified full-withdrawal suspension/restoration policy.
Exactly two policy keys remain unresolved: VAT/invoice treatment and owner-bound
no-transfer billing-account recovery, both specialist/engineering evidence gates
rather than new Founder questions. Post-settlement implementation and specialist
acceptance remain open under the settled rule. S2D supplies the bounded local
owner-bound recovery contract, not its authenticated/durable adapter or external
acceptance. S2E supplies detached non-authoritative structural prerequisites for
later specialist tax/invoice work, not accepted VAT/invoice facts or closure.
S3A remains the provider-neutral transition policy; its hardening at
`48a9704...` supplies an exact detached lifecycle history, including explicit
non-extendable seven-calendar-day `payment_recovery`, but no provider or
persistence authority.
S3B is only the detached record/admission/reconciliation contract and provides
no durable inbox, provider authenticity, persistence or entitlement decision.
S3C, accepted at `b458f2d...` and integrated/corrected through `be417ae...`,
`e145e43...` and `5e6ea88...`, is the owner-bound route-less non-durable
runtime-entitlement admission seam compatible with S5D. It validates and
projects exact content-identified admitted facts, but does not authenticate the
provider or caller, establish globally latest durable state, prevent replay or
forks across processes, persist, wire any route or enforce access live.
S4A-C remain disabled provider-edge and intent contracts with no runtime adapter,
provider session creation, runtime webhook signature admission or activation. The
separately accepted offline signature primitive is recorded below. S5A supplies the exact source-bound route inventory;
its linked-HICBC refresh is accepted at `8480264...`, integrated at `95dd628...`
and reconciled downstream through `d954ddc...` / `05134e5...` without changing
the paid-boundary policy or closing S5.
S2F settles its customer-product candidate class as paid-entitlement-required.
S5B supplies the exact source-bound
reconciliation of its 11 internal/admin/legacy/unknown routes and no new Founder
question, but changes no route and does not start S5.

S5C has now implemented the five accepted legacy/internal hardening treatments
without changing Founder-only scope or enforcing entitlement. S2F separately
settles the paid boundary. S5D is accepted at `88a3c879...`, integrated at
`824b306...`, and lineage-corrected through `64600d9...` / `7a1dbdb...`. It
provides a route-less provider-neutral decision kernel for the exact 25 paid
endpoints, fail-closing invalid authority, owner, sequence, lifecycle and
withdrawal evidence under `FD-W10-003` and `FD-W10-004`. It has no authoritative
provider authentication, global durability/latest-state admission, persistence,
route wiring or live enforcement; S3C provides only its compatible local
admission seam. S5 is therefore partial, not complete. S7A reconciliation is complete
at `1d91526...`; all 21 threats remain open unless separate accepted evidence
closes one.

S6E now presents the accepted recovery semantics without granting entitlement:
ordinary access continues only during the exact seven-calendar-day
`payment_recovery` interval, duplicate failures cannot extend it, verified
recovery restores paid state and unresolved expiry suspends access. Provider
labels and presentation objects have no direct authority. The evidence bindings
for the hardened entitlement convergence are reconciled at `4e1f226...` and the
W9 package-history sentinel is corrected at `109b5ec...`; neither checkpoint
closes an external, specialist, target or launch gate.

S6F presents cancellation and end-of-paid-period state as a detached,
zero-authority view. It cannot request cancellation, mutate provider or billing
state, persist a decision, extend a paid period or grant access. Its acceptance
and integration therefore advance truthful local presentation only; they do not
close S6 or supply provider/target evidence.

S6G presents only detached initial-payment pending/failure copy and cannot begin
paid access. S6H presents only the detached initial-paid/automatic-renewal copy
candidate for exact unauthenticated structural facts and cannot establish an
admitted payment, selected plan, entitlement or access. The accepted early-W8
composition at `584ff7f...` proves their local compatibility with the detached
entitlement, recovery and cancellation contracts through explicitly test-only
projections. It supplies no provider admission, persistence, runtime access,
customer delivery, target or launch assurance and therefore does not close S6,
W8 or any terminal check.

The next S2 work is accepted specialist/engineering evidence for mandatory
refund remedies, VAT/invoice, recovery and post-settlement implementation under
the now-settled Q3 rule, followed by one versioned closure record for all 15 keys. The
pre-Q2 route cleanup is complete at S5C and is not redispatch authority. S5D's
route-less guard kernel is also complete and S3C now supplies its compatible
owner-bound route-less non-durable admission seam. Neither is authority to
pretend provider authentication, global durability/latest-state admission,
cross-process replay/fork prevention, route wiring or live enforcement exists.
The next S5 work is the separately reviewed provider-authenticated durable
admission and route-wiring boundary; it still implements no provider path unless separately authorised. A
durable S3 implementation may proceed only when its datastore, migration
ownership, retention/erasure, key-custody, minimisation, authenticated-source and
independent-review dependencies are accepted; it must implement rather than
merely relabel S3B. Further provider-edge S4 implementation must preserve S4A,
proceed only against current authoritative technical evidence and remain
disabled-first.

No provider adapter, credential, persistence migration, access grant or checkout
package follows merely from the S1 contract. Provider-specific implementation
must remain within the selected provisional Stripe Billing/Checkout/Customer
Portal boundary and still waits for applicable external evidence. Preserve the
accepted non-durable S3A/S3B/S3C and disabled S4B/S4C
contracts. Further durable
entitlement/event-inbox implementation requires the approved W9
custody/data-lifecycle boundary as well as the explicit lifecycle decisions.

## Explicitly out of scope

This map does not authorise set-aside PIS/VRP or other customer money movement,
marketplace/reseller/affiliate commerce, merchant acquiring for third parties,
multi-currency or non-UK expansion, tax-return/VAT-return functionality, a free
tier or trial, account sharing/team seats, bespoke enterprise billing, dunning
optimisation, or post-launch pricing experiments. It does not select a provider,
amend Founder Decisions, modify the Control Plane, access production or sandbox
accounts, handle credentials, charge money, merge, deploy or go live. A required
launch policy may describe a deliberately unsupported case; unsupported
sophistication does not create another slice unless authoritative scope changes.

**Map disposition:** **S1 independently reviewed and integrated; S2 partially
implemented with independently reviewed/integrated S2A, S2B, evidence-only S2C,
contract-only S2D, detached non-authoritative S2E and bounded engineering-policy
S2F; Q1 refunds and Q2 paid surface are closed under existing Founder authority;
`FD-W10-004` closes Q3's verified full-withdrawal suspension/restoration policy;
exactly two policy keys remain unresolved, with VAT/invoice plus no-transfer
recovery still awaiting specialist/engineering evidence and post-settlement
implementation/specialist acceptance still open under the settled rule;
S3 partially implemented with independently reviewed/integrated hardened S3A
lifecycle, detached contract-only S3B and owner-bound route-less non-durable
S3C admission seam compatible with S5D, but no durable inbox,
provider-authenticated source, globally latest durable state, cross-process
replay/fork prevention, persistence, route wiring or enforcement boundary; S4 partially
implemented with independently reviewed/integrated disabled S4A, Checkout-intent
S4B and Portal-intent S4C but no runtime adapter, provider session, runtime
webhook admission, persistence or activation; S5 partially implemented,
with independently reviewed/integrated S5A inventory, S5B 11-route reconciliation,
S5C five-treatment hardening, HICBC-refreshed route evidence and S5D route-less
paid-access guard kernel; S3C is its compatible local admission seam, but these
packages have no provider authentication, global durability/latest-state
authority, persistence, route wiring or live enforcement;
S6 partially implemented/integrated through S6E's zero-authority
`payment_recovery` presentation, S6F's zero-authority cancellation/end-of-paid-period
presentation, S6G's zero-authority initial-payment pending/failure presentation,
S6H's zero-authority initial-paid presentation and early-W8 local lifecycle
composition; initial and post-convergence S7A are
integrated open-gap evidence with all 21 threats still open and supply no assurance; strict
completion remains 0/8 and the terminal gate remains 0/13 pending S2 policy
closure and every slice's remaining completion evidence.** W9 remains 0/5.
Provider, target,
specialist-review, residual-risk, Founder activation/release and launch authority
gates remain open.

## Subsequent accepted offline signature and HICBC presentation evidence

This bounded update uses clean integration
`bed02d9ee30e1b18ecf6ceb50b03040aa549c736`, tree
`028119b7b769f6689a75f1369b5a04686c5dd93c`; earlier route counts and source
snapshots above remain historical, not mutable current-HEAD requirements.

Offline Stripe verifier source `9e4e01a64fa393225db873ad8194a11b8cf81e78`
was independently accepted and integrated at
`7df8af92915ad28d9fee62c3d68c588ceb21d57b`. It verifies unchanged bytes with
supplied bounded keys, HMAC-SHA256, constant-time comparison and a fixed bounded
timestamp policy. Success is only a supplied-key signature/freshness match.
There is no key discovery/custody, webhook consumer, JSON/event admission,
provider/account ownership, durable replay prevention, entitlement, provider
session, SDK integration or activation. The three-path package had 71 focused
tests and 336 passing affected tests on its clean checkpoint, plus independent
OpenSSL/negative probes. It advances a local S4 prerequisite, not S4 completion.

The accepted HICBC annual runtime `bb06354...` and frontend source
`315248807667868ff52dffce2ab0dab599e651dc`, integrated at `bed02d9...`, refresh
live S5A/S5B bindings. At that historical cut-off S5A had 53 routes with HICBC enabled and 26 paid
endpoints; this is classification only, not runtime entitlement enforcement.
The manual preview remains disabled-first, non-production and non-persistent;
its source-adapter claimant-`none` defect was separately open. Billing repository
correction was also pending independent acceptance at that cut-off and was not promoted there
to durable application billing. No accepted-but-unreviewed result is inferred.

At this inspected lineage the full canonical internal gate passes 7,934 root
tests and all mandatory subgates, while October remains `not_ready` with 18
blockers. Strict completion remains 0/8, terminal 0/13 and W9 0/5. Preserve all
specialist, custody, retention, physical persistence, authenticated membership,
provider, human, target and Founder activation/release gates. No new slice,
policy, authority or launch claim is introduced by this evidence refresh.

## Accepted local repository and route-history reconciliation — 5 September 2026

This update is based on clean integration
`26831400fcb0ee638761b589b3bbbf0e239427dd`, tree
`2f717f551e91ae95819a5f981902bacdfac12ad9`. The older machine-readable
register is preserved byte-for-byte as historical evidence; its earlier review
does not cover this new prose. No denominator, terminal check or threat is closed.

### W10-S3D: accepted disposable-local persistence, not production custody

The three-path repository source is
`d2b42073ba9099a13912e9e8f0ccfc731f119528`, tree
`061f87c67f1b6f280ff51109bbf26e4b57088868`, sole parent
`064eac2d339038b942897c6e58e24cf496c1d7ae`. Integration `26831400...`
preserves this source as its second parent, alongside first parent
`7faa4dcf7b04c7ad59718b3724b17d9f1297b393`, with exactly the accepted blobs:

| Path | SHA-256 |
|---|---|
| `reserved/billing/local_billing_repository.py` | `469825766f1ae5058128dfa270bc9ab06327f786bd1e8ba05b923d3d6accef5e` |
| `tests/test_w10_local_billing_repository.py` | `8d0179223b34333697cece3f7b28e86fd0c9cd6ff1458be2d698d6e19f912c62` |
| `docs/W10_S3D_LOCAL_BILLING_REPOSITORY.md` | `c9c303511065d611c556e5aaf3bd39cf7eb8e83ee66517100bca3c9040c6a2ee` |

The implementation is an opt-in, caller-path, file-backed SQLite primitive for
disposable synthetic use. It supplies persistent structural journal/head and
reconciliation records, transactional append/head advancement, duplicate and
predecessor/order checks, rollback, strict schema validation and bounded
consistent reads across cooperating connections. This is real local durability,
not another purely in-memory contract. Supplied owner/account/subscription
identifiers and content hashes remain structural facts, not authenticated
membership, provider authenticity or resistance to a hostile datastore owner.

The owning record `work/w10-s3d-local-repository-checkpoint.md` in the parent
workspace supersedes the candidate-pending status in the historical package
evidence. It records independent review, 80 focused passes, schema and WAL-read
probes, and 373 clean source affected passes including the unchanged historical
dirty-scope sentinel. Those are bounded engineering results, not production
custody or application deployment assurance.

S3 remains partial. Authenticated owner/billing membership and source admission,
production datastore/custody/encryption, retention/erasure/backup handling,
application migrations, authoritative ingress, globally authoritative runtime
state and paid-route enforcement remain outstanding. This local schema does
not select the application datastore, grant entitlement or activate a provider.
The existing S3A/S3B/S3C and S5D boundaries are not relabelled as durable or
provider-authenticated by association.

### Accepted route/source changes after the historical cut-off

The HICBC claimant-none adapter correction is accepted at
`269c5427eac573cd73b4f9e5054675c8a40533db`, integrated at
`f3729c21b681cf4e6b2d70ba63421f2d3a3dee7d`. It maps affirmative no entitlement
to the existing None/zero engine input without repairing stored claimant facts;
unknown and contradictory facts remain insufficient. It closes that narrow
adapter defect, not HICBC privacy, persistence, annual-journey or launch gates.
Source evidence is `docs/HICBC_NO_CLAIMANT_ADAPTER_EVIDENCE.md` and the owning
`work/hicbc-no-claimant-checkpoint.md` record.

Accepted manual PAYE entry/review source
`f29a5a8d4acde639fb108f8f9eeaaa833b59dc4b` and manual MTD source
`730db03e9d952a43df2f6d7b638b5a893600ec89` extend the inventory to **46
always-registered / 55 HICBC-enabled routes and 28 paid classifications**.
Both remain independently disabled, non-production, unsaved manual pathways;
classification is not runtime entitlement enforcement. The current counts are
in `docs/W10_S5A_PAID_SURFACE_INVENTORY.md` and the accepted S5B/S5D consumers.
Earlier 25/26-paid and 53-route figures above remain historical, not current.

MTD source-binding reconciliation
`573a204a687dc41c1608d4d5f631d167fc01bc91`, integrated with the manual journey at
`7faa4dcf7b04c7ad59718b3724b17d9f1297b393`, binds S7A live SRC-16 to the accepted
MTD `v2.py` digest
`15b0893514d4e6a5daab935d602aa1d2aa899617f401ed7dbabc704ab91ef563`.
PAYE, S5C, preview and SRC-24 historical/independent source anchors remain
distinct. No general current-HEAD equality requirement is introduced.

### Integrated evidence and remaining disposition

The owning task collected canonical session 72446 at clean `26831400...`:
exit zero; **8,319 root tests passed, zero failures/errors/skips**, 13 artifact,
23 parity and 138 options tests passed, with mandatory RW3 true. This records
that exact integrated run, not a rerun by this map author and not review of
the subsequently edited map. October remains **not_ready, 18 blockers**.
S3 and W10 remain incomplete; strict completion is **0/8**, terminal **0/13**
and W9 **0/5**. Provider, authenticated custody/membership, specialist,
privacy/security, human/target and Founder activation/release gates remain open.
