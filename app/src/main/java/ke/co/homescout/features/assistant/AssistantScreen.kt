package ke.co.homescout.features.assistant

import androidx.compose.foundation.background
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardActions
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.Send
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.BookmarkBorder
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.ImeAction
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.AssistantApi
import ke.co.homescout.ui.components.EmptyState
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.theme.HomeScoutColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

private data class ChatLine(val role: String, val text: String)

@Composable
fun AssistantScreen(
    accessToken: String?,
    initialPropertyId: String,
    initialIntent: String,
    onBack: () -> Unit,
    onSignIn: () -> Unit,
    onNavigate: (String) -> Unit
) {
    val api = remember { AssistantApi() }
    val scope = rememberCoroutineScope()
    val lines = remember { mutableStateListOf<ChatLine>() }
    var configuration by remember { mutableStateOf(JSONObject()) }
    var privacy by remember { mutableStateOf<JSONObject?>(null) }
    var history by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var groups by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var contextProperties by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var selectedGroup by remember { mutableStateOf<JSONObject?>(null) }
    var conversationId by remember { mutableStateOf<String?>(null) }
    var draft by remember { mutableStateOf("") }
    var loading by remember { mutableStateOf(true) }
    var sending by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var includeFinance by remember { mutableStateOf(false) }
    var includeSaved by remember { mutableStateOf(false) }
    var includeSchedule by remember { mutableStateOf(false) }
    var includeWork by remember { mutableStateOf(false) }
    var showConsent by remember { mutableStateOf(false) }
    var showPrivacy by remember { mutableStateOf(false) }
    var showHistory by remember { mutableStateOf(false) }
    var showGroups by remember { mutableStateOf(false) }
    var renameTarget by remember { mutableStateOf<JSONObject?>(null) }
    var renameValue by remember { mutableStateOf("") }
    var deleteTarget by remember { mutableStateOf<JSONObject?>(null) }
    var consentBusy by remember { mutableStateOf(false) }
    val available = configuration.optBoolean("available")
    val consented = privacy?.optBoolean("provider_processing_allowed") == true

    LaunchedEffect(accessToken) {
        loading = true
        error = null
        try {
            val data = withContext(Dispatchers.IO) {
                val config = if (ApiConfiguration.isConfigured) {
                    api.configuration()
                } else JSONObject()
                    .put("available", false)
                    .put("disabled_message", "Connect the HomeScout API to use this assistant.")
                val privateState = if (ApiConfiguration.isConfigured && accessToken != null) {
                    api.privacy(accessToken)
                } else null
                val conversations = if (
                    accessToken != null &&
                    privateState?.optBoolean("at_rest_encryption_configured") == true
                ) api.conversations(accessToken) else emptyList()
                val memberGroups = if (ApiConfiguration.isConfigured && accessToken != null) {
                    api.groups(accessToken)
                } else emptyList()
                LoadResult(config, privateState, conversations, memberGroups)
            }
            configuration = data.config
            privacy = data.privacy
            history = data.conversations
            groups = data.groups.filter { it.optString("status") == "active" }
            showConsent = available && accessToken != null &&
                data.privacy?.optBoolean("provider_processing_allowed") != true
        } catch (exception: Exception) {
            error = exception.message ?: "HomeScout Assistant could not load."
        } finally {
            loading = false
        }
    }

    fun refreshHistory(token: String) {
        scope.launch {
            runCatching { withContext(Dispatchers.IO) { api.conversations(token) } }
                .onSuccess { history = it }
        }
    }

    fun loadConversation(row: JSONObject, token: String) {
        val id = row.optString("id")
        scope.launch {
            sending = true
            error = null
            try {
                val detail = withContext(Dispatchers.IO) { api.conversation(token, id) }
                conversationId = id
                lines.clear()
                contextProperties = emptyList()
                val items = detail.optJSONArray("messages")
                if (items != null) {
                    for (index in 0 until items.length()) {
                        val item = items.optJSONObject(index) ?: continue
                        lines += ChatLine(item.optString("role"), item.optString("text"))
                    }
                }
                showHistory = false
            } catch (exception: Exception) {
                error = exception.message ?: "That conversation could not be opened."
            } finally {
                sending = false
            }
        }
    }

    fun submitMessage() {
        val token = accessToken ?: return
        val text = draft.trim()
        if (text.isEmpty() || sending || !available || !consented) return
        draft = ""
        error = null
        sending = true
        scope.launch {
            try {
                val response = withContext(Dispatchers.IO) {
                    api.send(
                        token = token,
                        text = text,
                        conversationId = conversationId,
                        intent = initialIntent.ifBlank { "general" },
                        propertyId = initialPropertyId.takeIf(String::isNotBlank),
                        includeFinance = includeFinance,
                        includeSaved = includeSaved,
                        includeSchedule = includeSchedule,
                        includeWork = includeWork,
                        groupId = selectedGroup?.optString("id")
                    )
                }
                conversationId = response.optJSONObject("conversation")?.optString("id")
                val user = response.optJSONObject("user_message")?.optString("text").orEmpty()
                val assistant = response.optJSONObject("assistant_message")?.optString("text").orEmpty()
                if (user.isNotBlank() && assistant.isNotBlank()) {
                    lines += ChatLine("user", user)
                    lines += ChatLine("assistant", assistant)
                    val cards = response.optJSONArray("context_properties")
                    contextProperties = if (cards == null) emptyList() else {
                        (0 until cards.length()).mapNotNull { cards.optJSONObject(it) }
                    }
                    refreshHistory(token)
                } else {
                    error = "The provider did not return a complete reply."
                }
            } catch (exception: Exception) {
                error = exception.message ?: "HomeScout Assistant could not reply. Try again."
                draft = text
            } finally {
                sending = false
            }
        }
    }

    fun updateConsent(allowed: Boolean) {
        val token = accessToken ?: return
        consentBusy = true
        scope.launch {
            try {
                privacy = withContext(Dispatchers.IO) { api.updatePrivacy(token, allowed) }
                showConsent = false
            } catch (exception: Exception) {
                error = exception.message ?: "Privacy preference could not be saved."
            } finally {
                consentBusy = false
            }
        }
    }

    Column(Modifier.fillMaxSize(), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically,
            horizontalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back")
            }
            Surface(color = HomeScoutColors.paleBlue, shape = RoundedCornerShape(14.dp)) {
                Icon(Icons.Filled.AutoAwesome, null, Modifier.padding(10.dp).size(23.dp), tint = HomeScoutColors.blue)
            }
            Column(Modifier.weight(1f)) {
                Text("HomeScout Assistant", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                Text(if (available) "Housing help for Kenya" else "Provider not connected", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = {
                conversationId = null
                lines.clear()
                contextProperties = emptyList()
                error = null
            }) {
                Icon(Icons.Filled.Add, contentDescription = "New conversation")
            }
            IconButton(onClick = { showHistory = true }) {
                Icon(Icons.Filled.History, contentDescription = "Conversation history")
            }
            if (accessToken != null) {
                IconButton(onClick = { showPrivacy = true }) {
                    Icon(Icons.Filled.Lock, contentDescription = "Assistant privacy settings")
                }
            }
        }

        when {
            loading -> Box(Modifier.fillMaxSize(), contentAlignment = Alignment.Center) {
                CircularProgressIndicator()
            }
            accessToken == null -> Column(
                Modifier.fillMaxSize().padding(20.dp),
                verticalArrangement = Arrangement.Center,
                horizontalAlignment = Alignment.CenterHorizontally
            ) {
                EmptyState(
                    "Sign in to use HomeScout Assistant",
                    "Assistant conversations are private to your account."
                )
                Button(onClick = onSignIn) { Text("Sign in") }
            }
            !ApiConfiguration.isConfigured -> AssistantUnavailable(
                configuration.optString("disabled_message", "Connect the HomeScout API to continue.")
            )
            !available -> AssistantUnavailable(
                configuration.optString(
                    "disabled_message",
                    "HomeScout Assistant is not connected yet. No generated replies are available."
                )
            )
            else -> {
                error?.let { AssistantMessageNotice(it, isError = true) }
                if (!consented) {
                    AssistantMessageNotice(
                        "Review the privacy notice to allow messages to be processed by the configured AI provider."
                    )
                    OutlinedButton(
                        onClick = { showConsent = true },
                        modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp)
                    ) { Icon(Icons.Filled.Lock, null); Text("Review privacy and enable") }
                }
                if (initialPropertyId.isNotBlank()) {
                    AssistantMessageNotice("Context selected: this currently public home listing.")
                }
                ContextChoices(
                    includeFinance = includeFinance,
                    onFinance = { includeFinance = it },
                    includeSaved = includeSaved,
                    onSaved = { includeSaved = it },
                    includeSchedule = includeSchedule,
                    onSchedule = { includeSchedule = it },
                    includeWork = includeWork,
                    onWork = { includeWork = it },
                    groupName = selectedGroup?.optString("name"),
                    onChooseGroup = {
                        if (selectedGroup == null) {
                            if (groups.isEmpty()) accessToken.let { token ->
                                scope.launch {
                                    runCatching { withContext(Dispatchers.IO) { api.groups(token) } }
                                        .onSuccess { groups = it.filter { group -> group.optString("status") == "active" }; showGroups = true }
                                        .onFailure { error = it.message ?: "Shared groups could not be loaded." }
                                }
                            } else showGroups = true
                        } else selectedGroup = null
                    },
                    enabled = consented && !sending
                )
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 14.dp),
                    horizontalArrangement = Arrangement.spacedBy(4.dp)
                ) {
                    TextButton(onClick = { onNavigate("discover") }) { Text("Explore homes") }
                    TextButton(onClick = { onNavigate("finance") }) { Text("SmartRent") }
                    TextButton(onClick = { onNavigate("hub/support") }) { Text("Help") }
                }
                if (lines.isEmpty()) {
                    EmptyState(
                        "What would you like help with?",
                        "Ask about a home, your budget, viewing preparation, a lease term, or rental safety.",
                        Modifier.weight(1f)
                    )
                } else {
                    LazyColumn(
                        Modifier.weight(1f).fillMaxWidth(),
                        verticalArrangement = Arrangement.spacedBy(10.dp)
                    ) {
                        items(lines) { line -> AssistantBubble(line) }
                        items(contextProperties) { property ->
                            HomeScoutCard(Modifier.fillMaxWidth().padding(horizontal = 14.dp)) {
                                TextButton(
                                    onClick = { onNavigate("property/" + property.optString("id")) },
                                    modifier = Modifier.fillMaxWidth()
                                ) {
                                    Column(horizontalAlignment = Alignment.Start) {
                                        Text(
                                            property.optString("title"),
                                            style = MaterialTheme.typography.titleSmall
                                        )
                                        Text(
                                            "KSh " + property.optString("rent_amount_kes") +
                                                " · " + property.optString("location"),
                                            style = MaterialTheme.typography.bodySmall
                                        )
                                    }
                                }
                            }
                        }
                        if (sending) item { AssistantTyping() }
                    }
                }
                Row(
                    Modifier.fillMaxWidth().padding(horizontal = 14.dp, vertical = 8.dp),
                    verticalAlignment = Alignment.Bottom,
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    OutlinedTextField(
                        value = draft,
                        onValueChange = { if (it.length <= 4000) draft = it },
                        modifier = Modifier.weight(1f),
                        enabled = consented && !sending,
                        placeholder = { Text("Ask HomeScout Assistant") },
                        minLines = 1,
                        maxLines = 5,
                        keyboardOptions = KeyboardOptions(
                            capitalization = KeyboardCapitalization.Sentences,
                            imeAction = ImeAction.Send
                        ),
                        keyboardActions = KeyboardActions(onSend = { submitMessage() })
                    )
                    IconButton(
                        onClick = ::submitMessage,
                        enabled = draft.isNotBlank() && consented && !sending,
                        modifier = Modifier.size(52.dp)
                    ) {
                        if (sending) CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                        else Icon(Icons.AutoMirrored.Filled.Send, contentDescription = "Send message")
                    }
                }
            }
        }
    }

    if (showConsent && accessToken != null && available) {
        AlertDialog(
            onDismissRequest = { if (!consentBusy) showConsent = false },
            icon = { Icon(Icons.Filled.Lock, null) },
            title = { Text("Choose whether to use HomeScout Assistant") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text(configuration.optString("privacy_notice"))
                    Text("Your account details are not included by default. You can select specific context for each message.")
                }
            },
            confirmButton = {
                TextButton(enabled = !consentBusy, onClick = { updateConsent(true) }) {
                    Text(if (consentBusy) "Saving…" else "Allow AI processing")
                }
            },
            dismissButton = { TextButton(onClick = { showConsent = false }) { Text("Not now") } }
        )
    }

    if (showPrivacy && accessToken != null) {
        AlertDialog(
            onDismissRequest = { showPrivacy = false },
            icon = { Icon(Icons.Filled.Lock, null) },
            title = { Text("Assistant privacy") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(configuration.optString("privacy_notice"))
                    Text(if (consented) "Provider processing is enabled." else "Provider processing is disabled.")
                }
            },
            confirmButton = {
                if (consented) {
                    TextButton(
                        enabled = !consentBusy,
                        onClick = { updateConsent(false); showPrivacy = false }
                    ) { Text("Withdraw consent") }
                } else {
                    TextButton(onClick = { showPrivacy = false; showConsent = available }) {
                        Text("Review consent")
                    }
                }
            },
            dismissButton = { TextButton(onClick = { showPrivacy = false }) { Text("Close") } }
        )
    }

    if (showHistory && accessToken != null) {
        AlertDialog(
            onDismissRequest = { showHistory = false },
            title = { Text("Your conversations") },
            text = {
                if (history.isEmpty()) Text("No saved HomeScout Assistant conversations yet.")
                else Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    history.forEach { row ->
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            TextButton(
                                onClick = { loadConversation(row, accessToken) },
                                modifier = Modifier.weight(1f)
                            ) { Text(row.optString("title"), maxLines = 2) }
                            IconButton(onClick = {
                                renameTarget = row
                                renameValue = row.optString("title")
                            }) { Icon(Icons.Filled.Edit, "Rename conversation") }
                            IconButton(onClick = { deleteTarget = row }) {
                                Icon(Icons.Filled.DeleteOutline, "Delete conversation")
                            }
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showHistory = false }) { Text("Close") } }
        )
    }

    if (showGroups) {
        AlertDialog(
            onDismissRequest = { showGroups = false },
            title = { Text("Select a shared house search") },
            text = {
                if (groups.isEmpty()) Text("No active shared groups are available.")
                else Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    groups.forEach { group ->
                        TextButton(
                            onClick = { selectedGroup = group; showGroups = false },
                            modifier = Modifier.fillMaxWidth()
                        ) { Text(group.optString("name")) }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { showGroups = false }) { Text("Close") } }
        )
    }

    renameTarget?.let { row ->
        AlertDialog(
            onDismissRequest = { renameTarget = null },
            title = { Text("Rename conversation") },
            text = {
                OutlinedTextField(
                    value = renameValue,
                    onValueChange = { renameValue = it.take(80) },
                    label = { Text("Conversation name") },
                    singleLine = true
                )
            },
            confirmButton = {
                TextButton(enabled = renameValue.isNotBlank(), onClick = {
                    val token = accessToken ?: return@TextButton
                    scope.launch {
                        runCatching {
                            withContext(Dispatchers.IO) {
                                api.rename(token, row.optString("id"), renameValue.trim())
                            }
                        }.onSuccess { refreshHistory(token); renameTarget = null }
                            .onFailure { error = it.message ?: "Conversation could not be renamed." }
                    }
                }) { Text("Save") }
            },
            dismissButton = { TextButton(onClick = { renameTarget = null }) { Text("Cancel") } }
        )
    }

    deleteTarget?.let { row ->
        AlertDialog(
            onDismissRequest = { deleteTarget = null },
            title = { Text("Delete this conversation?") },
            text = { Text("Its encrypted message history will be removed from your account.") },
            confirmButton = {
                TextButton(onClick = {
                    val token = accessToken ?: return@TextButton
                    scope.launch {
                        runCatching {
                            withContext(Dispatchers.IO) { api.delete(token, row.optString("id")) }
                        }.onSuccess {
                            refreshHistory(token)
                            if (conversationId == row.optString("id")) {
                                conversationId = null
                                lines.clear()
                            }
                            deleteTarget = null
                        }.onFailure { error = it.message ?: "Conversation could not be deleted." }
                    }
                }) { Text("Delete", color = MaterialTheme.colorScheme.error) }
            },
            dismissButton = { TextButton(onClick = { deleteTarget = null }) { Text("Cancel") } }
        )
    }
}

