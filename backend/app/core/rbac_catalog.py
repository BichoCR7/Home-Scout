"""The HomeScout role and permission vocabulary. Missing grants are denied."""

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class RoleDefinition:
    code: str
    name: str
    description: str
    persistent: bool = True


ROLE_DEFINITIONS = (
    RoleDefinition("guest", "Guest", "Unauthenticated public access only.", persistent=False),
    RoleDefinition("tenant", "Tenant / House Hunter", "Renter and housing search account."),
    RoleDefinition(
        "roommate", "Roommate / Shared Search Member", "Member of explicitly shared groups."
    ),
    RoleDefinition(
        "landlord", "Landlord / Property Owner", "Owner access for owned property workflows."
    ),
    RoleDefinition("real_estate_agent", "Real Estate Agent", "Access to assigned listing work."),
    RoleDefinition(
        "property_manager", "Property Manager", "Access to assigned portfolio workflows."
    ),
    RoleDefinition(
        "service_provider", "Service Provider", "Access to own services and assigned bookings."
    ),
    RoleDefinition(
        "moderator", "Moderator", "Access to reported content and moderation workflows."
    ),
    RoleDefinition("admin", "Admin", "Limited operational administration."),
    RoleDefinition(
        "super_admin", "Super Admin", "Audited platform security and role administration."
    ),
)

ROLE_BY_CODE = {role.code: role for role in ROLE_DEFINITIONS}
PERSISTED_ROLE_CODES = tuple(role.code for role in ROLE_DEFINITIONS if role.persistent)

REQUESTABLE_ROLE_CODES = {
    "tenant",
    "landlord",
    "real_estate_agent",
    "property_manager",
    "service_provider",
}

GLOBAL_SCOPE = ("global", "*")
ALLOWED_SCOPE_TYPES = {
    "global",
    "property",
    "portfolio",
    "booking",
    "document",
    "group",
    "conversation",
    "moderation",
    "administrative_workflow",
}


def permission_description(code: str) -> str:
    """Describe resource:action:scope permission codes without granting them."""

    parts = code.split(":", maxsplit=2)
    if len(parts) != 3:
        return "Platform permission."
    resource, action, scope = parts
    return f"{action.replace('_', ' ').title()} {resource.replace('_', ' ')} in {scope} scope."


