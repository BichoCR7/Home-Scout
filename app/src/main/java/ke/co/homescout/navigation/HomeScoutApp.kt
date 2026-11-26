package ke.co.homescout.navigation

import androidx.compose.foundation.layout.fillMaxHeight
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Groups
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.NotificationsNone
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.runtime.DisposableEffect
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.setValue
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.vector.ImageVector
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.unit.dp
import androidx.navigation.NavGraph.Companion.findStartDestination
import androidx.navigation.compose.NavHost
import androidx.navigation.compose.composable
import androidx.navigation.compose.currentBackStackEntryAsState
import androidx.navigation.compose.rememberNavController
import androidx.navigation.navArgument
import androidx.navigation.NavType
import ke.co.homescout.features.home.HomeScreen
import ke.co.homescout.features.home.RoleDashboardScreen
import ke.co.homescout.features.admin.OperationsScreen
import ke.co.homescout.features.assistant.AssistantScreen
import ke.co.homescout.features.placeholder.FeaturePlaceholderScreen
import ke.co.homescout.features.discover.DiscoverScreen
import ke.co.homescout.features.collaboration.CollaborationScreen
import ke.co.homescout.features.discover.PropertyDetailScreen
import ke.co.homescout.features.discover.ListingManagementScreen
import ke.co.homescout.features.profile.ProfileScreen
import ke.co.homescout.features.profile.AuthEntryScreen
import ke.co.homescout.features.profile.HomeScoutProfileDrawer
import ke.co.homescout.features.profile.PersonalHubScreen
import ke.co.homescout.features.map.MapScreen
import ke.co.homescout.features.finance.SmartRentScreen
import ke.co.homescout.features.finance.PaymentsScreen
import ke.co.homescout.features.areas.AreasScreen
import ke.co.homescout.features.trust.TrustSafetyScreen
import ke.co.homescout.features.services.ServicesScreen
import ke.co.homescout.data.auth.AuthController
import ke.co.homescout.data.remote.PersonalHubApi
import ke.co.homescout.ui.components.HomeScoutLogo
import ke.co.homescout.ui.components.ProfileAvatar
import ke.co.homescout.ui.theme.HomeScoutColors
import kotlinx.coroutines.launch
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.withContext
import org.json.JSONObject

private data class WorkspaceNavItem(
    val label: String,
    val route: String,
    val icon: ImageVector,
    val argumentKey: String? = null,
    val argumentValue: String? = null
)

