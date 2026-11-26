package ke.co.homescout.features.profile

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.Email
import androidx.compose.material.icons.filled.PersonOutline
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material.icons.filled.Visibility
import androidx.compose.material.icons.filled.VisibilityOff
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.ExperimentalMaterial3Api
import androidx.compose.material3.ExposedDropdownMenuBox
import androidx.compose.material3.ExposedDropdownMenuDefaults
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.MenuAnchorType
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.auth.AuthController
import ke.co.homescout.data.remote.AdminUser
import ke.co.homescout.data.remote.DeviceSession
import ke.co.homescout.data.remote.RoleOption
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.theme.HomeScoutColors

private enum class ProfileMode { SignIn, Register, Verify, Reset }

@Composable
fun ProfileScreen(controller: AuthController, onNavigate: (String) -> Unit = {}, initialRegister: Boolean = false, authOnly: Boolean = false) {
    val state = controller.state
    val user = state.user
    var mode by rememberSaveable { mutableStateOf(if (initialRegister) ProfileMode.Register else ProfileMode.SignIn) }
    var signOutDialog by remember { mutableStateOf(false) }
    var sessionToRevoke by remember { mutableStateOf<DeviceSession?>(null) }
    var verificationToken by rememberSaveable { mutableStateOf("") }
    var resetToken by rememberSaveable { mutableStateOf("") }

    LaunchedEffect(state.developmentToken) {
        state.developmentToken?.let { token ->
            if (mode == ProfileMode.Register) {
                verificationToken = token
                mode = ProfileMode.Verify
            } else if (mode == ProfileMode.Reset) {
                resetToken = token
            }
        }
    }
    LaunchedEffect(state.message) {
        if (mode == ProfileMode.Verify && state.message?.startsWith("Email verified") == true) {
            mode = ProfileMode.SignIn
        }
        if (mode == ProfileMode.Reset && state.message?.startsWith("Password changed") == true) {
            mode = ProfileMode.SignIn
        }
    }

    Column(
        modifier = Modifier
            .fillMaxWidth()
            .verticalScroll(rememberScrollState())
            .padding(horizontal = 20.dp, vertical = 24.dp),
        verticalArrangement = Arrangement.spacedBy(18.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        if (user == null) {
            Column(
                Modifier.fillMaxWidth().widthIn(max = 560.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("Your HomeScout", style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.SemiBold)
                Text(
                    "A secure place for your home search and account settings.",
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        } else {
            Text(
                "My profile",
                Modifier.fillMaxWidth().widthIn(max = 560.dp),
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }

        if (state.error != null) {
            HomeScoutCard(Modifier.fillMaxWidth().widthIn(max = 560.dp)) {
                Text(
                    state.error,
                    Modifier.padding(16.dp),
                    color = MaterialTheme.colorScheme.error,
                    style = MaterialTheme.typography.bodyMedium
                )
            }
        }
        if (state.message != null) {
            HomeScoutCard(Modifier.fillMaxWidth().widthIn(max = 560.dp)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(state.message, style = MaterialTheme.typography.bodyMedium)
                    state.developmentToken?.let {
                        Text(
                            "Local development code",
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.primary
                        )
                        Text(it, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }

        if (user == null) {
            AccountAccessCard(
                mode = mode,
                onModeChange = { mode = it },
                loading = state.isLoading,
                verificationToken = verificationToken,
                resetToken = resetToken,
                onVerificationTokenChange = { verificationToken = it },
                onResetTokenChange = { resetToken = it },
                onSignIn = controller::signIn,
                onRegister = controller::register,
                onVerify = controller::verifyEmail,
                onResendVerification = controller::resendVerification,
                onRequestReset = controller::requestPasswordReset,
                onConfirmReset = controller::confirmPasswordReset
            )
            if (!authOnly) OutlinedButton(
                onClick = { onNavigate("trust-safety") },
                modifier = Modifier.fillMaxWidth().widthIn(max = 560.dp).heightIn(min = 48.dp)
            ) {
                Icon(Icons.Filled.Security, contentDescription = null)
                Spacer(Modifier.width(8.dp))
                Text("Rental safety and trust")
            }
            if (!authOnly && !ke.co.homescout.data.remote.ApiConfiguration.isConfigured) {
                Text(
                    "Connect an API address in the build configuration to use account features.",
                    Modifier.fillMaxWidth().widthIn(max = 560.dp),
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    style = MaterialTheme.typography.bodySmall
                )
            }
        } else {
            AccountSummaryCard(
                name = listOf(user.givenName, user.familyName).filter(String::isNotBlank).joinToString(" ")
                    .ifBlank { user.email },
                email = user.email,
                status = user.status,
                verified = user.emailVerified,
                roles = user.roles,
                requestedRole = user.requestedRole,
                loading = state.isLoading,
                onRefreshSessions = controller::loadSessions,
                onSignOut = { signOutDialog = true },
                onEditProfile = { onNavigate("hub/profile") }
            )
            SessionsCard(
                sessions = state.sessions,
                loading = state.isLoading,
                onRefresh = controller::loadSessions,
                onRevoke = { sessionToRevoke = it }
            )
            if (user.permissions.any { it == "roles:assign:operational" || it == "roles:assign:administrative" }) {
                AdministrationCard(
                    controller = controller,
                    roles = user.roles,
                    stateUsers = state.adminUsers,
                    roleOptions = state.roleOptions,
                    loading = state.isLoading
                )
            }
        }
    }

    if (signOutDialog) {
        AlertDialog(
            onDismissRequest = { signOutDialog = false },
            title = { Text("Sign out of HomeScout?") },
            text = { Text("You can sign in again whenever you need your account.") },
            confirmButton = {
                TextButton(onClick = { signOutDialog = false; controller.signOut() }) { Text("Sign out") }
            },
            dismissButton = { TextButton(onClick = { signOutDialog = false }) { Text("Cancel") } }
        )
    }
    sessionToRevoke?.let { session ->
        AlertDialog(
            onDismissRequest = { sessionToRevoke = null },
            title = { Text(if (session.current) "Sign out this device?" else "End this session?") },
            text = { Text("That session will no longer be able to access this account.") },
            confirmButton = {
                TextButton(onClick = { sessionToRevoke = null; controller.revokeSession(session) }) {
                    Text("End session")
                }
            },
            dismissButton = { TextButton(onClick = { sessionToRevoke = null }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun AccountAccessCard(
    mode: ProfileMode,
    onModeChange: (ProfileMode) -> Unit,
    loading: Boolean,
    verificationToken: String,
    resetToken: String,
    onVerificationTokenChange: (String) -> Unit,
    onResetTokenChange: (String) -> Unit,
    onSignIn: (String, String) -> Unit,
    onRegister: (String, String, String, String, String) -> Unit,
    onVerify: (String) -> Unit,
    onResendVerification: (String) -> Unit,
    onRequestReset: (String) -> Unit,
    onConfirmReset: (String, String) -> Unit
) {
    var email by rememberSaveable { mutableStateOf("") }
    var password by rememberSaveable { mutableStateOf("") }
    var newPassword by rememberSaveable { mutableStateOf("") }
    var givenName by rememberSaveable { mutableStateOf("") }
    var familyName by rememberSaveable { mutableStateOf("") }
    var requestedRole by rememberSaveable { mutableStateOf("tenant") }

    HomeScoutCard(Modifier.fillMaxWidth().widthIn(max = 560.dp)) {
        Column(
            Modifier.fillMaxWidth().padding(20.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            if (mode == ProfileMode.SignIn || mode == ProfileMode.Register) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    FilterChip(
                        selected = mode == ProfileMode.SignIn,
                        onClick = { onModeChange(ProfileMode.SignIn) },
                        label = { Text("Sign in") }
                    )
                    FilterChip(
                        selected = mode == ProfileMode.Register,
                        onClick = { onModeChange(ProfileMode.Register) },
                        label = { Text("Create account") }
                    )
                }
            }

            when (mode) {
                ProfileMode.SignIn -> {
                    Text("Welcome back", style = MaterialTheme.typography.titleLarge)
                    Text("Sign in to manage your HomeScout account.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    LabeledInput("Email address", email, { email = it }, enabled = !loading)
                    LabeledInput("Password", password, { password = it }, password = true, enabled = !loading)
                    Button(
                        onClick = { onSignIn(email, password) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                        enabled = !loading && email.isNotBlank() && password.isNotEmpty()
                    ) { LoadingOrText(loading, "Sign in") }
                    TextButton(onClick = { onModeChange(ProfileMode.Reset) }, modifier = Modifier.align(Alignment.End)) {
                        Text("Forgot password?")
                    }
                    TextButton(onClick = { onModeChange(ProfileMode.Verify) }, modifier = Modifier.align(Alignment.End)) {
                        Text("I have an email verification code")
                    }
                }
                ProfileMode.Register -> {
                    Text("Create your account", style = MaterialTheme.typography.titleLarge)
                    Text("Your account begins with tenant access. Other roles require approval.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    LabeledInput("First name", givenName, { givenName = it }, enabled = !loading)
                    LabeledInput("Last name (optional)", familyName, { familyName = it }, enabled = !loading)
                    LabeledInput("Email address", email, { email = it }, enabled = !loading)
                    LabeledInput("Password · at least 12 characters", password, { password = it }, password = true, enabled = !loading)
                    SimpleDropdown(
                        label = "I’m joining as",
                        options = listOf("tenant", "landlord", "real_estate_agent", "property_manager", "service_provider"),
                        selected = requestedRole,
                        onSelect = { requestedRole = it },
                        enabled = !loading
                    )
                    Button(
                        onClick = { onRegister(email, password, givenName, familyName, requestedRole) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                        enabled = !loading && givenName.isNotBlank() && email.isNotBlank() && password.length >= 12
                    ) { LoadingOrText(loading, "Create account") }
                    Text("We’ll send a one-time email verification code.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                ProfileMode.Verify -> {
                    Text("Verify your email", style = MaterialTheme.typography.titleLarge)
                    Text("Enter the one-time code sent to your email address.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    LabeledInput("Verification code", verificationToken, onVerificationTokenChange, enabled = !loading)
                    Button(
                        onClick = { onVerify(verificationToken) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                        enabled = !loading && verificationToken.isNotBlank()
                    ) { LoadingOrText(loading, "Verify email") }
                    TextButton(
                        onClick = { onResendVerification(email) },
                        enabled = !loading && email.isNotBlank(),
                        modifier = Modifier.align(Alignment.End)
                    ) { Text("Resend code") }
                    TextButton(onClick = { onModeChange(ProfileMode.SignIn) }, modifier = Modifier.align(Alignment.End)) {
                        Text("Back to sign in")
                    }
                }
                ProfileMode.Reset -> {
                    Text("Reset your password", style = MaterialTheme.typography.titleLarge)
                    Text("We’ll send a one-time reset code if the account is eligible.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    LabeledInput("Email address", email, { email = it }, enabled = !loading)
                    OutlinedButton(
                        onClick = { onRequestReset(email) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                        enabled = !loading && email.isNotBlank()
                    ) { Text("Send reset code") }
                    LabeledInput("Reset code", resetToken, onResetTokenChange, enabled = !loading)
                    LabeledInput("New password · at least 12 characters", newPassword, { newPassword = it }, password = true, enabled = !loading)
                    Button(
                        onClick = { onConfirmReset(resetToken, newPassword) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                        enabled = !loading && resetToken.isNotBlank() && newPassword.length >= 12
                    ) { LoadingOrText(loading, "Change password") }
                    TextButton(onClick = { onModeChange(ProfileMode.SignIn) }, modifier = Modifier.align(Alignment.End)) {
                        Text("Back to sign in")
                    }
                }
            }
        }
    }
}

@Composable
private fun AccountSummaryCard(
    name: String,
    email: String,
    status: String,
    verified: Boolean,
    roles: List<String>,
    requestedRole: String?,
    loading: Boolean,
    onRefreshSessions: () -> Unit,
    onSignOut: () -> Unit,
    onEditProfile: () -> Unit
) {
    val initials = name.trim().split(Regex("\\s+")).filter(String::isNotBlank)
        .take(2).mapNotNull { it.firstOrNull()?.uppercaseChar() }.joinToString("")
        .ifBlank { email.firstOrNull()?.uppercaseChar()?.toString() ?: "H" }

    Column(
        modifier = Modifier.fillMaxWidth().widthIn(max = 560.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp)
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(28.dp),
            color = HomeScoutColors.navy
        ) {
            Column(
                modifier = Modifier.fillMaxWidth().padding(horizontal = 22.dp, vertical = 24.dp),
                horizontalAlignment = Alignment.CenterHorizontally,
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Surface(
                    modifier = Modifier.size(86.dp),
                    shape = CircleShape,
                    color = Color(0xFFF4E9DE)
                ) {
                    Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                        Text(
                            initials,
                            color = HomeScoutColors.navy,
                            style = MaterialTheme.typography.headlineMedium,
                            fontWeight = FontWeight.Bold
                        )
                    }
                }
                Text(
                    name.ifBlank { "HomeScout member" },
                    style = MaterialTheme.typography.headlineSmall,
                    fontWeight = FontWeight.SemiBold,
                    color = Color.White
                )
                Text(
                    email,
                    style = MaterialTheme.typography.bodyMedium,
                    color = Color.White.copy(alpha = .78f)
                )
                Surface(
                    shape = CircleShape,
                    color = Color.White.copy(alpha = .12f)
                ) {
                    Row(
                        modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
                        verticalAlignment = Alignment.CenterVertically,
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        Icon(
                            if (verified) Icons.Filled.VerifiedUser else Icons.Filled.Security,
                            contentDescription = null,
                            tint = if (verified) HomeScoutColors.darkGreenText else HomeScoutColors.amber,
                            modifier = Modifier.size(16.dp)
                        )
                        Text(
                            if (verified) "Email verified" else "Email verification needed",
                            style = MaterialTheme.typography.labelMedium,
                            color = Color.White
                        )
                    }
                }
            }
        }

        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Text("Account details", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                ProfileDetailRow(Icons.Filled.Email, "Email address", email)
                HorizontalDivider()
                ProfileDetailRow(Icons.Filled.Security, "Account status", status.replaceFirstChar(Char::uppercase))
                HorizontalDivider()
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Access roles", style = MaterialTheme.typography.labelLarge)
                    if (roles.isEmpty()) {
                        Text("No role assigned", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else {
                        Row(
                            modifier = Modifier.horizontalScroll(rememberScrollState()),
                            horizontalArrangement = Arrangement.spacedBy(8.dp)
                        ) {
                            roles.forEach { role ->
                                ProfileInfoChip(role.replace('_', ' '))
                            }
                        }
                    }
                }
                if (requestedRole != null && requestedRole !in roles) {
                    Text(
                        "Requested role: ${requestedRole.replace('_', ' ')} · awaiting assignment",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                HorizontalDivider()
                OutlinedButton(onClick = onEditProfile, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Icon(Icons.Filled.PersonOutline, contentDescription = null)
                    Spacer(Modifier.width(8.dp))
                    Text("Edit profile details")
                }
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    OutlinedButton(onClick = onRefreshSessions, modifier = Modifier.weight(1f), enabled = !loading) {
                        Icon(Icons.Filled.Refresh, contentDescription = null)
                        Spacer(Modifier.width(6.dp))
                        Text("Devices")
                    }
                    Button(onClick = onSignOut, modifier = Modifier.weight(1f), enabled = !loading) { Text("Sign out") }
                }
            }
        }
    }
}

@Composable
private fun ProfileDetailRow(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String, value: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
        Surface(
            modifier = Modifier.size(40.dp),
            shape = RoundedCornerShape(13.dp),
            color = MaterialTheme.colorScheme.primaryContainer
        ) {
            Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.Center) {
                Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer)
            }
        }
        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
            Text(label, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
        }
    }
}

@Composable
private fun ProfileInfoChip(label: String) {
    Surface(shape = CircleShape, color = MaterialTheme.colorScheme.primaryContainer) {
        Text(
            label.replaceFirstChar(Char::uppercase),
            modifier = Modifier.padding(horizontal = 12.dp, vertical = 7.dp),
            style = MaterialTheme.typography.labelMedium,
            color = MaterialTheme.colorScheme.onPrimaryContainer
        )
    }
}

@Composable
private fun SessionsCard(
    sessions: List<DeviceSession>,
    loading: Boolean,
    onRefresh: () -> Unit,
    onRevoke: (DeviceSession) -> Unit
) {
    HomeScoutCard(Modifier.fillMaxWidth().widthIn(max = 560.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Signed-in devices", style = MaterialTheme.typography.titleMedium)
                    Text("Review or end a session.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = onRefresh, enabled = !loading) { Text("Refresh") }
            }
            when {
                loading && sessions.isEmpty() -> CircularProgressIndicator(Modifier.size(24.dp))
                sessions.isEmpty() -> Text("Select Sessions to load your devices.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                else -> sessions.forEach { session ->
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Column(Modifier.weight(1f)) {
                            Text(if (session.current) "This device" else "Other device", style = MaterialTheme.typography.bodyMedium)
                            Text(session.createdAt, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        TextButton(onClick = { onRevoke(session) }) { Text("Sign out") }
                    }
                }
            }
        }
    }
}

@Composable
private fun AdministrationCard(
    controller: AuthController,
    roles: List<String>,
    stateUsers: List<AdminUser>,
    roleOptions: List<RoleOption>,
    loading: Boolean
) {
    var expanded by rememberSaveable { mutableStateOf(false) }
    var query by rememberSaveable { mutableStateOf("") }
    var selectedUser by remember { mutableStateOf<AdminUser?>(null) }
    var roleCode by rememberSaveable { mutableStateOf("tenant") }
    var scopeType by rememberSaveable { mutableStateOf("global") }
    var scopeId by rememberSaveable { mutableStateOf("*") }
    var currentPassword by rememberSaveable { mutableStateOf("") }

    HomeScoutCard(Modifier.fillMaxWidth().widthIn(max = 560.dp)) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.AdminPanelSettings, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.width(10.dp))
                Column(Modifier.weight(1f)) {
                    Text("Administration", style = MaterialTheme.typography.titleMedium)
                    Text("Restricted tools · changes are audited", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = {
                    expanded = !expanded
                    if (expanded && "super_admin" in roles) controller.loadRoleOptions()
                }) { Text(if (expanded) "Hide" else "Open") }
            }
            if (expanded) {
                LabeledInput("Search user email", query, { query = it }, enabled = !loading)
                OutlinedButton(
                    onClick = { controller.searchAdminUsers(query) },
                    modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp),
                    enabled = !loading && query.trim().length >= 2
                ) { Text("Search users") }
                if (stateUsers.isNotEmpty()) {
                    stateUsers.forEach { user ->
                        UserResult(user, selected = selectedUser?.id == user.id, onSelect = { selectedUser = user })
                    }
                }
                if (selectedUser != null) {
                    HorizontalDivider()
                    Text("Assign role to ${selectedUser!!.email}", style = MaterialTheme.typography.titleSmall)
                    val choices = if (roleOptions.isNotEmpty()) roleOptions
                    else listOf("tenant", "roommate", "landlord", "real_estate_agent", "property_manager", "service_provider")
                        .map { RoleOption(it, it.replace('_', ' ').replaceFirstChar(Char::uppercase)) }
                    SimpleDropdown(
                        label = "Role",
                        options = choices.map(RoleOption::code),
                        selected = roleCode.takeIf { code -> choices.any { it.code == code } } ?: choices.first().code,
                        onSelect = { selected ->
                            roleCode = selected
                            scopeType = when (selected) {
                                "tenant" -> "global"
                                "roommate" -> "group"
                                "landlord", "real_estate_agent" -> "property"
                                "property_manager" -> "portfolio"
                                "service_provider" -> "booking"
                                "moderator" -> "moderation"
                                else -> "administrative_workflow"
                            }
                            scopeId = if (scopeType == "global") "*" else ""
                        },
                        enabled = !loading
                    )
                    Text(
                        "Scope: ${scopeType.replace('_', ' ')}",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    if (scopeType != "global") {
                        LabeledInput("Scope identifier", scopeId, { scopeId = it }, enabled = !loading)
                    }
                    LabeledInput("Confirm your password", currentPassword, { currentPassword = it }, password = true, enabled = !loading)
                    Button(
                        onClick = {
                            controller.assignRole(
                                selectedUser!!.id,
                                roleCode,
                                scopeType,
                                if (scopeType == "global") "*" else scopeId,
                                currentPassword
                            )
                            currentPassword = ""
                        },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp),
                        enabled = !loading && currentPassword.isNotEmpty() &&
                            (scopeType == "global" || scopeId.isNotBlank())
                    ) { LoadingOrText(loading, "Confirm role change") }
                }
            }
        }
    }
}

@Composable
private fun UserResult(user: AdminUser, selected: Boolean, onSelect: () -> Unit) {
    Surface(
        onClick = onSelect,
        shape = MaterialTheme.shapes.small,
        color = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surfaceVariant,
        modifier = Modifier.fillMaxWidth()
    ) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(user.email, style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
            Text(
                "${user.status} · ${user.roles.joinToString().ifBlank { "No role" }}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            if (user.requestedRole != null) {
                Text("Requested: ${user.requestedRole.replace('_', ' ')}", style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun LabeledInput(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    password: Boolean = false,
    enabled: Boolean = true
) {
    var passwordVisible by rememberSaveable(label) { mutableStateOf(false) }
    OutlinedTextField(
        value = value,
        onValueChange = onValueChange,
        label = { Text(label) },
        modifier = Modifier.fillMaxWidth(),
        singleLine = true,
        enabled = enabled,
        visualTransformation = if (password && !passwordVisible) PasswordVisualTransformation() else androidx.compose.ui.text.input.VisualTransformation.None,
        trailingIcon = if (password) {
            {
                IconButton(onClick = { passwordVisible = !passwordVisible }, enabled = enabled) {
                    Icon(
                        imageVector = if (passwordVisible) Icons.Filled.VisibilityOff else Icons.Filled.Visibility,
                        contentDescription = if (passwordVisible) "Hide password" else "Show password"
                    )
                }
            }
        } else null,
        shape = MaterialTheme.shapes.small
    )
}

@OptIn(ExperimentalMaterial3Api::class)
@Composable
private fun SimpleDropdown(
    label: String,
    options: List<String>,
    selected: String,
    onSelect: (String) -> Unit,
    enabled: Boolean
) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = !expanded && enabled }) {
        OutlinedTextField(
            value = selected.replace('_', ' ').replaceFirstChar(Char::uppercase),
            onValueChange = {},
            readOnly = true,
            label = { Text(label) },
            trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) },
            modifier = Modifier.menuAnchor(MenuAnchorType.PrimaryNotEditable, enabled).fillMaxWidth(),
            enabled = enabled,
            shape = MaterialTheme.shapes.small
        )
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option ->
                DropdownMenuItem(
                    text = { Text(option.replace('_', ' ').replaceFirstChar(Char::uppercase)) },
                    onClick = { onSelect(option); expanded = false }
                )
            }
        }
    }
}

@Composable
private fun LoadingOrText(loading: Boolean, text: String) {
    if (loading) {
        CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
    } else {
        Text(text)
    }
}
