"""Idempotently seed a development organization and explicitly supplied role users."""

from __future__ import annotations

import argparse
import asyncio
from dataclasses import dataclass

from app.auth.identifiers import canonicalize_domain
from app.auth.models import (
    CandidateProfile,
    EntityStatus,
    Organization,
    OrganizationDomainMapping,
    Role,
    User,
)
from app.core.config import Settings
from app.core.database import Database
from pydantic_settings import SettingsConfigDict
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession


@dataclass(frozen=True)
class SeedUser:
    role: Role
    email: str
    display_name: str


@dataclass(frozen=True)
class SeedDomainMapping:
    domain: str
    organization_slug: str


class SeedSettings(Settings):
    """Load API values from a shared local env file while ignoring frontend-only keys."""

    model_config = SettingsConfigDict(
        case_sensitive=False,
        env_file=None,
        extra="ignore",
        frozen=True,
    )


def parse_seed_user(value: str) -> SeedUser:
    role_value, separator, remainder = value.partition(":")
    email, second_separator, display_name = remainder.partition(":")
    if not separator or not second_separator or not email.strip() or not display_name.strip():
        raise argparse.ArgumentTypeError("User must use ROLE:email:display-name")
    try:
        role = Role(role_value.upper())
    except ValueError as error:
        raise argparse.ArgumentTypeError("Role must be CANDIDATE, MANAGER, or ADMIN") from error
    return SeedUser(role=role, email=email.strip(), display_name=display_name.strip())


def parse_domain_mapping(value: str) -> SeedDomainMapping:
    domain, separator, organization_slug = value.partition(":")
    if not separator or not organization_slug.strip():
        raise argparse.ArgumentTypeError("Domain mapping must use domain:organization-slug")
    try:
        normalized_domain = canonicalize_domain(domain)
    except ValueError as error:
        raise argparse.ArgumentTypeError("Domain mapping contains an invalid domain") from error
    return SeedDomainMapping(normalized_domain, organization_slug.strip())


async def seed(
    session: AsyncSession,
    *,
    organization_name: str,
    organization_slug: str,
    users: tuple[SeedUser, ...],
    domain_mappings: tuple[SeedDomainMapping, ...] = (),
) -> None:
    organization = await session.scalar(
        select(Organization).where(Organization.slug == organization_slug)
    )
    if organization is None:
        organization = Organization(
            name=organization_name,
            slug=organization_slug,
            status=EntityStatus.ACTIVE.value,
        )
        session.add(organization)
        await session.flush()

    for item in users:
        normalized_email = item.email.casefold()
        existing = await session.scalar(
            select(User).where(
                User.org_id == organization.id,
                User.normalized_email == normalized_email,
            )
        )
        if existing is not None:
            if existing.role != item.role.value:
                raise ValueError("Existing seed user has a different role")
            continue
        user = User(
            org_id=organization.id,
            email=item.email,
            normalized_email=normalized_email,
            display_name=item.display_name,
            role=item.role.value,
            status=EntityStatus.ACTIVE.value,
            auth_generation=1,
        )
        session.add(user)
        await session.flush()
        if item.role is Role.CANDIDATE:
            session.add(CandidateProfile(org_id=organization.id, user_id=user.id))

    for item in domain_mappings:
        target = await session.scalar(
            select(Organization).where(Organization.slug == item.organization_slug)
        )
        if target is None:
            raise ValueError("Domain mapping organization slug does not exist")
        existing = await session.scalar(
            select(OrganizationDomainMapping).where(
                OrganizationDomainMapping.normalized_domain == item.domain,
                OrganizationDomainMapping.removed_at.is_(None),
            )
        )
        if existing is not None:
            if existing.org_id != target.id:
                raise ValueError("Existing domain mapping targets a different organization")
            continue
        session.add(
            OrganizationDomainMapping(
                org_id=target.id,
                normalized_domain=item.domain,
                removed_at=None,
            )
        )


def parser() -> argparse.ArgumentParser:
    argument_parser = argparse.ArgumentParser(description=__doc__)
    argument_parser.add_argument("--env-file", default=".env.local")
    argument_parser.add_argument("--organization-name", default="MockInterview Development")
    argument_parser.add_argument("--organization-slug", default="mockinterview-development")
    argument_parser.add_argument(
        "--user",
        action="append",
        type=parse_seed_user,
        default=[],
        help="Repeatable ROLE:email:display-name; identities are never embedded in source.",
    )
    argument_parser.add_argument(
        "--domain-mapping",
        action="append",
        type=parse_domain_mapping,
        default=[],
        help="Repeatable domain:organization-slug mapping for development only.",
    )
    return argument_parser


async def run(arguments: argparse.Namespace) -> None:
    settings = SeedSettings(_env_file=arguments.env_file)
    database = Database(settings)
    try:
        async with database.transaction() as session:
            await seed(
                session,
                organization_name=arguments.organization_name,
                organization_slug=arguments.organization_slug,
                users=tuple(arguments.user),
                domain_mappings=tuple(arguments.domain_mapping),
            )
    finally:
        await database.dispose()


def main() -> None:
    asyncio.run(run(parser().parse_args()))


if __name__ == "__main__":
    main()