private fun workspaceTabs(role: String): List<WorkspaceNavItem> = when (role) {
    "landlord" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Listings", "listing-management", Icons.Filled.HomeWork),
        WorkspaceNavItem("Messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline, "tab", "Messages"),
        WorkspaceNavItem("Schedule", "hub/schedule", Icons.Filled.CalendarMonth),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "real_estate_agent" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Listings", "listing-management", Icons.Filled.HomeWork),
        WorkspaceNavItem("Search", "discover", Icons.Filled.Search),
        WorkspaceNavItem("Messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline, "tab", "Messages"),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "property_manager" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Portfolio", "listing-management", Icons.Filled.HomeWork),
        WorkspaceNavItem("Repairs", "services?tab=Maintenance", Icons.Filled.Build, "tab", "Maintenance"),
        WorkspaceNavItem("Messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline, "tab", "Messages"),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "service_provider" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Services", "services?tab=Provider", Icons.Filled.DirectionsCar, "tab", "Provider"),
        WorkspaceNavItem("Bookings", "services?tab=Bookings", Icons.Filled.CalendarMonth, "tab", "Bookings"),
        WorkspaceNavItem("Messages", "collaboration?tab=Messages", Icons.Filled.ChatBubbleOutline, "tab", "Messages"),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "roommate" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Homes", "discover", Icons.Filled.Search),
        WorkspaceNavItem("Shared", "collaboration?tab=Groups", Icons.Filled.Groups, "tab", "Groups"),
        WorkspaceNavItem("Finance", "finance", Icons.Filled.Payments),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "moderator" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Trust", "trust-safety?section=Staff%20review", Icons.Filled.Security, "section", "Staff review"),
        WorkspaceNavItem("Reports", "trust-safety?section=Reports", Icons.Filled.AdminPanelSettings, "section", "Reports"),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "admin" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Operations", "admin-operations", Icons.Filled.AdminPanelSettings),
        WorkspaceNavItem("Reports", "admin-operations?section=Reports", Icons.Filled.Security, "section", "Reports"),
        WorkspaceNavItem("Trust", "trust-safety?section=Staff%20review", Icons.Filled.Security, "section", "Staff review"),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    "super_admin" -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Operations", "admin-operations", Icons.Filled.AdminPanelSettings),
        WorkspaceNavItem("Trust", "trust-safety?section=Staff%20review", Icons.Filled.Security, "section", "Staff review"),
        WorkspaceNavItem("Roles", "admin-operations?section=Roles", Icons.Filled.Groups, "section", "Roles"),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
    else -> listOf(
        WorkspaceNavItem("Home", "home", Icons.Filled.Home),
        WorkspaceNavItem("Discover", "discover", Icons.Filled.Search),
        WorkspaceNavItem("Areas", "neighbourhoods", Icons.Filled.LocationOn),
        WorkspaceNavItem("Finance", "finance", Icons.Filled.Payments),
        WorkspaceNavItem("Profile", "profile", Icons.Filled.AccountCircle)
    )
}

private fun WorkspaceNavItem.isSelected(route: String?, arguments: android.os.Bundle?): Boolean {
    val root = route?.substringBefore('?')
    val itemRoot = this.route.substringBefore('?').substringBefore('/')
    if (argumentKey != null && argumentValue != null) {
        return root == itemRoot && arguments?.getString(argumentKey) == argumentValue
    }
    return when {
        this.route == "profile" -> root == "profile" || (root == "hub" && arguments?.getString("section") in setOf("profile", "settings", "hub"))
        this.route.startsWith("hub/") -> root == "hub" && arguments?.getString("section") == this.route.substringAfter("hub/")
        this.route == "home" -> root == "home"
        this.route == "finance" -> root == "finance" || root == "payments"
        else -> root == itemRoot || root?.startsWith("$itemRoot/") == true
    }
}

private fun defaultWorkspace(roles: List<String>): String {
    val priority = listOf("tenant", "roommate", "landlord", "real_estate_agent", "property_manager", "service_provider", "moderator", "admin", "super_admin")
    return priority.firstOrNull { it in roles } ?: roles.firstOrNull().orEmpty()
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun HomeScoutApp(
    onAppearanceChange: (String) -> Unit,
    onLargerTextChange: (Boolean) -> Unit
) {
    val context = LocalContext.current
    val authController = remember(context) { AuthController(context.applicationContext) }
    val authState = authController.state
    val accessToken = authController.accessToken()
    LaunchedEffect(authController) { authController.restoreSession() }
    DisposableEffect(authController) {
        onDispose { authController.close() }
    }
    val nav = rememberNavController()
    val drawerState = rememberDrawerState(DrawerValue.Closed)
    val scope = rememberCoroutineScope()
    val appSnackbar = remember { SnackbarHostState() }
    var guestBrowsing by rememberSaveable { mutableStateOf(false) }
    val backStack by nav.currentBackStackEntryAsState()
    val currentRoute = backStack?.destination?.route
    val currentArguments = backStack?.arguments
    var activeRoleCode by rememberSaveable(authState.user?.id) { mutableStateOf("") }
    var mapFullscreen by remember { mutableStateOf(false) }
    LaunchedEffect(currentRoute) {
        if (currentRoute != Destination.Map.route) mapFullscreen = false
    }
    LaunchedEffect(authState.sessionChecked, authState.user, guestBrowsing) {
        if (!authState.sessionChecked) return@LaunchedEffect
        if (authState.user == null && guestBrowsing) return@LaunchedEffect
        val destination = if (authState.user != null) Destination.Home.route else "auth-entry"
        if (currentRoute != destination) {
            nav.navigate(destination) {
                popUpTo(nav.graph.findStartDestination().id) { inclusive = true }
                launchSingleTop = true
            }
        }
    }
    LaunchedEffect(accessToken, authState.user?.id, currentRoute == Destination.Home.route) {
        val user = authState.user
        if (user == null) {
            activeRoleCode = ""
            return@LaunchedEffect
        }
        if (currentRoute != Destination.Home.route) return@LaunchedEffect
        val serverRole = accessToken?.let { token ->
            withContext(Dispatchers.IO) {
                runCatching { PersonalHubApi().getObject("hub/profile", token).optString("active_role_code").takeUnless { it == "null" } }.getOrNull()
            }
        }
        activeRoleCode = serverRole?.takeIf { it in user.roles }
            ?: activeRoleCode.takeIf { it in user.roles }
            ?: defaultWorkspace(user.roles)
    }
    val authRoute = currentRoute?.startsWith("auth-") == true || currentRoute == null || !authState.sessionChecked
    val profileInitials = authState.user?.let { account ->
        listOf(account.givenName, account.familyName)
            .mapNotNull { it.trim().firstOrNull()?.uppercaseChar() }
            .joinToString("")
            .ifBlank { account.email.firstOrNull()?.uppercaseChar()?.toString() ?: "HS" }
    } ?: "HS"

    ModalNavigationDrawer(
        drawerState = drawerState,
        gesturesEnabled = !authRoute && !mapFullscreen,
        scrimColor = Color.Black.copy(alpha = .52f),
        drawerContent = {
            if (!authRoute && !mapFullscreen) {
                ModalDrawerSheet(
                    modifier = Modifier.fillMaxHeight().widthIn(max = 286.dp),
                    drawerShape = RoundedCornerShape(topEnd = 28.dp, bottomEnd = 28.dp),
                    drawerContainerColor = HomeScoutColors.navy,
                    drawerContentColor = Color.White,
                    drawerTonalElevation = 0.dp
                ) {
                    HomeScoutProfileDrawer(
                        name = authState.user?.let { user ->
                            listOf(user.givenName, user.familyName).filter(String::isNotBlank).joinToString(" ")
                        }.orEmpty(),
                        email = authState.user?.email.orEmpty(),
                        initials = profileInitials,
                        roles = authState.user?.roles.orEmpty(),
                        activeRoleCode = activeRoleCode.takeIf { it.isNotBlank() } ?: defaultWorkspace(authState.user?.roles.orEmpty()),
                        currentRoute = currentRoute,
                        emailVerified = authState.user?.emailVerified == true,
                        onClose = { scope.launch { drawerState.close() } },
                        onNavigate = { route ->
                            scope.launch {
                                drawerState.close()
                                nav.navigate(route) { launchSingleTop = true }
                            }
                        },
                        onSelectRole = { role ->
                            val token = accessToken
                            if (token == null || role !in authState.user?.roles.orEmpty()) {
                                scope.launch { appSnackbar.showSnackbar("Only roles assigned to this account can be selected.") }
                            } else {
                                scope.launch {
                                    runCatching {
                                        withContext(Dispatchers.IO) {
                                            PersonalHubApi().send(
                                                "hub/profile/active-role",
                                                "PUT",
                                                token,
                                                JSONObject().put("role_code", role)
                                            )
                                        }
                                    }.onSuccess {
                                        activeRoleCode = role
                                        drawerState.close()
                                        nav.navigate(Destination.Home.route) {
                                            popUpTo(Destination.Home.route) { inclusive = false }
                                            launchSingleTop = true
                                        }
                                    }.onFailure { failure ->
                                        appSnackbar.showSnackbar(failure.message ?: "Could not switch workspace.")
                                    }
                                }
                            }
                        },
                        onSignOut = {
                            scope.launch {
                                drawerState.close()
                                guestBrowsing = false
                                authController.signOut()
                            }
                        }
                    )
                }
            }
        }
    ) {
    Scaffold(
        topBar = {
            if (!authRoute && !mapFullscreen) CenterAlignedTopAppBar(
                title = { HomeScoutLogo(markSize = 34.dp) },
                navigationIcon = {
                    IconButton(onClick = { scope.launch { drawerState.open() } }) {
                        ProfileAvatar(
                            initials = profileInitials,
                            modifier = Modifier,
                            contentDescription = "Open profile"
                        )
                    }
                },
                actions = {
                    IconButton(onClick = { nav.navigate("collaboration?tab=Messages") }) {
                        Icon(Icons.Filled.ChatBubbleOutline, contentDescription = "Messages")
                    }
                    IconButton(onClick = { nav.navigate("hub/notifications") }) {
                        Icon(Icons.Filled.NotificationsNone, contentDescription = "Notifications")
                    }
                },
                colors = TopAppBarDefaults.topAppBarColors(containerColor = MaterialTheme.colorScheme.background)
            )
        },
        snackbarHost = { SnackbarHost(appSnackbar) },
        bottomBar = {
            if (!authRoute && !mapFullscreen) NavigationBar(containerColor = MaterialTheme.colorScheme.surface) {
                workspaceTabs(activeRoleCode.ifBlank { defaultWorkspace(authState.user?.roles.orEmpty()) }).forEach { item ->
                    NavigationBarItem(
                        selected = item.isSelected(currentRoute, currentArguments),
                        onClick = {
                            nav.navigate(item.route) {
                                popUpTo(nav.graph.findStartDestination().id) { saveState = true }
                                launchSingleTop = true
                                restoreState = true
                            }
                        },
                        icon = { Icon(item.icon, contentDescription = null) },
                        label = { Text(item.label) },
                        colors = NavigationBarItemDefaults.colors(
                            selectedIconColor = MaterialTheme.colorScheme.primary,
                            selectedTextColor = MaterialTheme.colorScheme.primary,
                            indicatorColor = MaterialTheme.colorScheme.primaryContainer
                        ),
                        alwaysShowLabel = true
                    )
                }
            }
        },
        floatingActionButton = {
            if (!authRoute && !mapFullscreen && !currentRoute.startsWith(Destination.Assistant.route)) {
                FloatingActionButton(
                    onClick = {
                        nav.navigate(Destination.Assistant.route) { launchSingleTop = true }
                    },
                ) {
                    Icon(Icons.Filled.AutoAwesome, contentDescription = "Ask HomeScout")
                }
            }
        }
    ) { padding ->
        if (!authState.sessionChecked) {
            Surface(Modifier.padding(padding), color = MaterialTheme.colorScheme.background) {}
        } else NavHost(navController = nav, startDestination = "auth-entry", modifier = Modifier.padding(padding)) {
            composable("auth-entry") {
                AuthEntryScreen(
                    onSignIn = { nav.navigate("auth-login") },
                    onCreateAccount = { nav.navigate("auth-register") },
                    onBrowseAsGuest = {
                        guestBrowsing = true
                        nav.navigate(Destination.Home.route) {
                            popUpTo("auth-entry") { inclusive = true }
                            launchSingleTop = true
                        }
                    }
                )
            }
            composable("auth-login") {
                ProfileScreen(authController, onNavigate = { nav.navigate(it) }, authOnly = true)
            }
            composable("auth-register") {
                ProfileScreen(authController, onNavigate = { nav.navigate(it) }, initialRegister = true, authOnly = true)
            }
            composable(Destination.Home.route) {
                val role = activeRoleCode.takeIf { it in authState.user?.roles.orEmpty() }
                    ?: defaultWorkspace(authState.user?.roles.orEmpty())
                if (authState.user == null || role.isBlank() || role == "tenant") {
                    HomeScreen(onNavigate = { nav.navigate(it) }, accessToken = accessToken)
                } else {
                    val accountName = authState.user.let { listOf(it.givenName, it.familyName).filter(String::isNotBlank).joinToString(" ") }
                    RoleDashboardScreen(role, accountName) { nav.navigate(it) }
                }
            }
            composable(
                route = "${Destination.Discover.route}?query={query}&savedFilters={savedFilters}",
                arguments = listOf(
                    navArgument("query") { type = NavType.StringType; defaultValue = "" },
                    navArgument("savedFilters") { type = NavType.StringType; defaultValue = "" }
                )
            ) { entry ->
                DiscoverScreen(
                    onNavigate = { nav.navigate(it) },
                    initialQuery = entry.arguments?.getString("query").orEmpty(),
                    initialFilters = entry.arguments?.getString("savedFilters").orEmpty(),
                    accessToken = accessToken
                )
            }
            composable(
                route = "property/{propertyId}",
                arguments = listOf(navArgument("propertyId") { type = NavType.StringType })
            ) { entry ->
                PropertyDetailScreen(
                    propertyId = entry.arguments?.getString("propertyId").orEmpty(),
                    accessToken = accessToken,
                    onBack = { nav.popBackStack() },
                    onNavigate = { nav.navigate(it) }
                )
            }
            composable(
                route = "property-preview/{propertyId}",
                arguments = listOf(navArgument("propertyId") { type = NavType.StringType })
            ) { entry ->
                PropertyDetailScreen(
                    propertyId = entry.arguments?.getString("propertyId").orEmpty(),
                    accessToken = accessToken,
                    previewOnly = true,
                    onBack = { nav.popBackStack() },
                    onNavigate = { nav.navigate(it) }
                )
            }
            composable("listing-management") {
                ListingManagementScreen(
                    accessToken = accessToken,
                    onSignIn = { nav.navigate(Destination.Profile.route) },
                    onNavigate = { nav.navigate(it) }
                )
            }
            composable(
                route = "admin-operations?section={section}",
                arguments = listOf(navArgument("section") { type = NavType.StringType; defaultValue = "Overview" })
            ) { entry ->
                OperationsScreen(
                    accessToken = accessToken,
                    onSignIn = { nav.navigate(Destination.Profile.route) },
                    onNavigate = { nav.navigate(it) },
                    initialSection = entry.arguments?.getString("section") ?: "Overview"
                )
            }
            composable(
                route = "collaboration?propertyId={propertyId}&conversationId={conversationId}&tab={tab}",
                arguments = listOf(
                    navArgument("propertyId") { type = NavType.StringType; defaultValue = "" },
                    navArgument("conversationId") { type = NavType.StringType; defaultValue = "" },
                    navArgument("tab") { type = NavType.StringType; defaultValue = "" }
                )
            ) { entry ->
                CollaborationScreen(
                    accessToken = accessToken,
                    initialPropertyId = entry.arguments?.getString("propertyId").orEmpty(),
                    initialConversationId = entry.arguments?.getString("conversationId").orEmpty(),
                    initialTab = entry.arguments?.getString("tab").orEmpty(),
                    onNavigate = { nav.navigate(it) },
                    onSignIn = { nav.navigate(Destination.Profile.route) }
                )
            }
            Destination.Profile.let { destination ->
                composable(destination.route) {
                    ProfileScreen(authController, onNavigate = { nav.navigate(it) })
                }
            }
            composable(
                route = "trust-safety?propertyId={propertyId}&section={section}",
                arguments = listOf(
                    navArgument("propertyId") { type = NavType.StringType; defaultValue = "" },
                    navArgument("section") { type = NavType.StringType; defaultValue = "Safety" }
                )
            ) { entry ->
                TrustSafetyScreen(
                    accessToken = accessToken,
                    initialPropertyId = entry.arguments?.getString("propertyId").orEmpty(),
                    initialSection = entry.arguments?.getString("section") ?: "Safety"
                )
            }
            composable(
                route = "hub/collection/{collectionId}",
                arguments = listOf(navArgument("collectionId") { type = NavType.StringType })
            ) { entry ->
                PersonalHubScreen(
                    section = "collection",
                    collectionId = entry.arguments?.getString("collectionId"),
                    accessToken = accessToken,
                    onBack = { nav.popBackStack() },
                    onNavigate = { nav.navigate(it) },
                    onAppearanceChange = onAppearanceChange,
                    onLargerTextChange = onLargerTextChange,
                    onSignOut = { authController.signOut() }
                )
            }
            composable(
                route = "hub/{section}",
                arguments = listOf(navArgument("section") { type = NavType.StringType })
            ) { entry ->
                PersonalHubScreen(
                    section = entry.arguments?.getString("section").orEmpty(),
                    accessToken = accessToken,
                    onBack = { nav.popBackStack() },
                    onNavigate = { nav.navigate(it) },
                    onAppearanceChange = onAppearanceChange,
                    onLargerTextChange = onLargerTextChange,
                    onSignOut = { authController.signOut() }
                )
            }
            composable(Destination.Map.route) {
                MapScreen(
                    onBrowseDiscover = { nav.navigate(Destination.Discover.route) },
                    onFullscreenChange = { mapFullscreen = it },
                    onOpenProperty = { propertyId -> nav.navigate("property/$propertyId") }
                )
            }
            composable(Destination.Finance.route) {
                SmartRentScreen(
                    accessToken = accessToken,
                    onSignIn = { nav.navigate(Destination.Profile.route) },
                    onNavigate = { nav.navigate(it) },
                    onPayments = { nav.navigate("payments") }
                )
            }
            composable("payments") {
                PaymentsScreen(
                    accessToken = accessToken,
                    onBack = { nav.popBackStack() },
                    onSignIn = { nav.navigate(Destination.Profile.route) }
                )
            }
            composable(
                route = "assistant?propertyId={propertyId}&intent={intent}",
                arguments = listOf(
                    navArgument("propertyId") { type = NavType.StringType; defaultValue = "" },
                    navArgument("intent") { type = NavType.StringType; defaultValue = "general" }
                )
            ) { entry ->
                AssistantScreen(
                    accessToken = accessToken,
                    initialPropertyId = entry.arguments?.getString("propertyId").orEmpty(),
                    initialIntent = entry.arguments?.getString("intent").orEmpty(),
                    onBack = { nav.popBackStack() },
                    onSignIn = { nav.navigate(Destination.Profile.route) },
                    onNavigate = { nav.navigate(it) }
                )
            }
            composable(
                route = "services?tab={tab}",
                arguments = listOf(navArgument("tab") { type = NavType.StringType; defaultValue = "" })
            ) { entry ->
                ServicesScreen(
                    accessToken = accessToken,
                    userId = authState.user?.id,
                    onSignIn = { nav.navigate(Destination.Profile.route) },
                    onPayments = { nav.navigate("payments") },
                    initialTab = entry.arguments?.getString("tab").orEmpty()
                )
            }
            composable(Destination.Neighbourhoods.route) {
                AreasScreen(onNavigate = { nav.navigate(it) })
            }
        }
    }
    }
}
