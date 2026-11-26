package ke.co.homescout.features.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Close
import androidx.compose.material.icons.filled.ExpandMore
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.NotificationsNone
import androidx.compose.material.icons.filled.PersonOutline
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.Wallet
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.NavigationDrawerItem
import androidx.compose.material3.NavigationDrawerItemDefaults
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import ke.co.homescout.navigation.Destination
import ke.co.homescout.features.home.roleDisplayName
import ke.co.homescout.ui.theme.HomeScoutColors

private data class ProfileDrawerItem(
    val title: String,
    val route: String,
    val icon: ImageVector
)

@Composable
fun HomeScoutProfileDrawer(
    name: String,
    email: String,
    initials: String,
    roles: List<String>,
    activeRoleCode: String?,
    currentRoute: String?,
    emailVerified: Boolean,
    onClose: () -> Unit,
    onNavigate: (String) -> Unit,
    onSelectRole: (String) -> Unit,
    onSignOut: () -> Unit
) {
    var confirmSignOut by rememberSaveable { mutableStateOf(false) }
    var roleMenuExpanded by rememberSaveable { mutableStateOf(false) }
    val selectedRole = activeRoleCode?.takeIf { it in roles } ?: roles.firstOrNull().orEmpty()
    val items = buildList {
        if (email.isBlank()) {
            add(ProfileDrawerItem("Browse homes", Destination.Discover.route, Icons.Filled.Search))
            add(ProfileDrawerItem("Explore areas", Destination.Neighbourhoods.route, Icons.Filled.Home))
            add(ProfileDrawerItem("Sign in or create account", Destination.Profile.route, Icons.Filled.PersonOutline))
        } else {
            add(ProfileDrawerItem("My profile", Destination.Profile.route, Icons.Filled.PersonOutline))
            add(ProfileDrawerItem("Notifications", "hub/notifications", Icons.Filled.NotificationsNone))
            add(ProfileDrawerItem("Settings", "hub/settings", Icons.Filled.Settings))
            when (selectedRole) {
                "tenant" -> {
                    add(ProfileDrawerItem("Saved homes", "hub/saved", Icons.Filled.FavoriteBorder))
                    add(ProfileDrawerItem("Messages & viewings", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("My schedule", "hub/schedule", Icons.Filled.CalendarMonth))
                    add(ProfileDrawerItem("SmartRent finance", Destination.Finance.route, Icons.Filled.Wallet))
                    add(ProfileDrawerItem("Trust & safety", "trust-safety", Icons.Filled.Security))
                }
                "roommate" -> {
                    add(ProfileDrawerItem("Saved homes", "hub/saved", Icons.Filled.FavoriteBorder))
                    add(ProfileDrawerItem("Shared home search", "collaboration?tab=Groups", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("Messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("Housing finance", Destination.Finance.route, Icons.Filled.Wallet))
                }
                "landlord" -> {
                    add(ProfileDrawerItem("Manage my listings", "listing-management", Icons.Filled.Home))
                    add(ProfileDrawerItem("Tenant enquiries", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("Viewings and schedule", "collaboration?tab=Viewings", Icons.Filled.CalendarMonth))
                    add(ProfileDrawerItem("Trust & verification", "trust-safety", Icons.Filled.Security))
                }
                "real_estate_agent" -> {
                    add(ProfileDrawerItem("Assigned listings", "listing-management", Icons.Filled.Home))
                    add(ProfileDrawerItem("Client property search", Destination.Discover.route, Icons.Filled.Search))
                    add(ProfileDrawerItem("Client enquiries", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("Viewings and schedule", "collaboration?tab=Viewings", Icons.Filled.CalendarMonth))
                    add(ProfileDrawerItem("Trust & verification", "trust-safety", Icons.Filled.Security))
                }
                "property_manager" -> {
                    add(ProfileDrawerItem("Managed properties", "listing-management", Icons.Filled.Home))
                    add(ProfileDrawerItem("Maintenance requests", "services?tab=Maintenance", Icons.Filled.Settings))
                    add(ProfileDrawerItem("Resident messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("Property schedule", "hub/schedule", Icons.Filled.CalendarMonth))
                    add(ProfileDrawerItem("Trust & verification", "trust-safety", Icons.Filled.Security))
                }
                "service_provider" -> {
                    add(ProfileDrawerItem("Provider profile", "services?tab=Provider", Icons.Filled.Settings))
                    add(ProfileDrawerItem("Booking requests", "services?tab=Bookings", Icons.Filled.CalendarMonth))
                    add(ProfileDrawerItem("Customer messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                    add(ProfileDrawerItem("Work schedule", "hub/schedule", Icons.Filled.CalendarMonth))
                    add(ProfileDrawerItem("Trust & verification", "trust-safety", Icons.Filled.Security))
                }
                "moderator" -> {
                    add(ProfileDrawerItem("Moderation review", "trust-safety?section=Staff%20review", Icons.Filled.Security))
                    add(ProfileDrawerItem("My submitted reports", "trust-safety?section=Reports", Icons.Filled.AdminPanelSettings))
                }
                "admin", "super_admin" -> {
                    add(ProfileDrawerItem("Platform operations", "admin-operations", Icons.Filled.AdminPanelSettings))
                    add(ProfileDrawerItem("Reports and trust", "admin-operations?section=Reports", Icons.Filled.Security))
                    if (selectedRole == "super_admin") {
                        add(ProfileDrawerItem("Role assignments", "admin-operations?section=Roles", Icons.Filled.AdminPanelSettings))
                        add(ProfileDrawerItem("Audit history", "admin-operations?section=Audit", Icons.Filled.AdminPanelSettings))
                    }
                }
                else -> {
                    add(ProfileDrawerItem("Saved homes", "hub/saved", Icons.Filled.FavoriteBorder))
                    add(ProfileDrawerItem("Messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline))
                }
            }
        }
    }
    Column(
        modifier = Modifier.fillMaxHeight().padding(horizontal = 12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Row(
            modifier = Modifier.fillMaxWidth().padding(top = 6.dp),
            horizontalArrangement = Arrangement.End
        ) {
            IconButton(onClick = onClose) {
                Icon(Icons.Filled.Close, contentDescription = "Close profile menu", tint = Color.White)
            }
        }

        Column(
            modifier = Modifier.fillMaxWidth().padding(top = 8.dp, bottom = 18.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Surface(modifier = Modifier.size(78.dp), shape = CircleShape, color = Color(0xFFF4E9DE)) {
                Box(contentAlignment = Alignment.Center) {
                    Text(
                        initials.ifBlank { "HS" },
                        style = MaterialTheme.typography.headlineSmall,
                        color = HomeScoutColors.navy,
                        fontWeight = FontWeight.Bold
                    )
                }
            }
            Text(
                name.ifBlank { "Welcome to HomeScout" },
                style = MaterialTheme.typography.titleMedium,
                color = Color.White,
                fontWeight = FontWeight.SemiBold,
                maxLines = 1,
                overflow = TextOverflow.Ellipsis
            )
            if (email.isNotBlank()) {
                Text(
                    email,
                    style = MaterialTheme.typography.bodySmall,
                    color = Color.White.copy(alpha = .72f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            if (roles.isNotEmpty()) {
                Text(
                    if (selectedRole.isNotBlank()) "Active workspace · ${roleDisplayName(selectedRole)}" else roles.joinToString(" · ") { roleDisplayName(it) },
                    style = MaterialTheme.typography.labelSmall,
                    color = Color.White.copy(alpha = .86f),
                    maxLines = 1,
                    overflow = TextOverflow.Ellipsis
                )
            }
            if (roles.size > 1) {
                Box {
                    androidx.compose.material3.TextButton(onClick = { roleMenuExpanded = true }) {
                        Text("Switch workspace", color = Color.White)
                        Icon(Icons.Filled.ExpandMore, contentDescription = null, tint = Color.White)
                    }
                    DropdownMenu(expanded = roleMenuExpanded, onDismissRequest = { roleMenuExpanded = false }) {
                        roles.forEach { role ->
                            DropdownMenuItem(
                                text = { Text(roleDisplayName(role)) },
                                onClick = {
                                    roleMenuExpanded = false
                                    if (role != selectedRole) onSelectRole(role)
                                },
                                leadingIcon = if (role == selectedRole) {
                                    { Icon(Icons.Filled.Home, contentDescription = "Current workspace") }
                                } else null
                            )
                        }
                    }
                }
            }
            if (email.isNotBlank()) {
                Text(
                    if (emailVerified) "Email verified" else "Email verification pending",
                    style = MaterialTheme.typography.labelSmall,
                    color = if (emailVerified) HomeScoutColors.darkGreenText else HomeScoutColors.amber
                )
            }
        }

        HorizontalDivider(color = Color.White.copy(alpha = .14f))
        Text(
            if (email.isBlank()) "EXPLORE HOMESCOUT" else "YOUR HOMESCOUT",
            modifier = Modifier.fillMaxWidth().padding(start = 12.dp, top = 18.dp, bottom = 8.dp),
            style = MaterialTheme.typography.labelSmall,
            color = Color.White.copy(alpha = .62f),
            fontWeight = FontWeight.SemiBold
        )

        Column(
            modifier = Modifier.weight(1f).fillMaxWidth().verticalScroll(rememberScrollState()),
            verticalArrangement = Arrangement.spacedBy(2.dp)
        ) {
            items.forEach { item ->
                val selected = currentRoute == item.route ||
                    (item.route == "collaboration?tab=Messages" && currentRoute?.startsWith("collaboration") == true)
                NavigationDrawerItem(
                    label = { Text(item.title, maxLines = 1, overflow = TextOverflow.Ellipsis) },
                    selected = selected,
                    onClick = { onNavigate(item.route) },
                    icon = { Icon(item.icon, contentDescription = null) },
                    badge = {
                        Icon(
                            Icons.AutoMirrored.Filled.ArrowForward,
                            contentDescription = null,
                            modifier = Modifier.size(16.dp)
                        )
                    },
                    modifier = Modifier.fillMaxWidth(),
                    colors = NavigationDrawerItemDefaults.colors(
                        selectedContainerColor = Color.White.copy(alpha = .13f),
                        unselectedContainerColor = Color.Transparent,
                        selectedIconColor = Color.White,
                        unselectedIconColor = Color.White.copy(alpha = .82f),
                        selectedTextColor = Color.White,
                        unselectedTextColor = Color.White.copy(alpha = .92f)
                    )
                )
            }
            if (email.isNotBlank()) {
                NavigationDrawerItem(
                    label = { Text("Sign out") },
                    selected = false,
                    onClick = { confirmSignOut = true },
                    icon = { Icon(Icons.Filled.Close, contentDescription = null) },
                    modifier = Modifier.fillMaxWidth(),
                    colors = NavigationDrawerItemDefaults.colors(
                        unselectedContainerColor = Color.Transparent,
                        unselectedIconColor = Color.White.copy(alpha = .82f),
                        unselectedTextColor = Color.White.copy(alpha = .92f)
                    )
                )
            }
        }

        Text(
            "HomeScout · Kenya",
            modifier = Modifier.fillMaxWidth().padding(start = 12.dp, top = 12.dp, bottom = 18.dp),
            style = MaterialTheme.typography.labelSmall,
            color = Color.White.copy(alpha = .56f)
        )
    }

    if (confirmSignOut) {
        AlertDialog(
            onDismissRequest = { confirmSignOut = false },
            title = { Text("Sign out of HomeScout?") },
            text = { Text("You can sign in again whenever you need your account.") },
            confirmButton = {
                TextButton(onClick = {
                    confirmSignOut = false
                    onSignOut()
                }) { Text("Sign out") }
            },
            dismissButton = {
                TextButton(onClick = { confirmSignOut = false }) { Text("Cancel") }
            }
        )
    }
}