ROLE_PERMISSION_CODES: dict[str, frozenset[str]] = {
    "tenant": frozenset(
        {
            "profile:view:self",
            "profile:edit:self",
            "account:view:self",
            "account:edit:self",
            "session:view:self",
            "session:revoke:self",
            "property:view:public",
            "property:save:self",
            "property:compare:public",
            "property:report:self",
            "listing:view:public",
            "search:history:self",
            "alert:manage:self",
            "enquiry:create:self",
            "financial_record:view:self",
            "document:view:self",
            "conversation:view:participant",
            "conversation:send:participant",
            "viewing:create:self",
            "viewing:view:participant",
            "roommate:manage:self",
            "roommate:search:public",
            "roommate:connect:public",
            "shared_group:create:self",
            "activity:view:self",
            "booking:view:self",
            "booking:create:self",
            "payment:create:self",
            "payment:view:self",
            "maintenance:create:self",
            "maintenance:view:self",
            "move_plan:manage:self",
            "room_setup:manage:self",
            "service_review:create:self",
            "shared_group:view:member",
            "shared_group:manage:owned",
            "shared_search:manage:member",
            "shared_comparison:view:member",
            "shared_task:view:member",
            "shared_financial_goal:view:shared",
        }
    ),
    "roommate": frozenset(
        {
            "profile:view:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "conversation:view:participant",
            "conversation:send:participant",
            "viewing:create:self",
            "viewing:view:participant",
            "roommate:manage:self",
            "roommate:search:public",
            "roommate:connect:public",
            "booking:view:self",
            "booking:create:self",
            "payment:create:self",
            "payment:view:self",
            "maintenance:create:self",
            "maintenance:view:self",
            "move_plan:manage:self",
            "room_setup:manage:self",
            "service_review:create:self",
            "shared_group:create:self",
            "shared_group:view:member",
            "shared_group:manage:owned",
            "shared_collection:view:member",
            "shared_comparison:view:member",
            "shared_search:manage:member",
            "shared_task:view:member",
            "shared_viewing:view:member",
            "shared_financial_goal:view:shared",
        }
    ),
    "landlord": frozenset(
        {
            "profile:view:self",
            "profile:edit:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "property:view:owned",
            "property:create:self",
            "property:edit:owned",
            "listing:view:owned",
            "listing:create:owned",
            "listing:edit:owned",
            "listing:delete:owned",
            "listing:publish:owned",
            "listing:archive:owned",
            "listing:assign:owned",
            "enquiry:view:assigned",
            "enquiry:manage:assigned",
            "viewing:manage:assigned",
            "maintenance:manage:assigned",
            "conversation:view:participant",
            "conversation:send:participant",
            "viewing:view:participant",
            "shared_group:view:member",
            "shared_search:manage:member",
            "shared_comparison:view:member",
            "shared_task:view:member",
            "shared_financial_goal:view:shared",
            "verification:create:self",
        }
    ),
    "real_estate_agent": frozenset(
        {
            "profile:view:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "property:view:assigned",
            "listing:view:assigned",
            "listing:create:assigned",
            "listing:edit:assigned",
            "listing:publish:assigned",
            "listing:archive:assigned",
            "enquiry:view:assigned",
            "enquiry:manage:assigned",
            "viewing:manage:assigned",
            "maintenance:manage:assigned",
            "conversation:view:participant",
            "conversation:send:participant",
            "viewing:view:participant",
            "shared_group:view:member",
            "shared_search:manage:member",
            "shared_comparison:view:member",
            "shared_task:view:member",
            "shared_financial_goal:view:shared",
            "verification:create:self",
        }
    ),
    "property_manager": frozenset(
        {
            "profile:view:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "portfolio:view:assigned",
            "property:view:assigned",
            "property:edit:assigned",
            "listing:edit:assigned",
            "listing:publish:assigned",
            "listing:archive:assigned",
            "tenant:view:assigned",
            "maintenance:manage:assigned",
            "maintenance:view:assigned",
            "enquiry:view:assigned",
            "enquiry:manage:assigned",
            "viewing:manage:assigned",
            "document:view:assigned",
            "service_provider:view:assigned",
            "viewing:view:participant",
            "conversation:view:participant",
            "conversation:send:participant",
            "shared_group:view:member",
            "shared_search:manage:member",
            "shared_comparison:view:member",
            "shared_task:view:member",
            "shared_financial_goal:view:shared",
        }
    ),
    "service_provider": frozenset(
        {
            "profile:view:self",
            "profile:edit:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "service:view:self",
            "service:create:self",
            "service:edit:self",
            "booking:view:assigned",
            "booking:manage:assigned",
            "order:view:assigned",
            "maintenance:view:assigned",
            "customer:view:booking_participant",
            "review:view:self",
            "verification:create:self",
            "payment_record:view:booking_participant",
            "payment:view:booking_participant",
            "conversation:view:participant",
            "conversation:send:participant",
            "shared_group:view:member",
            "shared_search:manage:member",
            "shared_comparison:view:member",
            "shared_task:view:member",
            "shared_financial_goal:view:shared",
        }
    ),
    "moderator": frozenset(
        {
            "profile:view:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "moderation:view:reported",
            "moderation:approve:reported",
            "moderation:reject:reported",
            "report:view:assigned",
            "escalation:create:assigned",
            "audit:view:moderation",
        }
    ),
    "admin": frozenset(
        {
            "profile:view:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "user:view:basic",
            "user:edit:basic",
            "listing:view:platform",
            "listing:manage:platform",
            "service:manage:platform",
            "verification:approve:assigned",
            "verification:reject:assigned",
            "report:view:assigned",
            "moderation:view:assigned",
            "moderation:approve:reported",
            "moderation:reject:reported",
            "escalation:create:assigned",
            "support:manage:assigned",
            "category:manage:global",
            "location:manage:global",
            "analytics:view:platform",
            "audit:view:administrative_workflow",
            "roles:assign:operational",
            "payment:view:global",
            "payment:reconcile:global",
        }
    ),
    "super_admin": frozenset(
        {
            "profile:view:self",
            "account:view:self",
            "session:view:self",
            "session:revoke:self",
            "user:view:basic",
            "user:edit:basic",
            "listing:view:platform",
            "listing:manage:platform",
            "service:manage:platform",
            "verification:approve:assigned",
            "verification:reject:assigned",
            "report:view:assigned",
            "moderation:view:assigned",
            "moderation:approve:reported",
            "moderation:reject:reported",
            "escalation:create:assigned",
            "support:manage:assigned",
            "category:manage:global",
            "location:manage:global",
            "analytics:view:platform",
            "audit:view:administrative_workflow",
            "roles:assign:operational",
            "roles:assign:administrative",
            "roles:view:global",
            "roles:revoke:global",
            "security:manage:global",
            "integrations:manage:global",
            "system:manage:global",
            "payment:view:global",
            "payment:reconcile:global",
        }
    ),
}

for _assistant_role in (
    "tenant",
    "roommate",
    "landlord",
    "real_estate_agent",
    "property_manager",
    "service_provider",
    "moderator",
    "admin",
    "super_admin",
):
    ROLE_PERMISSION_CODES[_assistant_role] = ROLE_PERMISSION_CODES[_assistant_role] | frozenset(
        {"assistant:use:self", "assistant:history:self"}
    )

PERMISSION_CODES = frozenset().union(*ROLE_PERMISSION_CODES.values())


def role_permission_pairs() -> tuple[tuple[str, str], ...]:
    return tuple(
        (role_code, permission_code)
        for role_code, permission_codes in ROLE_PERMISSION_CODES.items()
        for permission_code in sorted(permission_codes)
    )
