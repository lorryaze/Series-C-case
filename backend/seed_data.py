"""Populate the database with realistic fintech demo data.

Idempotent: re-running replaces the demo dataset rather than duplicating it.

    python seed_data.py            # seed (creates tables if missing)
    python seed_data.py --reset    # wipe existing rows first
"""

from __future__ import annotations

import argparse
import random
from collections.abc import Sequence
from datetime import UTC, datetime, timedelta
from decimal import Decimal

from sqlalchemy import delete
from sqlalchemy.orm import Session

from app.config import get_settings
from app.database import SessionFactory, engine
from app.models import (
    AuditLog,
    Base,
    FeatureFlag,
    FeatureFlagState,
    KycDocument,
    KycNote,
    KycReview,
    Refund,
    User,
)
from app.models.enums import (
    AuditAction,
    AuditEntity,
    DocumentType,
    FlagEnvironment,
    KycStatus,
    RefundReason,
    RefundStatus,
    Role,
    risk_level_for_score,
)
from app.utils.security import hash_password

RANDOM_SEED = 20260818

FIRST_NAMES = [
    "Amara",
    "Ben",
    "Camila",
    "Devon",
    "Elena",
    "Farhan",
    "Grace",
    "Hiro",
    "Ines",
    "Jonas",
    "Keiko",
    "Liam",
    "Mariana",
    "Noah",
    "Olga",
    "Priya",
    "Quinn",
    "Rafael",
    "Sofia",
    "Tomas",
    "Uma",
    "Viktor",
    "Wren",
    "Xiomara",
    "Yusuf",
    "Zara",
    "Adaeze",
    "Bruno",
    "Chloe",
    "Dmitri",
]
LAST_NAMES = [
    "Adeyemi",
    "Bianchi",
    "Chen",
    "Duarte",
    "Eriksen",
    "Fontaine",
    "Gupta",
    "Haddad",
    "Ibrahim",
    "Jensen",
    "Kowalski",
    "Lindqvist",
    "Moreau",
    "Nakamura",
    "Okafor",
    "Petrov",
    "Quintero",
    "Rossi",
    "Santos",
    "Tanaka",
    "Ueda",
    "Vargas",
    "Watanabe",
    "Xu",
    "Yilmaz",
    "Zhang",
]
BUSINESS_SUFFIXES = ["Labs", "Capital", "Logistics", "Studio", "Holdings", "Collective"]
COUNTRIES = ["US", "GB", "DE", "BR", "NG", "SG", "CA", "AE", "IN", "MX"]

RISK_SUMMARIES = {
    "low": "Device, email and address checks consistent; no adverse media.",
    "medium": "Address mismatch against credit bureau; document quality acceptable.",
    "high": "Recently created email domain and IP geolocation mismatch with stated country.",
    "critical": "Sanctions screening hit requires manual adjudication before onboarding.",
}

FLAG_DEFINITIONS: list[tuple[str, str, bool]] = [
    (
        "Enable instant transfers",
        "Routes eligible payouts through the instant rails provider.",
        True,
    ),
    ("New onboarding flow", "Three-step KYC onboarding with document autocapture.", True),
    ("Dark mode", "Dark theme across the customer dashboard.", True),
    ("Beta risk engine", "Scores onboarding with the v2 risk model shadow-mode first.", False),
    ("Card controls", "Lets customers freeze cards and set merchant limits.", True),
    ("Refund self service", "Customers can request refunds without contacting support.", False),
    ("Ach same day", "Same-day ACH settlement for verified business accounts.", False),
    ("Fraud velocity checks", "Adds velocity rules to the transaction fraud pipeline.", True),
    ("Multi currency wallets", "Holds balances in USD, EUR and GBP.", False),
    ("Statement redesign", "New PDF statement layout with spend categories.", False),
    ("Merchant insights", "Cohort and retention analytics for merchant accounts.", False),
    ("Kyc auto approval", "Auto-approves low-risk cases scoring under 15.", False),
    ("Webhook retries v2", "Exponential backoff with dead-letter queue for webhooks.", True),
    ("Sms otp fallback", "Falls back to SMS OTP when push approval times out.", True),
    ("Treasury sweeps", "Nightly sweeps of idle balances into the treasury account.", False),
    ("Partner api sandbox", "Public sandbox with seeded partner API fixtures.", False),
]