private data class LoadResult(
    val config: JSONObject,
    val privacy: JSONObject?,
    val conversations: List<JSONObject>,
    val groups: List<JSONObject>
)

@Composable
private fun ContextChoices(
    includeFinance: Boolean,
    onFinance: (Boolean) -> Unit,
    includeSaved: Boolean,
    onSaved: (Boolean) -> Unit,
    includeSchedule: Boolean,
    onSchedule: (Boolean) -> Unit,
    includeWork: Boolean,
    onWork: (Boolean) -> Unit,
    groupName: String?,
    onChooseGroup: () -> Unit,
    enabled: Boolean
) {
    HomeScoutCard(Modifier.fillMaxWidth().padding(horizontal = 14.dp)) {
        Column(Modifier.padding(horizontal = 12.dp, vertical = 8.dp)) {
            Text("Optional context for this message", style = MaterialTheme.typography.labelLarge)
            ContextToggle(Icons.Filled.Payments, "My SmartRent summary", includeFinance, onFinance, enabled)
            ContextToggle(Icons.Filled.BookmarkBorder, "My saved public homes", includeSaved, onSaved, enabled)
            ContextToggle(Icons.Filled.CalendarMonth, "My schedule and viewings", includeSchedule, onSchedule, enabled)
            ContextToggle(Icons.Filled.AutoAwesome, "My listings, moving tasks & bookings", includeWork, onWork, enabled)
            TextButton(enabled = enabled, onClick = onChooseGroup) {
                Text(groupName?.let { "Shared search: $it  ·  Remove" } ?: "Choose an active shared search")
            }
            Text("Only the selected context is sent with this message.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun ContextToggle(
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    title: String,
    checked: Boolean,
    onChecked: (Boolean) -> Unit,
    enabled: Boolean
) {
    Row(verticalAlignment = Alignment.CenterVertically) {
        Icon(icon, null, Modifier.size(18.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(title, Modifier.weight(1f), style = MaterialTheme.typography.bodySmall)
        Checkbox(checked = checked, onCheckedChange = onChecked, enabled = enabled)
    }
}

@Composable
private fun AssistantBubble(line: ChatLine) {
    val fromAssistant = line.role == "assistant"
    Row(
        Modifier.fillMaxWidth().padding(horizontal = 14.dp),
        horizontalArrangement = if (fromAssistant) Arrangement.Start else Arrangement.End
    ) {
        Surface(
            modifier = Modifier.fillMaxWidth(.88f),
            color = if (fromAssistant) MaterialTheme.colorScheme.surfaceVariant else HomeScoutColors.navy,
            shape = RoundedCornerShape(18.dp)
        ) {
            Text(
                line.text,
                Modifier.padding(horizontal = 15.dp, vertical = 12.dp),
                color = if (fromAssistant) MaterialTheme.colorScheme.onSurfaceVariant else HomeScoutColors.white,
                style = MaterialTheme.typography.bodyMedium
            )
        }
    }
}

@Composable
private fun AssistantTyping() {
    Row(Modifier.padding(start = 18.dp), verticalAlignment = Alignment.CenterVertically) {
        CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
        Text("HomeScout Assistant is responding…", Modifier.padding(start = 9.dp), style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun AssistantUnavailable(message: String) {
    Column(
        Modifier.fillMaxSize().padding(20.dp),
        verticalArrangement = Arrangement.Center,
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Icon(Icons.Filled.AutoAwesome, null, Modifier.size(44.dp), tint = HomeScoutColors.blue)
        Text("HomeScout Assistant is unavailable", style = MaterialTheme.typography.titleLarge)
        Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("No sample or canned answers are shown.", style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun AssistantMessageNotice(message: String, isError: Boolean = false) {
    Surface(
        Modifier.fillMaxWidth().padding(horizontal = 14.dp),
        color = if (isError) MaterialTheme.colorScheme.errorContainer else HomeScoutColors.paleBlue,
        shape = MaterialTheme.shapes.medium
    ) {
        Text(
            message,
            Modifier.padding(12.dp),
            color = if (isError) MaterialTheme.colorScheme.onErrorContainer else HomeScoutColors.navy,
            style = MaterialTheme.typography.bodySmall
        )
    }
}
