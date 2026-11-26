package ke.co.homescout.features.home

import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.PaddingValues
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ManageSearch
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Checklist
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.PersonSearch
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Handyman
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.theme.HomeScoutColors

private data class WorkspaceAction(
    val title: String,
    val description: String,
    val route: String,
    val icon: ImageVector
)

private data class Workspace(
    val title: String,
    val subtitle: String,
    val actions: List<WorkspaceAction>
)

private fun workspaceFor(role: String): Workspace = when (role) {
    "landlord" -> Workspace(
        "Landlord workspace",
        "Manage homes you own, respond to enquiries, and coordinate viewings.",
        listOf(
            WorkspaceAction("Your property listings", "Create, edit, and review homes linked to your account.", "listing-management", Icons.Filled.HomeWork),
            WorkspaceAction("Tenant enquiries", "Open conversations about your listings.", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline),
            WorkspaceAction("Viewings", "Review and coordinate viewing requests.", "collaboration?tab=Viewings", Icons.Filled.CalendarMonth),
            WorkspaceAction("Your schedule", "Keep property tasks and viewing plans together.", "hub/schedule", Icons.Filled.Checklist),
            WorkspaceAction("Trust and verification", "Manage evidence and review the safety guidance.", "trust-safety", Icons.Filled.VerifiedUser)
        )
    )
    "real_estate_agent" -> Workspace(
        "Agent workspace",
        "Work with assigned listings, match homes to clients, and follow up on viewings.",
        listOf(
            WorkspaceAction("Assigned listings", "Open listing work available to your account.", "listing-management", Icons.Filled.HomeWork),
            WorkspaceAction("Find homes for clients", "Search the current property inventory and apply filters.", "discover", Icons.AutoMirrored.Filled.ManageSearch),
            WorkspaceAction("Client enquiries", "Continue conversations you are authorized to access.", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline),
            WorkspaceAction("Viewings", "Coordinate property viewing requests.", "collaboration?tab=Viewings", Icons.Filled.CalendarMonth),
            WorkspaceAction("Follow-up schedule", "Keep reminders and next steps in one place.", "hub/schedule", Icons.Filled.Checklist)
        )
    )
    "property_manager" -> Workspace(
        "Property manager workspace",
        "Focus on assigned homes, maintenance coordination, and resident communication.",
        listOf(
            WorkspaceAction("Managed properties", "Review listings assigned to your management scope.", "listing-management", Icons.Filled.HomeWork),
            WorkspaceAction("Maintenance requests", "Review requests and authorized maintenance actions.", "services?tab=Maintenance", Icons.Filled.Build),
            WorkspaceAction("Resident messages", "Open conversations available to your account.", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline),
            WorkspaceAction("Property schedule", "Track service visits, viewings, and follow-ups.", "hub/schedule", Icons.Filled.CalendarMonth),
            WorkspaceAction("Service coordination", "Browse home services when you need a provider.", "services?tab=Explore", Icons.Filled.Handyman)
        )
    )
    "service_provider" -> Workspace(
        "Service provider workspace",
        "Manage your provider profile and the service bookings assigned to you.",
        listOf(
            WorkspaceAction("Provider profile", "Review the services and details shown for your account.", "services?tab=Provider", Icons.Filled.Handyman),
            WorkspaceAction("Booking requests", "Review and respond to authorized service bookings.", "services?tab=Bookings", Icons.Filled.CalendarMonth),
            WorkspaceAction("Customer messages", "Continue conversations available to your account.", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline),
            WorkspaceAction("Work schedule", "Keep your service appointments and follow-ups organized.", "hub/schedule", Icons.Filled.Checklist),
            WorkspaceAction("Service discovery", "See the current home-service catalogue.", "services?tab=Explore", Icons.AutoMirrored.Filled.ManageSearch)
        )
    )
    "roommate" -> Workspace(
        "Shared home search",
        "Find compatible housemates and coordinate a home search with your group.",
        listOf(
            WorkspaceAction("Roommate matches", "Update your preferences and review available match suggestions.", "collaboration?tab=Roommates", Icons.Filled.PersonSearch),
            WorkspaceAction("Shared groups", "Coordinate searches, comparisons, and moving tasks.", "collaboration?tab=Groups", Icons.Filled.Groups),
            WorkspaceAction("Messages", "Open your authorized conversations.", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline),
            WorkspaceAction("Browse homes", "Search available public property records.", "discover", Icons.Filled.LocationOn),
            WorkspaceAction("Housing budget", "Plan KES costs using figures you choose to enter.", "finance", Icons.Filled.AccountBalanceWallet)
        )
    )
    "moderator" -> Workspace(
        "Moderation workspace",
        "Review reported content and safety cases using the permissions granted to your account.",
        listOf(
            WorkspaceAction("Moderation review", "Open the staff review tools for reported cases.", "trust-safety?section=Staff%20review", Icons.Filled.Security),
            WorkspaceAction("My submitted reports", "Check reports and safety cases created from this account.", "trust-safety?section=Reports", Icons.Filled.AdminPanelSettings),
            WorkspaceAction("Notifications", "Review updates assigned to your account.", "hub/notifications", Icons.Filled.VerifiedUser)
        )
    )
    "admin" -> Workspace(
        "Operations workspace",
        "Manage platform operations within your assigned administrative permissions.",
        listOf(
            WorkspaceAction("Platform overview", "Review operational information available to staff.", "admin-operations", Icons.Filled.AdminPanelSettings),
            WorkspaceAction("Listings review", "Open the listing operations queue.", "admin-operations?section=Listings", Icons.Filled.HomeWork),
            WorkspaceAction("Reports and moderation", "Review reported content and moderation records.", "admin-operations?section=Reports", Icons.Filled.Security),
            WorkspaceAction("Support tickets", "Review support cases available to your role.", "admin-operations?section=Support", Icons.Filled.ChatBubbleOutline)
        )
    )
    "super_admin" -> Workspace(
        "Platform administration",
        "Access audited platform controls granted to the Super Admin role.",
        listOf(
            WorkspaceAction("Operations overview", "Review current operational information.", "admin-operations", Icons.Filled.AdminPanelSettings),
            WorkspaceAction("Role assignments", "Manage role assignments through the protected staff workflow.", "admin-operations?section=Roles", Icons.Filled.VerifiedUser),
            WorkspaceAction("Platform settings", "Open operational settings available to your account.", "admin-operations?section=Settings", Icons.Filled.Build),
            WorkspaceAction("Audit history", "Review recorded administrative actions.", "admin-operations?section=Audit", Icons.Filled.Checklist),
            WorkspaceAction("Trust review", "Open verification, safety, and moderation tools.", "trust-safety?section=Staff%20review", Icons.Filled.Security)
        )
    )
    else -> Workspace(
        "HomeScout home search",
        "Explore homes, areas, and tools available to your account.",
        listOf(
            WorkspaceAction("Browse homes", "Search the current public property inventory.", "discover", Icons.AutoMirrored.Filled.ManageSearch),
            WorkspaceAction("Saved homes", "Open homes and searches you have saved.", "hub/saved", Icons.Filled.FavoriteBorder),
            WorkspaceAction("Messages", "Continue conversations you can access.", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline),
            WorkspaceAction("Housing budget", "Plan KES costs using your own figures.", "finance", Icons.Filled.AccountBalanceWallet),
            WorkspaceAction("Explore areas", "Browse Kenyan counties, towns, and neighbourhoods.", "neighbourhoods", Icons.Filled.LocationOn)
        )
    )
}