DEMO_USERS: list[tuple[str, str, Role]] = [
    ("admin@fintech.com", "Alex Rivera", Role.ADMIN),
    ("reviewer@fintech.com", "Riley Chen", Role.REVIEWER),
    ("viewer@fintech.com", "Vic Okonkwo", Role.VIEWER),
    ("compliance.lead@fintech.com", "Dana Whitfield", Role.REVIEWER),
]


def utc(days_ago: float = 0.0) -> datetime:
    """Timestamp ``days_ago`` days before now, in UTC."""
    return datetime.now(UTC) - timedelta(days=days_ago)


def wipe(session: Session) -> None:
    """Delete every demo row so seeding starts from a clean slate."""
    for model in (
        AuditLog,
        KycNote,
        KycDocument,
        KycReview,
        Refund,
        FeatureFlagState,
        FeatureFlag,
        User,
    ):
        session.execute(delete(model))
    session.commit()


def seed_users(session: Session) -> list[User]:
    """Create the demo staff users."""
    password = get_settings().demo_user_password
    users = [
        User(
            email=email,
            full_name=full_name,
            hashed_password=hash_password(password),
            role=role,
        )
        for email, full_name, role in DEMO_USERS
    ]
    session.add_all(users)
    session.flush()
    return users


def seed_kyc_reviews(
    session: Session, *, users: Sequence[User], rng: random.Random, count: int = 60
) -> list[KycReview]:
    """Create KYC cases spread across statuses, risk bands and reviewers."""
    reviewers = [user for user in users if user.role in (Role.ADMIN, Role.REVIEWER)]
    admin = next(user for user in users if user.role == Role.ADMIN)
    status_weights = [
        (KycStatus.PENDING, 0.34),
        (KycStatus.IN_REVIEW, 0.22),
        (KycStatus.APPROVED, 0.24),
        (KycStatus.REJECTED, 0.1),
        (KycStatus.ESCALATED, 0.1),
    ]
    statuses = [status for status, _ in status_weights]
    weights = [weight for _, weight in status_weights]

    reviews: list[KycReview] = []
    for index in range(count):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        name = f"{first} {last}"
        status = rng.choices(statuses, weights=weights, k=1)[0]
        risk_score = rng.choice(
            [rng.randint(3, 24), rng.randint(25, 49), rng.randint(50, 74), rng.randint(75, 98)]
        )
        risk_level = risk_level_for_score(risk_score)
        submitted_at = utc(rng.uniform(0.2, 45))
        is_business = rng.random() < 0.3

        review = KycReview(
            case_reference=f"KYC-2026-{1000 + index}",
            customer_name=name,
            customer_email=f"{first.lower()}.{last.lower()}@example.com",
            customer_country=rng.choice(COUNTRIES),
            business_name=(f"{last} {rng.choice(BUSINESS_SUFFIXES)}" if is_business else None),
            submitted_at=submitted_at,
            status=status,
            risk_score=risk_score,
            risk_level=risk_level,
            risk_summary=RISK_SUMMARIES[risk_level.value],
            sanctions_hit=risk_score > 80 and rng.random() < 0.5,
            pep_match=risk_score > 60 and rng.random() < 0.25,
            primary_document_type=(
                DocumentType.BUSINESS_REGISTRATION
                if is_business
                else rng.choice(
                    [
                        DocumentType.PASSPORT,
                        DocumentType.DRIVERS_LICENSE,
                        DocumentType.NATIONAL_ID,
                    ]
                )
            ),
        )
        if status != KycStatus.PENDING:
            review.assigned_reviewer = rng.choice(reviewers)
        if status in (KycStatus.APPROVED, KycStatus.REJECTED):
            review.decided_at = submitted_at + timedelta(hours=rng.uniform(2, 72))
            review.decision_reason = (
                "Identity and address verified against two independent sources."
                if status == KycStatus.APPROVED
                else "Submitted document expired and address could not be verified."
            )

        review.documents = [
            KycDocument(
                document_type=review.primary_document_type,
                file_name=f"{first.lower()}_{last.lower()}_id.pdf",
                verified=status == KycStatus.APPROVED,
                uploaded_at=submitted_at,
            ),
            KycDocument(
                document_type=DocumentType.PROOF_OF_ADDRESS,
                file_name=f"{first.lower()}_{last.lower()}_utility_bill.pdf",
                verified=status == KycStatus.APPROVED,
                uploaded_at=submitted_at,
            ),
        ]
        reviews.append(review)

    session.add_all(reviews)
    session.flush()

    for review in reviews:
        session.add(
            AuditLog(
                entity_type=AuditEntity.KYC_REVIEW,
                entity_id=review.id,
                action=AuditAction.CREATED,
                new_value=review.case_reference,
                actor_id=admin.id,
                actor_email=admin.email,
                created_at=review.submitted_at,
            )
        )
        reviewer = review.assigned_reviewer
        if reviewer is not None:
            session.add(
                AuditLog(
                    entity_type=AuditEntity.KYC_REVIEW,
                    entity_id=review.id,
                    action=AuditAction.ASSIGNED,
                    field="assigned_reviewer",
                    new_value=reviewer.email,
                    actor_id=admin.id,
                    actor_email=admin.email,
                    created_at=review.submitted_at + timedelta(hours=1),
                )
            )
            if rng.random() < 0.5:
                session.add(
                    KycNote(
                        review_id=review.id,
                        author_id=reviewer.id,
                        body=rng.choice(
                            [
                                "Requested a clearer scan of the proof of address.",
                                "Bureau match confirmed; proceeding with standard checks.",
                                "Escalating: sanctions screening needs a second reviewer.",
                                "Customer confirmed source of funds over the phone.",
                            ]
                        ),
                        created_at=review.submitted_at + timedelta(hours=2),
                    )
                )
        if review.decided_at is not None:
            session.add(
                AuditLog(
                    entity_type=AuditEntity.KYC_REVIEW,
                    entity_id=review.id,
                    action=AuditAction.STATUS_CHANGED,
                    field="status",
                    previous_value=KycStatus.IN_REVIEW.value,
                    new_value=review.status.value,
                    reason=review.decision_reason,
                    actor_id=(review.assigned_reviewer or admin).id,
                    actor_email=(review.assigned_reviewer or admin).email,
                    created_at=review.decided_at,
                )
            )
    session.flush()
    return reviews


