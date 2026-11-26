package ke.co.homescout.features.admin

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.PasswordVisualTransformation
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.AdminOperationsApi
import ke.co.homescout.ui.components.HomeScoutCard
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject

private val operationSections = listOf(
    "Overview", "Users", "Listings", "Reports", "Reviews", "Trust", "Support", "Services", "Locations",
    "Categories", "Settings", "Audit", "Roles"
)

@Composable
fun OperationsScreen(
    accessToken: String?,
    onSignIn: () -> Unit,
    onNavigate: (String) -> Unit,
    initialSection: String = "Overview"
) {
    val api = remember { AdminOperationsApi() }
    val scope = rememberCoroutineScope()
    var section by rememberSaveable(initialSection) {
        mutableStateOf(initialSection.takeIf { it in operationSections } ?: "Overview")
    }
    var rows by remember { mutableStateOf(emptyList<JSONObject>()) }
    var overview by remember { mutableStateOf(JSONObject()) }
    var loading by remember { mutableStateOf(false) }
    var busy by remember { mutableStateOf(false) }
    var refresh by remember { mutableIntStateOf(0) }
    var search by rememberSaveable { mutableStateOf("") }
    var error by remember { mutableStateOf<String?>(null) }
    var dialogKind by remember { mutableStateOf<String?>(null) }
    var dialogTarget by remember { mutableStateOf(JSONObject()) }
    var dialogStatus by remember { mutableStateOf("") }
    var dialogTitle by remember { mutableStateOf("") }
    var reason by remember { mutableStateOf("") }
    var password by remember { mutableStateOf("") }
    var removeMessage by remember { mutableStateOf(false) }
    var selectedTicketId by remember { mutableStateOf<String?>(null) }
    var selectedTicket by remember { mutableStateOf<JSONObject?>(null) }
    var selectedReportId by remember { mutableStateOf<String?>(null) }
    var selectedReport by remember { mutableStateOf<JSONObject?>(null) }
    var replyDraft by remember { mutableStateOf("") }

    fun loadData(token: String) {
        scope.launch {
            loading = true
            error = null
            try {
                val loaded = withContext(Dispatchers.IO) {
                    if (section == "Overview") {
                        api.objectRows("admin/operations/overview", token) to emptyList<JSONObject>()
                    } else {
                        val list = when (section) {
                            "Users" -> api.rows(
                                "admin/operations/users?q=${ke.co.homescout.data.remote.PersonalHubApi.query(search)}",
                                token
                            )
                            "Listings" -> api.rows("admin/operations/listings", token)
                            "Reports" -> api.rows("admin/operations/reports/messages", token)
                            "Reviews" -> api.rows("admin/operations/reviews/services", token)
                            "Support" -> api.rows("admin/operations/support/tickets", token)
                            "Services" -> api.rows("admin/operations/services/providers", token)
                            "Locations" -> api.rows("admin/operations/locations", token)
                            "Categories" -> api.rows("admin/operations/categories/support", token)
                            "Settings" -> api.rows("admin/operations/settings", token)
                            "Audit" -> api.rows("admin/operations/audit", token)
                            else -> JSONArray()
                        }
                        JSONObject() to list.objects()
                    }
                }
                overview = loaded.first
                rows = loaded.second
            } catch (failure: Exception) {
                error = failure.message ?: "HomeScout operations could not load."
                rows = emptyList()
            } finally {
                loading = false
            }
        }
    }

    LaunchedEffect(accessToken, section, refresh, search) {
        val token = accessToken ?: return@LaunchedEffect
        if (section == "Trust" || section == "Roles") return@LaunchedEffect
        loadData(token)
    }

    LaunchedEffect(accessToken, selectedTicketId) {
        val token = accessToken ?: return@LaunchedEffect
        val id = selectedTicketId ?: return@LaunchedEffect
        try {
            selectedTicket = withContext(Dispatchers.IO) {
                api.objectRows("admin/operations/support/tickets/$id", token)
            }
        } catch (failure: Exception) {
            error = failure.message ?: "The support ticket could not be opened."
            selectedTicketId = null
        }
    }

    LaunchedEffect(accessToken, selectedReportId) {
        val token = accessToken ?: return@LaunchedEffect
        val id = selectedReportId ?: return@LaunchedEffect
        try {
            selectedReport = withContext(Dispatchers.IO) {
                api.objectRows("admin/operations/reports/messages/$id", token)
            }
        } catch (failure: Exception) {
            error = failure.message ?: "The reported message could not be opened."
            selectedReportId = null
        }
    }

    fun perform(action: () -> Unit) {
        val token = accessToken
        if (token == null) {
            onSignIn()
            return
        }
        scope.launch {
            busy = true
            error = null
            try {
                withContext(Dispatchers.IO) { action() }
                refresh++
                selectedTicketId?.let { id ->
                    selectedTicket = withContext(Dispatchers.IO) {
                        api.objectRows("admin/operations/support/tickets/$id", token)
                    }
                }
            } catch (failure: Exception) {
                error = failure.message ?: "HomeScout could not save this operations change."
            } finally {
                busy = false
            }
        }
    }

    fun confirmDialog() {
        val token = accessToken ?: return
        val target = dialogTarget
        val kind = dialogKind ?: return
        val status = dialogStatus
        val cleanReason = reason.trim()
        if (cleanReason.length < 10 || (kind == "user" && password.isBlank())) return
        val path: String
        val body: JSONObject
        when (kind) {
            "user" -> {
                path = "admin/operations/users/${target.optString("id")}/status"
                body = JSONObject().put("status", status).put("current_password", password)
                    .put("reason", cleanReason)
            }
            "listing" -> {
                path = "admin/operations/listings/${target.optString("id")}/moderation"
                body = JSONObject().put("status", status).put("reason", cleanReason)
            }
            "service-review" -> {
                path = "admin/operations/reviews/services/${target.optString("id")}/moderation"
                body = JSONObject().put("status", status).put("reason", cleanReason)
            }
            "provider" -> {
                path = "admin/operations/services/providers/${target.optString("provider_user_id")}/publication"
                body = JSONObject().put("is_published", status == "published").put("reason", cleanReason)
            }
            "location" -> {
                path = "admin/operations/locations/${target.optString("type")}/${target.optString("id")}"
                body = JSONObject().put("is_active", status == "active").put("reason", cleanReason)
            }
            "message-report" -> {
                path = "admin/operations/reports/messages/${target.optString("id")}/review"
                body = JSONObject().put("status", status)
                    .put("remove_message", removeMessage)
                    .put("reason", cleanReason)
            }
            else -> return
        }
        dialogKind = null
        perform({ api.send(path, "PATCH", token, body) })
    }

    Surface(color = MaterialTheme.colorScheme.background) {
        Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
            LazyColumn(
                modifier = Modifier.fillMaxWidth().widthIn(max = 820.dp),
                contentPadding = androidx.compose.foundation.layout.PaddingValues(18.dp),
                verticalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                item {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text("Platform operations", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold)
                            Text("Restricted staff tools · all figures use current platform records", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        IconButton(onClick = { refresh++ }, enabled = !loading && !busy) {
                            Icon(Icons.Filled.Refresh, contentDescription = "Refresh operations data")
                        }
                    }
                }
                item {
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        operationSections.forEach { item ->
                            FilterChip(
                                selected = section == item,
                                onClick = {
                                    if (item == "Trust") onNavigate("trust-safety")
                                    else if (item == "Roles") onNavigate("profile")
                                    else {
                                        selectedTicketId = null
                                        selectedReportId = null
                                        section = item
                                    }
                                },
                                label = { Text(item) }
                            )
                        }
                    }
                }
                if (accessToken == null) {
                    item {
                        HomeScoutCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                                Text("Staff sign-in required", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                                Text("Sign in with an authorized HomeScout staff account to open operations.")
                                OutlinedButton(onClick = onSignIn) { Text("Open Profile") }
                            }
                        }
                    }
                } else if (selectedReportId != null && selectedReport != null) {
                    item {
                        TextButton(onClick = { selectedReportId = null; selectedReport = null }) { Text("← Reports queue") }
                    }
                    item {
                        selectedReport?.let { report ->
                            MessageReportDetail(
                                report = report,
                                busy = busy,
                                onDecision = { closed, remove ->
                                    dialogKind = "message-report"
                                    dialogTarget = report
                                    dialogStatus = if (closed) "closed" else "reviewed"
                                    removeMessage = remove
                                    dialogTitle = if (remove) "Remove reported message" else "Close report"
                                    reason = ""
                                }
                            )
                        }
                    }
                } else if (selectedTicketId != null && selectedTicket != null) {
                    item {
                        TextButton(onClick = { selectedTicketId = null; selectedTicket = null }) { Text("← Support queue") }
                    }
                    item {
                        selectedTicket?.let { ticket ->
                            TicketDetail(
                                ticket = ticket,
                                reply = replyDraft,
                                onReplyChange = { replyDraft = it },
                                busy = busy,
                                onReply = {
                                    if (replyDraft.isNotBlank()) {
                                        selectedTicketId?.let { id ->
                                            val value = replyDraft.trim()
                                            perform({ api.send("admin/operations/support/tickets/$id/reply", "POST", checkNotNull(accessToken), JSONObject().put("body", value)) })
                                            replyDraft = ""
                                        }
                                    }
                                },
                                onStatus = { value ->
                                    selectedTicketId?.let { id ->
                                        perform({ api.send("admin/operations/support/tickets/$id", "PATCH", checkNotNull(accessToken), JSONObject().put("status", value)) })
                                    }
                                }
                            )
                        }
                    }
                } else {
                    error?.let { message ->
                        item { StateCard(title = "Operations unavailable", body = message) }
                    }
                    if (loading) {
                        item { Row(Modifier.fillMaxWidth().padding(22.dp), horizontalArrangement = Arrangement.Center) { CircularProgressIndicator() } }
                    }
                    if (section == "Overview") {
                        overviewMetrics(overview).forEach { (title, value) ->
                            item { MetricCard(title = title, value = value) }
                        }
                        item {
                            StateCard(
                                title = "Trust and verification",
                                body = "Verification decisions, listing reports and safety reports remain in the audited Trust & Safety review workspace."
                            )
                        }
                    } else {
                        if (section == "Users") item {
                            OutlinedTextField(
                                value = search,
                                onValueChange = { search = it },
                                label = { Text("Search by email or phone") },
                                modifier = Modifier.fillMaxWidth(),
                                singleLine = true
                            )
                        }
                        if (section == "Settings") {
                            item { StateCard("Settings access", "System settings require the Super Admin system-management permission.") }
                        }
                        items(rows, key = { it.optString("id").ifBlank { it.optString("code", it.optString("key")) } }) { row ->
                            when (section) {
                                "Users" -> UserRow(row, busy) { status ->
                                    dialogKind = "user"; dialogTarget = row; dialogStatus = status
                                    dialogTitle = if (status == "suspended") "Restrict account" else "Restore account"
                                    reason = ""; password = ""
                                }
                                "Listings" -> ListingRow(row, busy) { status ->
                                    dialogKind = "listing"; dialogTarget = row; dialogStatus = status
                                    dialogTitle = if (status == "under_review") "Place listing under review" else "Change listing status"
                                    reason = ""
                                }
                                "Reports" -> ReportRow(row) { selectedReportId = row.optString("id") }
                                "Reviews" -> ServiceReviewRow(row, busy) { status ->
                                    dialogKind = "service-review"; dialogTarget = row; dialogStatus = status
                                    dialogTitle = when (status) {
                                        "clear" -> "Restore service review"
                                        "removed" -> "Remove service review"
                                        else -> "Hold service review for review"
                                    }
                                    reason = ""
                                }
                                "Support" -> SupportRow(row) { selectedTicketId = row.optString("id") }
                                "Services" -> ProviderRow(row, busy) { published ->
                                    dialogKind = "provider"; dialogTarget = row
                                    dialogStatus = if (published) "published" else "paused"
                                    dialogTitle = if (published) "Publish provider profile" else "Pause provider profile"
                                    reason = ""
                                }
                                "Locations" -> LocationRow(row, busy) { active ->
                                    dialogKind = "location"; dialogTarget = row
                                    dialogStatus = if (active) "active" else "inactive"
                                    dialogTitle = if (active) "Activate location" else "Deactivate location"
                                    reason = ""
                                }
                                "Categories" -> ToggleRow(
                                    title = row.optString("code").replace('_', ' ').replaceFirstChar(Char::uppercase),
                                    detail = "Support ticket category · ${if (row.optBoolean("is_active")) "available" else "disabled"}",
                                    checked = row.optBoolean("is_active"),
                                    enabled = !busy,
                                    onChange = { active ->
                                        perform({ api.send("admin/operations/categories/support/${row.optString("code")}", "PATCH", checkNotNull(accessToken), JSONObject().put("is_active", active)) })
                                    }
                                )
                                "Settings" -> ToggleRow(
                                    title = row.optString("key").replace('.', ' ').replace('_', ' ').replaceFirstChar(Char::uppercase),
                                    detail = row.optString("description"),
                                    checked = row.optBoolean("value"),
                                    enabled = !busy,
                                    onChange = { active ->
                                        perform({ api.send("admin/operations/settings/${row.optString("key")}", "PUT", checkNotNull(accessToken), JSONObject().put("value", active)) })
                                    }
                                )
                                "Audit" -> AuditRow(row)
                            }
                        }
                        if (!loading && rows.isEmpty() && error == null) {
                            item { StateCard("No records to show", "No matching ${section.lowercase()} records were returned for your current staff access.") }
                        }
                    }
                }
            }
        }
    }

    if (dialogKind != null) {
        AlertDialog(
            onDismissRequest = { dialogKind = null },
            title = { Text(dialogTitle) },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Enter a clear reason. This action is recorded in the administrative audit history.")
                    OutlinedTextField(
                        value = reason,
                        onValueChange = { reason = it.take(500) },
                        label = { Text("Reason (at least 10 characters)") },
                        minLines = 2,
                        modifier = Modifier.fillMaxWidth()
                    )
                    if (dialogKind == "user") {
                        OutlinedTextField(
                            value = password,
                            onValueChange = { password = it.take(128) },
                            label = { Text("Confirm your current password") },
                            visualTransformation = PasswordVisualTransformation(),
                            singleLine = true,
                            modifier = Modifier.fillMaxWidth()
                        )
                    }
                    if (dialogKind == "message-report") {
                        Text(
                            if (removeMessage) "The reported message will be hidden from its participants." else "The reported message will remain visible.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            },
            confirmButton = {
                TextButton(
                    onClick = { confirmDialog() },
                    enabled = reason.trim().length >= 10 && (dialogKind != "user" || password.isNotBlank())
                ) { Text("Confirm") }
            },
            dismissButton = { TextButton(onClick = { dialogKind = null }) { Text("Cancel") } }
        )
    }
}

private fun overviewMetrics(data: JSONObject): List<Pair<String, String>> = listOf(
    "Accounts" to "${data.optInt("users_total")} total · ${data.optInt("users_active")} active",
    "Listings" to "${data.optInt("listings_total")} non-demo · ${data.optInt("listings_review")} under review",
    "Trust review" to "${data.optInt("verifications_pending")} verifications · ${data.optInt("listing_reports_open")} listing reports",
    "Safety queue" to "${data.optInt("safety_reports_open")} safety · ${data.optInt("message_reports_open")} message reports",
    "Support" to "${data.optInt("support_open")} open · ${data.optInt("support_waiting")} waiting",
    "Services & reviews" to "${data.optInt("providers_published")} providers · ${data.optInt("services_active")} services · ${data.optInt("service_reviews_pending")} reviews held",
    "Locations" to "${data.optInt("counties_active")} counties · ${data.optInt("towns_active")} towns · ${data.optInt("neighbourhoods_active")} neighbourhoods"
)

@Composable
private fun MetricCard(title: String, value: String) = StateCard(title, value)

@Composable
private fun StateCard(title: String, body: String) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(body, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun UserRow(row: JSONObject, busy: Boolean, onAction: (String) -> Unit) {
    OperationRow(
        title = row.optString("email").ifBlank { "Account ${row.optString("id").take(8)}" },
        detail = "${row.optString("status")} · ${row.optJSONArray("roles").strings().joinToString().ifBlank { "No assigned role" }}" +
            row.optString("requested_role_code").takeIf { it.isNotBlank() && it != "null" }?.let { " · requested $it" }.orEmpty(),
        action = if (row.optString("status") == "suspended") "Restore" else "Restrict",
        enabled = !busy && row.optString("status") != "closed",
        onAction = { onAction(if (row.optString("status") == "suspended") "active" else "suspended") }
    )
}

@Composable
private fun ListingRow(row: JSONObject, busy: Boolean, onAction: (String) -> Unit) {
    val held = row.optString("moderation_status") in setOf("under_review", "removed")
    OperationRow(
        title = row.optString("title"),
        detail = "KSh ${row.optString("rent_kes")} · ${row.optString("town")} · ${row.optString("moderation_status")} · ${row.optInt("reported_count")} reports",
        action = if (held) "Restore" else "Review",
        enabled = !busy,
        onAction = { onAction(if (held) "clear" else "under_review") }
    )
}

@Composable
private fun SupportRow(row: JSONObject, onOpen: () -> Unit) {
    OperationRow(
        title = row.optString("subject"),
        detail = "${row.optString("category")} · ${row.optString("status")} · ${row.optString("priority")} · ${row.optString("owner_email")}",
        action = "Open",
        enabled = true,
        onAction = onOpen
    )
}

@Composable
private fun ReportRow(row: JSONObject, onOpen: () -> Unit) {
    OperationRow(
        title = "${row.optString("category").replace('_', ' ')} report",
        detail = "Reported message · received ${row.optString("created_at")} · message ${row.optString("message_id").take(8)}",
        action = "Review",
        enabled = true,
        onAction = onOpen
    )
}

@Composable
private fun ServiceReviewRow(row: JSONObject, busy: Boolean, onModerate: (String) -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(
            Modifier.padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(8.dp)
        ) {
            Text(row.optString("offering_title", "Service review"), fontWeight = FontWeight.SemiBold)
            Text(
                "${row.optInt("rating")}/5 · ${row.optString("moderation_status").replace('_', ' ')}",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            row.optString("review_text").takeIf(String::isNotBlank)?.let { reviewText ->
                Text(reviewText, style = MaterialTheme.typography.bodyMedium)
            }
            Row(
                Modifier.horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedButton(onClick = { onModerate("clear") }, enabled = !busy) {
                    Text("Keep visible")
                }
                OutlinedButton(onClick = { onModerate("under_review") }, enabled = !busy) {
                    Text("Hold")
                }
                OutlinedButton(onClick = { onModerate("removed") }, enabled = !busy) {
                    Text("Remove")
                }
            }
        }
    }
}

@Composable
private fun MessageReportDetail(
    report: JSONObject,
    busy: Boolean,
    onDecision: (closed: Boolean, remove: Boolean) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StateCard(
            title = "Reported message · ${report.optString("category").replace('_', ' ')}",
            body = "${report.optString("details").ifBlank { "No additional report details were supplied." }}\n\n${report.optString("message_body")}"
        )
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { onDecision(true, false) }, enabled = !busy) {
                Text("Close report")
            }
            OutlinedButton(onClick = { onDecision(false, true) }, enabled = !busy) {
                Text("Remove message")
            }
        }
    }
}