fun roleDisplayName(role: String): String = when (role) {
    "real_estate_agent" -> "Real estate agent"
    "property_manager" -> "Property manager"
    "service_provider" -> "Service provider"
    "super_admin" -> "Super Admin"
    else -> role.replace('_', ' ').replaceFirstChar { it.uppercase() }
}

@Composable
fun RoleDashboardScreen(
    roleCode: String,
    accountName: String,
    onNavigate: (String) -> Unit
) {
    val workspace = workspaceFor(roleCode)
    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = PaddingValues(horizontal = 20.dp, vertical = 18.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("${roleDisplayName(roleCode).uppercase()} WORKSPACE", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary)
                Text(
                    if (accountName.isBlank()) workspace.title else "${accountName.substringBefore(' ')}’s ${workspace.title.lowercase().replaceFirstChar { it.uppercase() }}",
                    style = MaterialTheme.typography.headlineMedium,
                    fontWeight = FontWeight.Bold
                )
                Text(workspace.subtitle, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Surface(color = MaterialTheme.colorScheme.secondaryContainer, shape = RoundedCornerShape(50)) {
                    Text(
                        "Showing tools for your ${roleDisplayName(roleCode)} role",
                        modifier = Modifier.padding(horizontal = 13.dp, vertical = 8.dp),
                        style = MaterialTheme.typography.labelMedium,
                        color = MaterialTheme.colorScheme.onSecondaryContainer
                    )
                }
            }
        }
        item { Text("Your work", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, modifier = Modifier.padding(top = 8.dp)) }
        items(workspace.actions.size) { index ->
            val action = workspace.actions[index]
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Row(
                    modifier = Modifier.fillMaxWidth().clickable { onNavigate(action.route) }.padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(14.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Surface(color = MaterialTheme.colorScheme.primaryContainer, shape = RoundedCornerShape(14.dp)) {
                        Icon(action.icon, contentDescription = null, tint = HomeScoutColors.navy, modifier = Modifier.padding(12.dp))
                    }
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        Text(action.title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(action.description, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Open ${action.title}", tint = MaterialTheme.colorScheme.primary)
                }
            }
        }
    }
}