def seed_refunds(
    session: Session, *, users: Sequence[User], rng: random.Random, count: int = 120
) -> list[Refund]:
    """Create refund requests across statuses, reasons and amounts."""
    processors = [user for user in users if user.role in (Role.ADMIN, Role.REVIEWER)]
    status_weights = [
        (RefundStatus.PENDING, 0.3),
        (RefundStatus.APPROVED, 0.45),
        (RefundStatus.REJECTED, 0.15),
        (RefundStatus.INFO_REQUESTED, 0.1),
    ]
    statuses = [status for status, _ in status_weights]
    weights = [weight for _, weight in status_weights]
    reason_details = {
        RefundReason.DUPLICATE_CHARGE: "Customer was charged twice for the same order.",
        RefundReason.SERVICE_NOT_RENDERED: "Subscription renewed after cancellation request.",
        RefundReason.FRAUD: "Card reported stolen; transaction disputed by issuer.",
        RefundReason.CUSTOMER_REQUEST: "Customer requested a goodwill refund.",
        RefundReason.PROCESSING_ERROR: "Incorrect amount captured during settlement.",
    }

    refunds: list[Refund] = []
    for index in range(count):
        first, last = rng.choice(FIRST_NAMES), rng.choice(LAST_NAMES)
        status = rng.choices(statuses, weights=weights, k=1)[0]
        reason = rng.choice(list(RefundReason))
        requested_at = utc(rng.uniform(0.1, 29.9))
        amount = Decimal(str(round(rng.uniform(5, 5000), 2)))

        refund = Refund(
            refund_reference=f"RF-2026-{2000 + index}",
            customer_name=f"{first} {last}",
            customer_email=f"{first.lower()}.{last.lower()}@example.com",
            transaction_reference=f"TXN-{rng.randint(100000, 999999)}",
            amount=amount,
            currency="USD",
            reason=reason,
            reason_detail=reason_details[reason],
            status=status,
            requested_at=requested_at,
        )
        if status in (RefundStatus.APPROVED, RefundStatus.REJECTED):
            processor = rng.choice(processors)
            refund.processed_at = requested_at + timedelta(hours=rng.uniform(1, 96))
            refund.processed_by = processor
            refund.decision_reason = (
                "Duplicate confirmed in the ledger; refunded to the original method."
                if status == RefundStatus.APPROVED
                else "Charge matches a delivered service; no refund due."
            )
        elif status == RefundStatus.INFO_REQUESTED:
            refund.decision_reason = "Awaiting the customer's bank statement excerpt."
        refunds.append(refund)

    session.add_all(refunds)
    session.flush()

    for refund in refunds:
        actor = refund.processed_by or processors[0]
        session.add(
            AuditLog(
                entity_type=AuditEntity.REFUND,
                entity_id=refund.id,
                action=AuditAction.CREATED,
                new_value=refund.refund_reference,
                actor_id=actor.id,
                actor_email=actor.email,
                created_at=refund.requested_at,
            )
        )
        if refund.processed_at is not None:
            session.add(
                AuditLog(
                    entity_type=AuditEntity.REFUND,
                    entity_id=refund.id,
                    action=AuditAction.STATUS_CHANGED,
                    field="status",
                    previous_value=RefundStatus.PENDING.value,
                    new_value=refund.status.value,
                    reason=refund.decision_reason,
                    actor_id=actor.id,
                    actor_email=actor.email,
                    created_at=refund.processed_at,
                )
            )
    session.flush()
    return refunds


