"""Legal page content (Privacy Policy & Terms).

Separated from `app/main.py` so legal text is easy to review and update.

The rendering layer is responsible for HTML escaping/sanitization.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional


@dataclass(frozen=True)
class LegalSection:
    heading: str
    body: Optional[str] = None
    bullets: Optional[List[str]] = None


PRIVACY_POLICY_SECTIONS: List[LegalSection] = [
    LegalSection(
        heading="Overview",
        body=(
            "Foo Ball Service is a football match prediction and data aggregation service. "
            "This Privacy Policy explains what we collect, how we use it, and the choices you have."
        ),
    ),
    LegalSection(
        heading="Information we collect",
        bullets=[
            "Request metadata: approximate timestamp, endpoint, HTTP method, response status, and basic user-agent information.",
            "Security metadata (when enabled): authentication/authorization outcomes (for example, whether an admin key was provided/validated).",
            "Operational logs: error traces and performance timings used to keep the service reliable.",
            "Stored football data: competition, fixture, and head-to-head datasets retrieved from third-party providers and cached in our database.",
            "We do not intentionally collect special-category personal data (e.g., health, biometrics) or payment information.",
        ],
    ),
    LegalSection(
        heading="How we use information",
        bullets=[
            "Provide core functionality (predictions, rankings, fixtures, and supporting metrics).",
            "Maintain, monitor, and improve service reliability and security (e.g., debugging, rate-limit protection, fraud/abuse prevention).",
            "Comply with legal obligations and enforce our Terms.",
        ],
    ),
    LegalSection(
        heading="Cookies and tracking",
        bullets=[
            "The service does not set advertising cookies by default.",
            "If you deploy Foo Ball Service behind a proxy/load balancer or add analytics, those components may introduce cookies or tracking—review your deployment configuration.",
        ],
    ),
    LegalSection(
        heading="Sharing and disclosure",
        bullets=[
            "We do not sell your personal information.",
            "We may share limited data with infrastructure providers (hosting, monitoring, database) strictly to operate the service.",
            "We may disclose information if required by law, regulation, or legal process.",
            "Football data may originate from third-party providers. Their terms and privacy practices apply to their services.",
        ],
    ),
    LegalSection(
        heading="Data retention",
        bullets=[
            "Service logs are retained for troubleshooting and security auditing for a limited period based on operational needs.",
            "Cached sports datasets (competitions/matches/H2H) may be retained to reduce repeated third-party API calls.",
            "Prediction outputs may be retained for a limited time and may be periodically cleaned as part of maintenance jobs.",
        ],
    ),
    LegalSection(
        heading="Security",
        bullets=[
            "We use reasonable security measures such as authentication for restricted endpoints, logging, and monitoring.",
            "No method of transmission or storage is 100% secure; we cannot guarantee absolute security.",
        ],
    ),
    LegalSection(
        heading="Your choices",
        bullets=[
            "If you operate your own deployment, you can configure log levels, retention, and access controls.",
            "If you are an end user of a hosted deployment, contact the service owner to request access, correction, or deletion where applicable.",
        ],
    ),
    LegalSection(
        heading="International users",
        body=(
            "If you access the service from outside the country where it is hosted, "
            "your information may be processed in that hosting region."
        ),
    ),
    LegalSection(
        heading="Changes to this policy",
        body=(
            "We may update this Privacy Policy from time to time. "
            "The ‘Last updated’ date reflects the latest revision."
        ),
    ),
]


TERMS_AND_CONDITIONS_SECTIONS: List[LegalSection] = [
    LegalSection(
        heading="Agreement to terms",
        body=(
            "By accessing or using Foo Ball Service, you agree to these Terms and Conditions. "
            "If you do not agree, do not use the service."
        ),
    ),
    LegalSection(
        heading="Service description",
        bullets=[
            "The service provides football data retrieval, caching, and match prediction outputs.",
            "Predictions are informational only and may be inaccurate.",
            "The service may change, suspend, or be discontinued at any time.",
        ],
    ),
    LegalSection(
        heading="No betting or financial advice",
        bullets=[
            "Predictions are not guarantees and do not constitute betting, investment, or financial advice.",
            "You are solely responsible for decisions you make based on the service.",
        ],
    ),
    LegalSection(
        heading="Acceptable use",
        bullets=[
            "Do not misuse the service (e.g., attempt unauthorized access, abuse rate limits, or interfere with normal operation).",
            "Do not use the service to violate applicable laws or third-party rights.",
            "Automated scraping is allowed only if it respects rate limits and does not degrade service availability.",
        ],
    ),
    LegalSection(
        heading="Accounts, authentication, and admin endpoints",
        bullets=[
            "Some endpoints may require an admin key or other credentials.",
            "You are responsible for maintaining the confidentiality of credentials and for all activity under them.",
            "We may revoke or rotate credentials if misuse is detected.",
        ],
    ),
    LegalSection(
        heading="Third-party services and data",
        bullets=[
            "The service may rely on third-party football data providers and infrastructure components.",
            "Third-party terms may apply; availability and correctness of third-party data is not guaranteed.",
        ],
    ),
    LegalSection(
        heading="Intellectual property",
        bullets=[
            "The software, APIs, and documentation may be protected by intellectual property laws.",
            "Team names, logos, and competition marks belong to their respective owners and are used for identification purposes.",
        ],
    ),
    LegalSection(
        heading="Disclaimers",
        bullets=[
            "The service is provided ‘as is’ and ‘as available’ without warranties of any kind.",
            "We do not warrant uninterrupted, secure, or error-free operation.",
        ],
    ),
    LegalSection(
        heading="Limitation of liability",
        body=(
            "To the maximum extent permitted by law, we are not liable for indirect, incidental, special, "
            "consequential, or exemplary damages arising from your use of the service."
        ),
    ),
    LegalSection(
        heading="Termination",
        body=(
            "We may suspend or terminate access to the service at any time if we reasonably believe you violated "
            "these Terms or if necessary to protect the service."
        ),
    ),
    LegalSection(
        heading="Governing law",
        body=(
            "These Terms are governed by the laws applicable in the jurisdiction where the service operator is established, "
            "unless otherwise required by law."
        ),
    ),
    LegalSection(
        heading="Contact",
        body="For questions about these Terms, contact the service owner/administrator.",
    ),
]