@Composable
private fun ProviderRow(row: JSONObject, busy: Boolean, onAction: (Boolean) -> Unit) {
    OperationRow(
        title = row.optString("public_name"),
        detail = "${row.optInt("active_offerings")} active services · ${if (row.optBoolean("is_published")) "published" else "not published"}",
        action = if (row.optBoolean("is_published")) "Pause" else "Publish",
        enabled = !busy,
        onAction = { onAction(!row.optBoolean("is_published")) }
    )
}

@Composable
private fun LocationRow(row: JSONObject, busy: Boolean, onAction: (Boolean) -> Unit) {
    OperationRow(
        title = row.optString("name"),
        detail = "${row.optString("type")} · ${if (row.optBoolean("is_active")) "active" else "inactive"}",
        action = if (row.optBoolean("is_active")) "Disable" else "Enable",
        enabled = !busy,
        onAction = { onAction(!row.optBoolean("is_active")) }
    )
}

@Composable
private fun ToggleRow(title: String, detail: String, checked: Boolean, enabled: Boolean, onChange: (Boolean) -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Row(Modifier.fillMaxWidth().padding(start = 16.dp, end = 8.dp, top = 10.dp, bottom = 10.dp), verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Switch(checked = checked, onCheckedChange = onChange, enabled = enabled)
        }
    }
}