def seed_feature_flags(
    session: Session, *, users: Sequence[User], rng: random.Random
) -> list[FeatureFlag]:
    """Create feature flags with per-environment rollout state."""
    admin = next(user for user in users if user.role == Role.ADMIN)
    flags: list[FeatureFlag] = []
    for name, description, production_enabled in FLAG_DEFINITIONS:
        flag = FeatureFlag(
            key=name.lower().replace(" ", "_"),
            name=name,
            description=description,
            default_enabled=production_enabled,
            modified_by=admin,
        )
        flag.environments = [
            FeatureFlagState(
                environment=FlagEnvironment.PRODUCTION,
                enabled=production_enabled,
                rollout_percentage=rng.choice([10, 25, 50, 100]) if production_enabled else 0,
            ),
            FeatureFlagState(
                environment=FlagEnvironment.STAGING,
                enabled=True,
                rollout_percentage=100,
            ),
            FeatureFlagState(
                environment=FlagEnvironment.DEVELOPMENT,
                enabled=True,
                rollout_percentage=100,
            ),
        ]
        flags.append(flag)

    session.add_all(flags)
    session.flush()

    for flag in flags:
        session.add(
            AuditLog(
                entity_type=AuditEntity.FEATURE_FLAG,
                entity_id=flag.id,
                action=AuditAction.CREATED,
                new_value=flag.key,
                actor_id=admin.id,
                actor_email=admin.email,
                created_at=utc(rng.uniform(10, 60)),
            )
        )
        if flag.default_enabled:
            session.add(
                AuditLog(
                    entity_type=AuditEntity.FEATURE_FLAG,
                    entity_id=flag.id,
                    action=AuditAction.TOGGLED,
                    field="production.enabled",
                    previous_value="False",
                    new_value="True",
                    actor_id=admin.id,
                    actor_email=admin.email,
                    created_at=utc(rng.uniform(1, 9)),
                )
            )
    session.flush()
    return flags


def seed(*, reset: bool = True, skip_if_seeded: bool = False) -> None:
    """Seed the database, optionally wiping existing rows first."""
    Base.metadata.create_all(bind=engine)
    rng = random.Random(RANDOM_SEED)
    with SessionFactory() as session:
        if skip_if_seeded and session.query(User).count() > 0:
            print("Database already seeded; leaving it untouched.")
            return
        if reset:
            wipe(session)
        users = seed_users(session)
        reviews = seed_kyc_reviews(session, users=users, rng=rng)
        refunds = seed_refunds(session, users=users, rng=rng)
        flags = seed_feature_flags(session, users=users, rng=rng)
        session.commit()

    print(
        f"Seeded {len(users)} users, {len(reviews)} KYC reviews, "
        f"{len(refunds)} refunds and {len(flags)} feature flags."
    )
    print(
        "Demo credentials: admin@fintech.com / reviewer@fintech.com / viewer@fintech.com "
        f"(password: {get_settings().demo_user_password})"
    )


def main() -> None:
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="Seed realistic demo data.")
    parser.add_argument(
        "--keep-existing",
        action="store_true",
        help="Append instead of wiping the existing demo rows.",
    )
    parser.add_argument(
        "--skip-if-seeded",
        action="store_true",
        help="Do nothing when users already exist; used on container start-up.",
    )
    args = parser.parse_args()
    seed(reset=not args.keep_existing, skip_if_seeded=args.skip_if_seeded)


if __name__ == "__main__":
    main()