@Composable
private fun AuditRow(row: JSONObject) {
    OperationRow(
        title = row.optString("event_type").replace('.', ' ').replace('_', ' '),
        detail = "${row.optString("subject_type")} ${row.optString("subject_id")} · ${row.optString("occurred_at")}",
        action = null,
        enabled = false,
        onAction = {}
    )
}

@Composable
private fun TicketDetail(
    ticket: JSONObject,
    reply: String,
    onReplyChange: (String) -> Unit,
    busy: Boolean,
    onReply: () -> Unit,
    onStatus: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        StateCard(
            title = ticket.optString("subject"),
            body = "${ticket.optString("owner_email")} · ${ticket.optString("category")} · ${ticket.optString("status")} · ${ticket.optString("priority")}"
        )
        ticket.optJSONArray("messages").objects().forEach { message ->
            StateCard(
                title = if (message.optString("sender_user_id") == ticket.optString("owner_user_id")) "Customer" else "Staff",
                body = message.optString("body")
            )
        }
        ticket.optJSONArray("actions").objects().forEach { event ->
            Text("${event.optString("action")} · ${event.optString("note")}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedButton(onClick = { onStatus("waiting") }, enabled = !busy) { Text("Mark waiting") }
            OutlinedButton(onClick = { onStatus("closed") }, enabled = !busy) { Text("Close") }
            OutlinedButton(onClick = { onStatus("open") }, enabled = !busy) { Text("Reopen") }
        }
        OutlinedTextField(
            value = reply,
            onValueChange = onReplyChange,
            label = { Text("Reply to customer") },
            modifier = Modifier.fillMaxWidth(),
            minLines = 3,
            maxLines = 7
        )
        OutlinedButton(onClick = onReply, enabled = !busy && reply.isNotBlank(), modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
            Text(if (busy) "Sending…" else "Send reply")
        }
    }
}

@Composable
private fun OperationRow(title: String, detail: String, action: String?, enabled: Boolean, onAction: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title.ifBlank { "HomeScout record" }, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (action != null) OutlinedButton(onClick = onAction, enabled = enabled, modifier = Modifier.heightIn(min = 44.dp)) { Text(action) }
        }
    }
}

private fun JSONArray?.objects(): List<JSONObject> =
    this?.let { array -> (0 until array.length()).mapNotNull(array::optJSONObject) }.orEmpty()

private fun JSONArray?.strings(): List<String> =
    this?.let { array -> (0 until array.length()).map { array.optString(it) } }.orEmpty()
