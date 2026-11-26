package ke.co.homescout.features.collaboration

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Switch
import androidx.compose.material3.Text
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.AuthApi
import ke.co.homescout.data.remote.PersonalHubApi
import ke.co.homescout.navigation.Destination
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter
import ke.co.homescout.ui.components.HomeScoutDateField
import ke.co.homescout.ui.components.HomeScoutDateTimeField

private data class DemoLocationIds(val countyId: String = "", val townId: String = "")

private data class DemoComparisonRow(
    val name: String,
    val location: String,
    val rent: Int,
    val deposit: Int,
    val bedrooms: Int,
    val monthlyExtra: Int,
    val moveInExtra: Int,
    val note: String,
)

private fun randomDemoComparison(): List<DemoComparisonRow> = listOf(
    DemoComparisonRow(
        "DEMO · Kilimani apartment", "Nairobi", kotlin.random.Random.nextInt(28_000, 46_000),
        32_000, 2, kotlin.random.Random.nextInt(3_000, 7_001),
        kotlin.random.Random.nextInt(12_000, 28_001), "Check water pressure and evening noise.",
    ),
    DemoComparisonRow(
        "DEMO · Ruaka townhouse", "Kiambu", kotlin.random.Random.nextInt(22_000, 37_001),
        25_000, 2, kotlin.random.Random.nextInt(2_000, 6_001),
        kotlin.random.Random.nextInt(9_000, 24_001), "Confirm commute time and parking.",
    ),
    DemoComparisonRow(
        "DEMO · Nyali studio", "Mombasa", kotlin.random.Random.nextInt(18_000, 31_001),
        20_000, 1, kotlin.random.Random.nextInt(2_000, 5_001),
        kotlin.random.Random.nextInt(8_000, 19_001), "Ask about internet and backup power.",
    ),
)

private val collaborationTabs = listOf("Messages", "Viewings", "Compare", "Roommates", "Groups", "Journal")
private const val DEMO_CONVERSATION_ID = "homescout-demo-conversation"
private const val DEMO_SENDER_ID = "homescout-demo-contact"

private data class DemoRoommate(
    val name: String,
    val about: String,
    val minBudget: Int,
    val maxBudget: Int,
    val tags: List<String>,
    val area: String,
)

private val demoRoommates = listOf(
    DemoRoommate("Amina · demo", "Quiet, tidy working professional looking to share a 2-bedroom home.", 12000, 26000, listOf("quiet", "tidy", "weekday routine"), "Kilimani example"),
    DemoRoommate("Brian · demo", "Friendly student who prefers a calm home and shared chores.", 10000, 22000, listOf("student", "calm", "shared chores"), "Ruiru example"),
    DemoRoommate("Njeri · demo", "Works hybrid and values good natural light and a clean kitchen.", 18000, 38000, listOf("hybrid work", "clean", "daylight"), "Westlands example"),
)

private fun demoConversationMessages(): List<JSONObject> = listOf(
    JSONObject().put("id", "demo-message-1").put("sender_user_id", DEMO_SENDER_ID)
        .put("body", "Hi! I’m looking at homes around Kilimani. Is the viewing checklist ready?")
        .put("created_at", "DEMO · example message"),
    JSONObject().put("id", "demo-message-2").put("sender_user_id", "demo-current-user")
        .put("body", "Yes, I’m checking water, power, security and the total move-in cost.")
        .put("created_at", "DEMO · example reply"),
)

@Composable
fun CollaborationScreen(
    accessToken: String?,
    initialPropertyId: String = "",
    initialConversationId: String = "",
    initialTab: String = "",
    onNavigate: (String) -> Unit,
    onSignIn: () -> Unit,
) {
    val api = remember { PersonalHubApi() }
    val scope = rememberCoroutineScope()
    var tab by rememberSaveable(initialPropertyId, initialConversationId, initialTab) {
        mutableStateOf(
            when {
                initialConversationId.isNotBlank() -> "Messages"
                initialTab in collaborationTabs -> initialTab
                initialPropertyId.isNotBlank() -> "Compare"
                else -> "Messages"
            }
        )
    }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var notice by remember { mutableStateOf<String?>(null) }
    var userId by remember { mutableStateOf("") }
    var inbox by remember { mutableStateOf(emptyList<JSONObject>()) }
    var messages by remember { mutableStateOf(emptyList<JSONObject>()) }
    var isDemoConversation by remember { mutableStateOf(false) }
    var viewings by remember { mutableStateOf(emptyList<JSONObject>()) }
    var comparisons by remember { mutableStateOf(emptyList<JSONObject>()) }
    var demoComparisonRows by remember { mutableStateOf(emptyList<DemoComparisonRow>()) }
    var demoNairobiIds by remember { mutableStateOf(DemoLocationIds()) }
    var availableHomes by remember { mutableStateOf(emptyList<JSONObject>()) }
    var privateDocuments by remember { mutableStateOf(emptyList<JSONObject>()) }
    var blockedUserIds by remember { mutableStateOf(emptySet<String>()) }
    var roommate by remember { mutableStateOf(JSONObject()) }
    var suggestions by remember { mutableStateOf(emptyList<JSONObject>()) }
    var interests by remember { mutableStateOf(emptyList<JSONObject>()) }
    var groups by remember { mutableStateOf(emptyList<JSONObject>()) }
    var journals by remember { mutableStateOf(emptyList<JSONObject>()) }
    var selectedConversation by remember { mutableStateOf(initialConversationId) }
    var selectedGroup by remember { mutableStateOf("") }
    var sharedSearches by remember { mutableStateOf(emptyList<JSONObject>()) }
    var sharedProperties by remember { mutableStateOf(emptyList<JSONObject>()) }
    var sharedTasks by remember { mutableStateOf(emptyList<JSONObject>()) }
    var goals by remember { mutableStateOf(emptyList<JSONObject>()) }
    val propertyIds = remember { mutableStateListOf<String>() }
    val monthlyCostInputs = remember { mutableStateMapOf<String, String>() }
    val moveInCostInputs = remember { mutableStateMapOf<String, String>() }
    val comparisonNotes = remember { mutableStateMapOf<String, String>() }
    var propertyId by rememberSaveable(initialPropertyId) { mutableStateOf(initialPropertyId) }
    var viewingAt by rememberSaveable { mutableStateOf(defaultViewingTime()) }
    var viewingDemoMode by rememberSaveable { mutableStateOf(false) }
    var messageDraft by rememberSaveable { mutableStateOf("") }
    val selectedAttachmentIds = remember { mutableStateListOf<String>() }
    val selectedPhotoDocumentIds = remember { mutableStateListOf<String>() }
    var taskTitle by rememberSaveable { mutableStateOf("") }
    var alias by rememberSaveable { mutableStateOf("") }
    var about by rememberSaveable { mutableStateOf("") }
    var budget by rememberSaveable { mutableStateOf("") }
    var minimumBudget by rememberSaveable { mutableStateOf("") }
    var roommateCountyId by rememberSaveable { mutableStateOf("") }
    var roommateTownId by rememberSaveable { mutableStateOf("") }
    var preferredMoveIn by rememberSaveable { mutableStateOf("") }
    var roommateLifestyleTags by rememberSaveable { mutableStateOf("") }
    var demoRoommateSearchUsed by rememberSaveable { mutableStateOf(false) }
    var matching by rememberSaveable { mutableStateOf(false) }
    var groupName by rememberSaveable { mutableStateOf("") }
    var inviteId by rememberSaveable { mutableStateOf("") }
    var groupExampleMode by rememberSaveable { mutableStateOf(false) }
    var shareSearchName by rememberSaveable { mutableStateOf("") }
    var sharedSearchQuery by rememberSaveable { mutableStateOf("") }
    var sharedRentMin by rememberSaveable { mutableStateOf("") }
    var sharedRentMax by rememberSaveable { mutableStateOf("") }
    var sharedComment by rememberSaveable { mutableStateOf("") }
    var goalTitle by rememberSaveable { mutableStateOf("") }
    var goalAmount by rememberSaveable { mutableStateOf("") }
    var goalDate by rememberSaveable { mutableStateOf("") }
    var shareGoalAmount by rememberSaveable { mutableStateOf(false) }
    var sharedGroupComparisons by remember { mutableStateOf(emptyList<JSONObject>()) }
    var journalTitle by rememberSaveable { mutableStateOf("") }
    var journalExampleMode by rememberSaveable { mutableStateOf(false) }
    var journalNotes by rememberSaveable { mutableStateOf("") }
    var journalViewingId by rememberSaveable { mutableStateOf("") }
    var journalPros by rememberSaveable { mutableStateOf("") }
    var journalCons by rememberSaveable { mutableStateOf("") }
    var journalRating by rememberSaveable { mutableStateOf("") }
    var waterChecked by rememberSaveable { mutableStateOf(false) }
    var powerChecked by rememberSaveable { mutableStateOf(false) }
    var securityChecked by rememberSaveable { mutableStateOf(false) }
    var shareTarget by rememberSaveable { mutableStateOf("") }

    fun loadMessages(id: String) {
        if (id == DEMO_CONVERSATION_ID) {
            isDemoConversation = true
            messages = demoConversationMessages()
            selectedConversation = id
            return
        }
        val token = accessToken ?: return
        scope.launch {
            try {
                messages = withContext(Dispatchers.IO) {
                    api.getArray("communications/conversations/$id/messages", token).jsonObjects()
                }
                isDemoConversation = false
                selectedConversation = id
            } catch (failure: Exception) { error = failure.message ?: "Messages are unavailable." }
        }
    }

    fun loadGroup(id: String) {
        val token = accessToken ?: return
        selectedGroup = id
        scope.launch {
            try {
                val values = withContext(Dispatchers.IO) {
                    listOf(
                        api.getArray("collaboration/groups/$id/searches", token).jsonObjects(),
                        api.getArray("collaboration/groups/$id/properties", token).jsonObjects(),
                        api.getArray("collaboration/groups/$id/moving-goals", token).jsonObjects(),
                        api.getArray("collaboration/groups/$id/comparisons", token).jsonObjects(),
                        api.getArray("collaboration/groups/$id/tasks", token).jsonObjects(),
                    )
                }
                sharedSearches = values[0]; sharedProperties = values[1]; goals = values[2]; sharedGroupComparisons = values[3]; sharedTasks = values[4]
            } catch (failure: Exception) { error = failure.message ?: "This shared group is unavailable." }
        }
    }

    fun openRoommateConversation(interestId: String) {
        val token = accessToken ?: return
        scope.launch {
            try {
                val conversation = withContext(Dispatchers.IO) {
                    api.send("communications/roommate-interests/$interestId/conversation", "POST", token)
                }
                onNavigate("collaboration?conversationId=${PersonalHubApi.query(conversation.optString("id"))}&tab=Messages")
            } catch (failure: Exception) {
                error = failure.message ?: "The roommate conversation is unavailable."
            }
        }
    }

    fun openGroupConversation(groupId: String) {
        val token = accessToken ?: return
        scope.launch {
            try {
                val conversation = withContext(Dispatchers.IO) {
                    api.send("communications/groups/$groupId/conversation", "GET", token)
                }
                onNavigate("collaboration?conversationId=${PersonalHubApi.query(conversation.optString("id"))}&tab=Messages")
            } catch (failure: Exception) {
                error = failure.message ?: "The group conversation is unavailable."
            }
        }
    }

    fun refresh() {
        val token = accessToken ?: return
        scope.launch {
            loading = true; error = null
            try {
                val values = withContext(Dispatchers.IO) {
                    val me = AuthApi().currentUser(token)
                    val rawRoommate = api.raw("collaboration/roommates/me", token).trim()
                    val roommateFilters = buildList {
                        roommateCountyId.trim().takeIf(String::isNotBlank)?.let { add("county_id=${PersonalHubApi.query(it)}") }
                        roommateTownId.trim().takeIf(String::isNotBlank)?.let { add("town_id=${PersonalHubApi.query(it)}") }
                        budget.toDoubleOrNull()?.let { add("budget_max=$it") }
                    }.joinToString("&")
                    listOf(
                        me.id,
                        api.getArray("communications/inbox", token).jsonObjects(),
                        api.getArray("viewings/calendar", token).jsonObjects(),
                        api.getArray("collaboration/comparisons", token).jsonObjects(),
                        if (rawRoommate == "null" || rawRoommate.isBlank()) JSONObject() else JSONObject(rawRoommate),
                        api.getArray("collaboration/roommates/suggestions" + if (roommateFilters.isBlank()) "" else "?$roommateFilters", token).jsonObjects(),
                        api.getArray("collaboration/roommates/interests", token).jsonObjects(),
                        api.getArray("collaboration/groups", token).jsonObjects(),
                        api.getArray("viewings/journals", token).jsonObjects(),
                        api.getObject("properties?limit=25", token).optJSONArray("items").jsonObjects(),
                        api.getArray("hub/documents", token).jsonObjects(),
                        api.getArray("communications/blocks", token).jsonObjects(),
                        runCatching {
                            val nairobi = api.getArray("locations/counties", token).jsonObjects()
                                .firstOrNull { it.optString("name").equals("Nairobi", ignoreCase = true) }
                            val countyId = nairobi?.optString("id").orEmpty()
                            val townId = if (countyId.isBlank()) "" else api
                                .getArray("locations/counties/$countyId/towns", token).jsonObjects()
                                .firstOrNull { it.optString("name").contains("Nairobi", ignoreCase = true) }
                                ?.optString("id").orEmpty()
                            DemoLocationIds(countyId, townId)
                        }.getOrDefault(DemoLocationIds()),
                    )
                }
                userId = values[0] as String; inbox = values[1] as List<JSONObject>
                viewings = values[2] as List<JSONObject>; comparisons = values[3] as List<JSONObject>
                roommate = values[4] as JSONObject; suggestions = values[5] as List<JSONObject>
                interests = values[6] as List<JSONObject>; groups = values[7] as List<JSONObject>
                journals = values[8] as List<JSONObject>; availableHomes = values[9] as List<JSONObject>
                privateDocuments = values[10] as List<JSONObject>
                blockedUserIds = (values[11] as List<JSONObject>).mapTo(mutableSetOf()) { it.optString("blocked_user_id") }
                demoNairobiIds = values[12] as DemoLocationIds
                alias = roommate.optString("display_alias", alias); about = roommate.optString("about", about)
                budget = roommate.optString("budget_max").takeUnless { it == "null" }.orEmpty()
                matching = roommate.optBoolean("matching_enabled", matching)
                minimumBudget = roommate.optString("budget_min").takeUnless { it == "null" }.orEmpty()
                roommateCountyId = roommate.optString("county_id").takeUnless { it == "null" }.orEmpty()
                roommateTownId = roommate.optString("town_id").takeUnless { it == "null" }.orEmpty()
                preferredMoveIn = roommate.optString("preferred_move_in").takeUnless { it == "null" }.orEmpty()
                roommateLifestyleTags = roommate.optJSONArray("lifestyle_tags").jsonStrings().joinToString(", ")
                if (selectedConversation.isNotBlank()) loadMessages(selectedConversation)
                val activeGroup = groups.firstOrNull { it.optString("id") == selectedGroup && it.optString("status") == "active" }
                    ?: groups.firstOrNull { it.optString("status") == "active" }
                selectedGroup = activeGroup?.optString("id").orEmpty()
                if (selectedGroup.isNotBlank()) loadGroup(selectedGroup)
            } catch (failure: Exception) { error = failure.message ?: "HomeScout could not load this screen." }
            finally { loading = false }
        }
    }

    fun send(
        path: String,
        method: String = "POST",
        body: JSONObject? = null,
        message: String,
        onSuccess: (() -> Unit)? = null
    ) {
        val token = accessToken ?: return
        scope.launch {
            loading = true; error = null
            try {
                withContext(Dispatchers.IO) { api.send(path, method, token, body) }
                notice = message
                onSuccess?.invoke()
                refresh()
            } catch (failure: Exception) { error = failure.message ?: "HomeScout could not complete that action." }
            finally { loading = false }
        }
    }

    LaunchedEffect(accessToken, initialConversationId) { refresh() }
    LaunchedEffect(initialPropertyId) {
        if (initialPropertyId.isNotBlank() && initialPropertyId !in propertyIds) propertyIds.add(initialPropertyId)
    }

    Column(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 10.dp)) {
            Text("Plan together", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text("Private conversations and shared home-search plans", color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        if (accessToken == null) {
            InfoCard("Sign in to coordinate your move", "Messages and shared plans belong to your HomeScout account.", action = "Go to Profile", onAction = onSignIn)
            return@Column
        }
        Row(Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()).padding(horizontal = 12.dp), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            collaborationTabs.forEach { FilterChip(tab == it, onClick = { tab = it }, label = { Text(it) }) }
        }
        if (loading) CircularProgressIndicator(Modifier.padding(12.dp))
        error?.let { InfoCard("Could not load this section", it) }
        notice?.let { InfoCard("Updated", it) }
        val selectedGroupRecord = groups.firstOrNull { it.optString("id") == selectedGroup && it.optString("status") == "active" }
        LazyColumn(Modifier.fillMaxSize(), contentPadding = androidx.compose.foundation.layout.PaddingValues(16.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            when (tab) {
                "Messages" -> {
                    item { Intro("Messages", "Only participants can open these encrypted conversations.") }
                    item {
                        InfoCard(
                            "Demo conversation · sample only",
                            "Amina is a fictional renter. Try the chat to demonstrate the message flow; nothing is sent to a real person or saved to your account.",
                            action = if (selectedConversation == DEMO_CONVERSATION_ID) "Restart demo chat" else "Open demo chat",
                            onAction = { loadMessages(DEMO_CONVERSATION_ID) },
                        )
                    }
                    if (selectedConversation.isNotBlank()) {
                        item { OutlinedButton(onClick = { selectedConversation = ""; isDemoConversation = false }) { Text("Back to inbox") } }
                        if (isDemoConversation) item {
                            InfoCard("Sample chat", "Amina · demo contact", "Demo messages stay on this screen and reset when the chat is reopened.")
                        }
                        items(messages) { row ->
                            val senderId = row.optString("sender_user_id")
                            val isBlocked = senderId in blockedUserIds
                            MessageCard(
                                title = when {
                                    senderId == userId || senderId == "demo-current-user" -> "You"
                                    isDemoConversation && senderId == DEMO_SENDER_ID -> "Amina · demo"
                                    else -> "HomeScout member"
                                },
                                body = row.optString("body"),
                                supporting = listOfNotNull(
                                    row.optString("created_at"),
                                    row.optJSONArray("attachments").jsonObjects().map { it.optString("filename") }.takeIf { it.isNotEmpty() }?.joinToString(prefix = "Files: ")
                                ).joinToString(" · "),
                                onReport = if (isDemoConversation || senderId == userId) null else {
                                    { send("communications/messages/${row.optString("id")}/reports", body = JSONObject().put("category", "other"), message = "Report received for review.") }
                                },
                                onBlock = if (isDemoConversation || senderId == userId) null else {
                                    { send("communications/blocks/$senderId", if (isBlocked) "DELETE" else "PUT", message = if (isBlocked) "Member unblocked." else "Member blocked.") }
                                },
                                blockLabel = if (isBlocked) "Unblock" else "Block"
                            )
                        }
                        item {
                            if (isDemoConversation) {
                                OutlinedButton(onClick = {
                                    messageDraft = listOf(
                                        "DEMO · Hi Amina, is the water available throughout the week?",
                                        "DEMO · Could we arrange a viewing after 2 PM this week?",
                                        "DEMO · Please share the move-in costs and parking details.",
                                    ).random()
                                }, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                                Text("Demo chat only · Send adds a local example message and reply. Nothing is sent to a real account.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            OutlinedTextField(messageDraft, { messageDraft = it }, Modifier.fillMaxWidth(), label = { Text("Message") }, minLines = 2)
                            if (!isDemoConversation) {
                                Text("Attach private documents (up to five)", style = MaterialTheme.typography.labelLarge)
                                privateDocuments.take(10).forEach { document ->
                                    Row(verticalAlignment = Alignment.CenterVertically) {
                                        Checkbox(checked = document.optString("id") in selectedAttachmentIds, onCheckedChange = { checked ->
                                            val id = document.optString("id")
                                            if (checked && selectedAttachmentIds.size < 5 && id !in selectedAttachmentIds) selectedAttachmentIds.add(id)
                                            if (!checked) selectedAttachmentIds.remove(id)
                                        })
                                        Text(document.optString("original_filename", "Private file"))
                                    }
                                }
                                if (privateDocuments.isEmpty()) Text("Upload a document in Profile first if you want to attach a file.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Button(onClick = {
                                if (isDemoConversation && messageDraft.isNotBlank()) {
                                    val sent = messageDraft.trim()
                                    messages = messages + JSONObject()
                                        .put("id", "demo-user-${System.nanoTime()}")
                                        .put("sender_user_id", "demo-current-user")
                                        .put("body", sent)
                                        .put("created_at", "DEMO · just now")
                                    messages = messages + JSONObject()
                                        .put("id", "demo-reply-${System.nanoTime()}")
                                        .put("sender_user_id", DEMO_SENDER_ID)
                                        .put("body", "Thanks for the message! This is an example reply in the HomeScout demo chat.")
                                        .put("created_at", "DEMO · sample reply")
                                    messageDraft = ""
                                    notice = "Demo only: no message was sent to a real person."
                                } else if (messageDraft.isNotBlank()) {
                                    val body = JSONObject().put("body", messageDraft.trim()).put("attachment_document_ids", JSONArray().apply {
                                        selectedAttachmentIds.take(5).forEach(::put)
                                    })
                                    send(
                                        "communications/conversations/$selectedConversation/messages",
                                        body = body,
                                        message = "Message sent.",
                                        onSuccess = {
                                            messageDraft = ""
                                            selectedAttachmentIds.clear()
                                        }
                                    )
                                }
                            }, enabled = messageDraft.isNotBlank() && !loading) { Text("Send") }
                        }
                    } else if (inbox.isEmpty()) item {
                        InfoCard(
                            "No live conversations yet",
                            "Send a property enquiry or accept a roommate request to start a chat.",
                            action = "Find a home to ask about",
                            onAction = { onNavigate(Destination.Discover.route) }
                        )
                    }
                    else items(inbox) { row -> InfoCard(row.optString("title", "HomeScout conversation"), "${row.optInt("unread_count")} unread · ${row.optString("last_message_at")}", action = "Open", onAction = { loadMessages(row.optString("id")) }) }
                }
                "Viewings" -> {
                    val sampleProperty = availableHomes.firstOrNull { !it.optBoolean("is_demo") } ?: availableHomes.firstOrNull()
                    val liveRequestableProperties = availableHomes.filterNot { it.optBoolean("is_demo") }
                    item { Intro("Viewing requests", "Requests remain pending until the listing contact confirms. Dates use DD-MM-YYYY and East Africa time.") }
                    item {
                        InfoCard(
                            "Viewing example · demo only",
                            "A fictional Kilimani viewing with a random date and time. It is never sent to a host or shown as confirmed.",
                            "The example fills the property ID when a listing is loaded. Real requests require a published, available, non-demo property.",
                            action = "Fill random demo example",
                            onAction = {
                                propertyId = sampleProperty?.optString("id")?.takeIf(String::isNotBlank)
                                    ?: "DEMO-PROPERTY-KILIMANI-${kotlin.random.Random.nextInt(100, 999)}"
                                viewingAt = defaultViewingTime()
                                viewingDemoMode = true
                                notice = "Demo values filled. They are not sent or saved as an appointment."
                            },
                        )
                    }
                    item {
                        FormCard("Request a viewing") {
                            OutlinedTextField(
                                propertyId,
                                { propertyId = it; viewingDemoMode = false },
                                Modifier.fillMaxWidth(),
                                label = { Text("Property ID") },
                                supportingText = { Text("A real property ID is loaded from your selected listing. Demo IDs cannot be submitted.") },
                                singleLine = true,
                            )
                            HomeScoutDateTimeField(
                                value = viewingAt,
                                onValueChange = { viewingAt = it },
                                label = "Viewing date and time · DD-MM-YYYY",
                                modifier = Modifier.fillMaxWidth(),
                            )
                            if (viewingDemoMode) {
                                Text("DEMO PREVIEW · ${sampleProperty?.optString("title")?.takeIf(String::isNotBlank) ?: "Kilimani example home"} · ${formatDemoDateTime(viewingAt)}. Not sent and not confirmed.", color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.bodySmall)
                                if (liveRequestableProperties.any { it.optString("id") == propertyId }) {
                                    OutlinedButton(onClick = { viewingDemoMode = false }) { Text("Use this live listing for a real request") }
                                }
                            }
                            Button(onClick = {
                                send("viewings/requests", body = JSONObject().put("property_id", propertyId.trim()).put("requested_at", viewingAt.trim()).put("timezone", "Africa/Nairobi"), message = "Viewing request sent. Await confirmation.")
                            }, enabled = !viewingDemoMode && liveRequestableProperties.any { it.optString("id") == propertyId.trim() } && runCatching { ZonedDateTime.parse(viewingAt) }.isSuccess) { Text("Request time") }
                            if (!viewingDemoMode && propertyId.isNotBlank() && liveRequestableProperties.none { it.optString("id") == propertyId.trim() }) {
                                Text("Choose a currently available listing. Demo examples cannot create real appointments.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            }
                        }
                    }
                    if (viewings.isEmpty()) item { InfoCard("No viewings", "Your schedule and viewing history will appear here.") }
                    items(viewings) { row ->
                        val id = row.optString("id")
                        val status = row.optString("status")
                        val isHost = row.optString("host_user_id") == userId
                        val isRequester = row.optBoolean("is_requester")
                        val canComplete = status == "confirmed" && isHost && runCatching {
                            ZonedDateTime.parse(row.optString("requested_at")).isBefore(ZonedDateTime.now())
                        }.getOrDefault(false)
                        Card(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Text(row.optString("property_title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                                Text("${status.replace('_', ' ')} · ${formatDemoDateTime(row.optString("requested_at"))}")
                                row.optString("request_message").takeIf(String::isNotBlank)?.let { Text(it) }
                                row.optString("proposed_at").takeIf(String::isNotBlank)?.let { Text("Proposed time: ${formatDemoDateTime(it)}") }
                                val history = row.optJSONArray("history").jsonObjects().joinToString(" · ") { it.optString("action").replace('_', ' ') }
                                if (history.isNotBlank()) Text("History: $history", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                                if (isHost && status in listOf("requested", "confirmed")) {
                                    HomeScoutDateTimeField(viewingAt, { viewingAt = it }, "Propose date and time · DD-MM-YYYY", Modifier.fillMaxWidth())
                                }
                                if (status == "requested" && isHost) {
                                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                        OutlinedButton(onClick = { send("viewings/$id/actions", body = JSONObject().put("action", "confirm"), message = "Viewing confirmed.") }) { Text("Confirm") }
                                        OutlinedButton(onClick = { send("viewings/$id/actions", body = JSONObject().put("action", "decline"), message = "Viewing request declined.") }) { Text("Decline") }
                                        OutlinedButton(onClick = { send("viewings/$id/actions", body = JSONObject().put("action", "propose_reschedule").put("proposed_at", viewingAt.trim()), message = "New time proposed.") }, enabled = runCatching { ZonedDateTime.parse(viewingAt) }.isSuccess) { Text("Propose time") }
                                    }
                                }
                                if (status == "reschedule_proposed" && isRequester) {
                                    OutlinedButton(onClick = { send("viewings/$id/actions", body = JSONObject().put("action", "accept_reschedule"), message = "New viewing time accepted.") }) { Text("Accept new time") }
                                }
                                if (status in listOf("requested", "confirmed", "reschedule_proposed")) {
                                    OutlinedButton(onClick = { send("viewings/$id/actions", body = JSONObject().put("action", "cancel"), message = "Viewing cancelled.") }) { Text("Cancel viewing") }
                                }
                                if (canComplete) {
                                    OutlinedButton(onClick = { send("viewings/$id/actions", body = JSONObject().put("action", "complete"), message = "Viewing marked complete.") }) { Text("Mark complete") }
                                }
                                if (status in listOf("confirmed", "completed", "cancelled")) {
                                    OutlinedButton(onClick = { propertyId = row.optString("property_id"); journalViewingId = id; tab = "Journal" }) { Text("Add journal entry") }
                                }
                            }
                        }
                    }
                }
                "Compare" -> {
                    item { Intro("Compare up to five homes", "True costs use listing figures where available; your notes remain private.") }
                    item {
                        InfoCard(
                            "Sample comparison · fictional demo data",
                            "Kilimani example · KSh 38,000/month · 2 bedrooms · furnished\nRuiru example · KSh 24,000/month · 2 bedrooms · parking\nNyali example · KSh 46,000/month · 1 bedroom · pool",
                            "Generate random fictional comparisons below. To save a comparison to your account, use the valid listing IDs loaded from HomeScout.",
                        )
                    }
                    item {
                        OutlinedButton(
                            onClick = { demoComparisonRows = randomDemoComparison() },
                            modifier = Modifier.fillMaxWidth(),
                        ) { Text("Generate random demo comparison") }
                    }
                    items(demoComparisonRows) { row ->
                        InfoCard(
                            row.name,
                            "KSh ${row.rent}/month · KSh ${row.deposit} deposit · ${row.bedrooms} bedroom(s)\nEstimated extra monthly costs: KSh ${row.monthlyExtra}\nEstimated move-in extras: KSh ${row.moveInExtra}",
                            "${row.location} · ${row.note} · Fictional preview only; not saved as a real property comparison.",
                        )
                    }
                    if (availableHomes.size >= 2) item {
                        OutlinedButton(onClick = {
                            propertyIds.clear()
                            availableHomes.take(3).forEach { propertyIds.add(it.optString("id")) }
                            propertyIds.forEach { id ->
                                monthlyCostInputs[id] = kotlin.random.Random.nextInt(2_500, 7_501).toString()
                                moveInCostInputs[id] = kotlin.random.Random.nextInt(8_000, 30_001).toString()
                                comparisonNotes[id] = listOf(
                                    "DEMO · Check water pressure and evening noise.",
                                    "DEMO · Confirm parking and commute costs.",
                                    "DEMO · Ask about internet and backup power.",
                                ).random()
                            }
                            notice = "Random example costs and notes filled using loaded listing IDs. Tap Save comparison to store this shortlist on your account."
                        }, modifier = Modifier.fillMaxWidth()) { Text("Fill random shortlist from loaded homes") }
                    }
                    items(availableHomes) { home ->
                        val id = home.optString("id")
                        Card(Modifier.fillMaxWidth()) {
                            Row(Modifier.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(checked = id in propertyIds, onCheckedChange = { checked ->
                                    if (checked && propertyIds.size < 5 && id !in propertyIds) propertyIds.add(id)
                                    if (!checked) propertyIds.remove(id)
                                })
                                Column(Modifier.weight(1f)) {
                                    Text(home.optString("title"), fontWeight = FontWeight.SemiBold)
                                    Text("KSh ${home.optString("rent_amount")} · ${home.optJSONObject("location")?.optString("town_name").orEmpty()}")
                                    if (id in propertyIds) {
                                        OutlinedTextField(monthlyCostInputs[id].orEmpty(), { monthlyCostInputs[id] = it }, Modifier.fillMaxWidth(), label = { Text("Your extra monthly KES estimate") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                                        OutlinedTextField(moveInCostInputs[id].orEmpty(), { moveInCostInputs[id] = it }, Modifier.fillMaxWidth(), label = { Text("Your extra move-in KES estimate") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                                        OutlinedTextField(comparisonNotes[id].orEmpty(), { comparisonNotes[id] = it }, Modifier.fillMaxWidth(), label = { Text("Private note") }, maxLines = 2)
                                    }
                                }
                            }
                        }
                    }
                    item {
                        Button(onClick = {
                            val itemsBody = JSONArray().apply {
                                propertyIds.forEach { id ->
                                    val item = JSONObject().put("property_id", id)
                                    monthlyCostInputs[id].orEmpty().toDoubleOrNull()?.let { item.put("monthly_cost_input", it) }
                                    moveInCostInputs[id].orEmpty().toDoubleOrNull()?.let { item.put("move_in_cost_input", it) }
                                    comparisonNotes[id].orEmpty().trim().takeIf(String::isNotBlank)?.let { item.put("note", it) }
                                    put(item)
                                }
                            }
                            val body = JSONObject().put("name", "My home shortlist").put("items", itemsBody)
                            send("collaboration/comparisons", body = body, message = "Private comparison saved.")
                            propertyIds.clear()
                            monthlyCostInputs.clear(); moveInCostInputs.clear(); comparisonNotes.clear()
                        }, enabled = propertyIds.size in 2..5) { Text("Save comparison (${propertyIds.size}/5)") }
                    }
                    items(comparisons) { board ->
                        val propertySummaries = board.optJSONArray("items").jsonObjects().map { home ->
                            val utilities = home.optJSONObject("utilities")
                            "${home.optString("title")}\n" + listOfNotNull(
                                "KSh ${home.optString("rent_amount_kes")} rent · KSh ${home.optString("deposit_amount_kes")} deposit",
                                "${home.optString("bedrooms")} bedrooms · ${home.optString("bathrooms")} bathrooms · ${home.optString("size_sqm")} m²",
                                "${home.optString("county")} · ${home.optString("town")} · ${home.optString("furnishing")}",
                                home.optJSONArray("amenities").jsonStrings().joinToString().takeIf(String::isNotBlank)?.let { "Amenities: $it" },
                                "Move-in estimate: KSh ${home.optString("estimated_move_in_total_kes")} · extra monthly: KSh ${home.optString("user_monthly_cost_input_kes")}",
                                "Water: ${utilities?.optString("water_availability").orEmpty()} · power: ${utilities?.optString("electricity_available").orEmpty()} · internet: ${utilities?.optString("internet_available").orEmpty()}",
                                home.optString("security_information").takeIf(String::isNotBlank)?.let { "Security on listing: $it" },
                                home.optString("user_note").takeIf(String::isNotBlank)?.let { "Your note: $it" },
                                "Transport details not available"
                            ).joinToString("\n")
                        }.joinToString("\n\n")
                        InfoCard(board.optString("name"), "Private comparison · ${board.optJSONArray("items").jsonObjects().size} homes\n\n$propertySummaries")
                    }
                }
                "Roommates" -> {
                    item { Intro("Roommate matching", "Only profiles that opt in appear here. Contact details stay private.") }
                    item {
                        FormCard("Your profile") {
                            OutlinedButton(onClick = {
                                val name = listOf("Amina", "Brian", "Njeri", "Sam").random()
                                val minimum = listOf(10_000, 12_000, 15_000, 18_000).random()
                                val maximum = minimum + listOf(12_000, 16_000, 20_000, 24_000).random()
                                alias = "DEMO · $name"
                                about = listOf(
                                    "Friendly, tidy renter looking for a calm shared home near work.",
                                    "Hybrid worker who values a clean kitchen, natural light, and clear house rules.",
                                    "Quiet student looking for a safe, affordable place with shared chores.",
                                ).random()
                                minimumBudget = minimum.toString()
                                budget = maximum.toString()
                                roommateCountyId = demoNairobiIds.countyId
                                roommateTownId = demoNairobiIds.townId
                                preferredMoveIn = java.time.LocalDate.now(ZoneId.of("Africa/Nairobi"))
                                    .plusMonths(kotlin.random.Random.nextLong(1, 4)).withDayOfMonth(1).toString()
                                roommateLifestyleTags = listOf(
                                    "quiet, tidy, shared chores",
                                    "hybrid work, clean, daylight",
                                    "student, calm, shared chores",
                                ).random()
                                matching = true
                                demoRoommateSearchUsed = true
                                notice = if (demoNairobiIds.countyId.isBlank() || demoNairobiIds.townId.isBlank()) {
                                    "Random demo profile filled. Nairobi location IDs could not load, so those optional filters are blank. Save profile to keep the sample."
                                } else {
                                    "Random demo profile filled with real Nairobi location IDs. Review it, then tap Save profile to store it on your account."
                                }
                            }) { Text("Fill a new random example") }
                            OutlinedTextField(alias, { alias = it }, Modifier.fillMaxWidth(), label = { Text("Display name") }, singleLine = true)
                            OutlinedTextField(about, { about = it }, Modifier.fillMaxWidth(), label = { Text("About you") }, minLines = 2)
                            OutlinedTextField(minimumBudget, { minimumBudget = it }, Modifier.fillMaxWidth(), label = { Text("Minimum monthly budget in KSh") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                            OutlinedTextField(budget, { budget = it }, Modifier.fillMaxWidth(), label = { Text("Maximum monthly budget in KSh") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                            OutlinedTextField(roommateCountyId, { roommateCountyId = it }, Modifier.fillMaxWidth(), label = { Text("County ID (optional filter)") }, supportingText = { Text("The example uses Nairobi's actual county ID from HomeScout location data.") }, singleLine = true)
                            OutlinedTextField(roommateTownId, { roommateTownId = it }, Modifier.fillMaxWidth(), label = { Text("Town ID (optional filter)") }, supportingText = { Text("The example uses Nairobi's actual town ID from HomeScout location data.") }, singleLine = true)
                            HomeScoutDateField(preferredMoveIn, { preferredMoveIn = it }, "Preferred move-in date · DD-MM-YYYY", Modifier.fillMaxWidth())
                            OutlinedTextField(roommateLifestyleTags, { roommateLifestyleTags = it }, Modifier.fillMaxWidth(), label = { Text("Lifestyle tags (comma separated)") })
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Switch(matching, { matching = it }); Text("Show me in suggestions", Modifier.padding(start = 8.dp))
                            }
                            Button(onClick = {
                                val body = JSONObject().put("display_alias", alias.trim()).put("about", about.trim()).put("matching_enabled", matching)
                                    .put("lifestyle_tags", JSONArray().apply { roommateLifestyleTags.split(',').map(String::trim).filter(String::isNotBlank).forEach(::put) })
                                    .put("budget_min", minimumBudget.toDoubleOrNull() ?: JSONObject.NULL)
                                    .put("budget_max", budget.toDoubleOrNull() ?: JSONObject.NULL)
                                    .put("county_id", roommateCountyId.trim().takeIf(String::isNotBlank) ?: JSONObject.NULL)
                                    .put("town_id", roommateTownId.trim().takeIf(String::isNotBlank) ?: JSONObject.NULL)
                                    .put("preferred_move_in", preferredMoveIn.trim().takeIf(String::isNotBlank) ?: JSONObject.NULL)
                                send("collaboration/roommates/me", "PUT", body, "Roommate preferences saved.")
                            }, enabled = alias.isNotBlank()) { Text("Save profile") }
                            OutlinedButton(onClick = {
                                demoRoommateSearchUsed = true
                                val token = accessToken
                                if (token != null) scope.launch {
                                    loading = true
                                    try {
                                        val query = buildList {
                                            roommateCountyId.trim().takeIf(String::isNotBlank)?.let { add("county_id=${PersonalHubApi.query(it)}") }
                                            roommateTownId.trim().takeIf(String::isNotBlank)?.let { add("town_id=${PersonalHubApi.query(it)}") }
                                            budget.toDoubleOrNull()?.let { add("budget_max=$it") }
                                        }.joinToString("&")
                                        suggestions = withContext(Dispatchers.IO) {
                                            api.getArray("collaboration/roommates/suggestions" + if (query.isBlank()) "" else "?$query", token).jsonObjects()
                                        }
                                        notice = if (suggestions.isEmpty()) "No live opt-in profiles match yet. Fictional demo matches are shown below." else "${suggestions.size} live opt-in profile(s) found. Demo examples are labeled separately."
                                    } catch (failure: Exception) {
                                        error = failure.message ?: "Roommate matches could not be loaded."
                                    } finally { loading = false }
                                }
                            }, enabled = !loading) { Text("Find matches") }
                        }
                    }
                    items(suggestions) { row ->
                        InfoCard(row.optString("display_alias"), row.optString("about"), "${row.optString("budget_min", "—")}–${row.optString("budget_max", "—")} KSh · ${row.optJSONArray("shared_preferences").jsonStrings().joinToString()}", action = "Request to connect", onAction = {
                            send("collaboration/roommates/${row.optString("profile_id")}/interests", body = JSONObject(), message = "Connection request sent.")
                        })
                    }
                    if (demoRoommateSearchUsed || suggestions.isEmpty()) {
                        val minFilter = minimumBudget.toIntOrNull() ?: 0
                        val maxFilter = budget.toIntOrNull() ?: Int.MAX_VALUE
                        val tags = roommateLifestyleTags.split(',').map(String::trim).filter(String::isNotBlank)
                        val sampleMatches = demoRoommates.filter { candidate ->
                            candidate.minBudget <= maxFilter && candidate.maxBudget >= minFilter &&
                                (tags.isEmpty() || tags.any { tag -> candidate.tags.any { it.contains(tag, ignoreCase = true) } })
                        }
                        item { Intro("Demo match examples", "Fictional profiles only · filtered by the budget and lifestyle tags above") }
                        if (sampleMatches.isEmpty()) item { InfoCard("No sample matches for these filters", "Change the budget or lifestyle tags, then tap Find matches again.") }
                        items(sampleMatches) { candidate ->
                            InfoCard(
                                "${candidate.name} · fictional",
                                candidate.about,
                                "KSh ${candidate.minBudget}–${candidate.maxBudget} · ${candidate.area} · ${candidate.tags.joinToString()}",
                            )
                        }
                    }
                    items(interests.filter { it.optString("target_user_id") == userId && it.optString("status") == "pending" }) { row ->
                        InfoCard("Roommate request", "A member would like to connect.", "Accepting opens a private conversation.", action = "Accept", onAction = {
                            send("collaboration/roommates/interests/${row.optString("id")}", "PATCH", JSONObject().put("accept", true), "Connection accepted.")
                        })
                    }
                    items(interests.filter { it.optString("status") == "accepted" }) { row ->
                        InfoCard("Roommate connection", "Contact details remain private. Start a HomeScout conversation when you are ready.", action = "Open conversation", onAction = {
                            openRoommateConversation(row.optString("id"))
                        })
                    }
                }
                "Groups" -> {
                    item { Intro("Shared search", "Create a small private group to share homes and coordinate a move.") }
                    item {
                        InfoCard(
                            "Shared group example · demo only",
                            "Generate a random group name, invite ID example, rent budget, home ID, goal amount, task, and notes. The demo invite ID is never sent to another account.",
                            "Tap Save example group to create a private group on your account. Then the example plan fields are ready to save individually.",
                        )
                    }
                    item {
                        FormCard("Create a group") {
                            OutlinedButton(onClick = {
                                val area = listOf("Kilimani", "Westlands", "Ruaka", "Ruiru").random()
                                val lower = listOf(22_000, 25_000, 28_000, 32_000).random()
                                groupName = "DEMO · $area house hunt"
                                inviteId = "DEMO-USER-${kotlin.random.Random.nextInt(100, 999)}"
                                groupExampleMode = true
                                shareSearchName = "DEMO · $area homes under KSh ${lower + 15_000}"
                                sharedSearchQuery = "$area, Kenya"
                                sharedRentMin = lower.toString()
                                sharedRentMax = (lower + 15_000).toString()
                                propertyId = availableHomes.firstOrNull()?.optString("id")?.takeIf(String::isNotBlank)
                                    ?: "DEMO-PROPERTY-$area"
                                taskTitle = "DEMO · Compare commute and utilities"
                                goalTitle = "DEMO · Moving buffer"
                                goalDate = java.time.LocalDate.now(ZoneId.of("Africa/Nairobi")).plusMonths(kotlin.random.Random.nextLong(2, 5)).toString()
                                goalAmount = kotlin.random.Random.nextInt(35_000, 75_001).toString()
                                sharedComment = "DEMO · Check water, security, parking, and evening noise."
                                notice = "Random group and plan details filled. The example invite ID is display-only and will not be sent. Save the group, then save its sample plan fields."
                            }) { Text("Fill a new random example") }
                            OutlinedTextField(
                                groupName,
                                { value ->
                                    groupName = value
                                    if (groupExampleMode) { groupExampleMode = false; inviteId = "" }
                                },
                                Modifier.fillMaxWidth(),
                                label = { Text("Group name") },
                                singleLine = true,
                            )
                            OutlinedTextField(
                                inviteId,
                                { value -> inviteId = value; groupExampleMode = false },
                                Modifier.fillMaxWidth(),
                                label = { Text("Invitee account ID (optional)") },
                                supportingText = {
                                    Text(if (groupExampleMode) "Demo ID only · not sent. Enter a real HomeScout account ID to invite someone." else "Leave blank to create a private group with only your account.")
                                },
                                singleLine = true,
                            )
                            Button(onClick = {
                                val isExample = groupExampleMode
                                val invitees = JSONArray().apply {
                                    if (!isExample) inviteId.trim().takeIf(String::isNotBlank)?.let(::put)
                                }
                                send(
                                    "collaboration/groups",
                                    body = JSONObject().put("name", groupName.trim()).put("invite_user_ids", invitees),
                                    message = if (isExample) "Demo group saved to your account. No demo invitation was sent." else "Group created.",
                                    onSuccess = {
                                        groupName = ""; inviteId = ""; groupExampleMode = false
                                    },
                                )
                            }, enabled = groupName.isNotBlank()) { Text(if (groupExampleMode) "Save example group" else "Create shared space") }
                        }
                    }
                    items(groups) { row ->
                        val invited = row.optString("status") == "invited"
                        InfoCard(row.optString("name"), "${row.optString("status")} · ${row.optJSONArray("members").jsonObjects().size} members", action = if (invited) "Accept" else "Open", onAction = {
                            if (invited) send("collaboration/groups/${row.optString("id")}/invitation-response?accept=true", message = "Invitation accepted.") else loadGroup(row.optString("id"))
                        })
                    }
                    if (selectedGroup.isNotBlank()) {
                        item { FormCard("Shared group plan") {
                            Text("Group ID · $selectedGroup", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("Your account ID · $userId", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            OutlinedButton(onClick = { openGroupConversation(selectedGroup) }) { Text("Open group conversation") }
                            Text("DEMO values stay in this private group and are saved only when you tap an Add or Share button.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            OutlinedButton(onClick = {
                                val area = listOf("Kilimani", "Westlands", "Ruaka", "Ruiru").random()
                                val minRent = listOf(22_000, 25_000, 28_000, 32_000).random()
                                shareSearchName = "DEMO · $area 2-bedroom search"
                                sharedSearchQuery = "$area, Kenya"
                                sharedRentMin = minRent.toString()
                                sharedRentMax = (minRent + listOf(12_000, 15_000, 18_000).random()).toString()
                                propertyId = availableHomes.firstOrNull()?.optString("id")?.takeIf(String::isNotBlank)
                                    ?: "DEMO-PROPERTY-$area"
                                taskTitle = "DEMO · Compare commute options"
                                goalTitle = "DEMO · Moving buffer"
                                goalDate = java.time.LocalDate.now(ZoneId.of("Africa/Nairobi")).plusMonths(kotlin.random.Random.nextLong(2, 5)).toString()
                                goalAmount = kotlin.random.Random.nextInt(35_000, 75_001).toString()
                                sharedComment = "DEMO · Confirm water, security, parking, and internet."
                                notice = if (availableHomes.any { it.optString("id") == propertyId }) {
                                    "Random group budget, amounts, notes, and a real loaded listing ID are ready. Save each item with its Add or Share button."
                                } else {
                                    "Random group details are ready. No listing ID is available, so the sample home ID cannot be submitted."
                                }
                            }, modifier = Modifier.fillMaxWidth()) { Text("Fill all fields with a random example") }
                            OutlinedTextField(inviteId, { inviteId = it }, Modifier.fillMaxWidth(), label = { Text("Invite account ID") }, singleLine = true)
                            OutlinedButton(onClick = { send("collaboration/groups/$selectedGroup/invitations", body = JSONObject().put("user_id", inviteId.trim()), message = "Invitation sent."); inviteId = "" }, enabled = inviteId.isNotBlank()) { Text("Invite member") }
                            OutlinedTextField(shareSearchName, { shareSearchName = it }, Modifier.fillMaxWidth(), label = { Text("Shared search name") }, singleLine = true)
                            OutlinedTextField(sharedSearchQuery, { sharedSearchQuery = it }, Modifier.fillMaxWidth(), label = { Text("Area or keyword") }, singleLine = true)
                            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                OutlinedTextField(sharedRentMin, { sharedRentMin = it }, Modifier.weight(1f), label = { Text("Min KES") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                                OutlinedTextField(sharedRentMax, { sharedRentMax = it }, Modifier.weight(1f), label = { Text("Max KES") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                            }
                            Button(onClick = {
                                val filters = JSONObject()
                                sharedSearchQuery.trim().takeIf(String::isNotBlank)?.let { filters.put("query", it) }
                                sharedRentMin.toIntOrNull()?.let { filters.put("rent_min", it) }
                                sharedRentMax.toIntOrNull()?.let { filters.put("rent_max", it) }
                                send("collaboration/groups/$selectedGroup/searches", body = JSONObject().put("name", shareSearchName.trim()).put("filters", filters), message = "Search shared.")
                                shareSearchName = ""; sharedSearchQuery = ""; sharedRentMin = ""; sharedRentMax = ""
                            }, enabled = shareSearchName.isNotBlank() && (sharedRentMin.toIntOrNull() == null || sharedRentMax.toIntOrNull() == null || sharedRentMin.toInt() <= sharedRentMax.toInt())) { Text("Share search") }
                            OutlinedTextField(propertyId, { propertyId = it }, Modifier.fillMaxWidth(), label = { Text("Property ID to share") }, singleLine = true)
                            OutlinedButton(onClick = { send("collaboration/groups/$selectedGroup/properties", body = JSONObject().put("property_id", propertyId.trim()), message = "Home added to group.") }, enabled = availableHomes.any { it.optString("id") == propertyId.trim() }) { Text("Add home") }
                            OutlinedTextField(taskTitle, { taskTitle = it }, Modifier.fillMaxWidth(), label = { Text("Moving task") }, singleLine = true)
                            OutlinedButton(onClick = { send("collaboration/groups/$selectedGroup/tasks", body = JSONObject().put("title", taskTitle.trim()), message = "Task added to your group."); taskTitle = "" }, enabled = taskTitle.isNotBlank()) { Text("Add task") }
                            OutlinedTextField(goalTitle, { goalTitle = it }, Modifier.fillMaxWidth(), label = { Text("Moving goal") }, singleLine = true)
                            HomeScoutDateField(goalDate, { goalDate = it }, "Target date · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                            OutlinedTextField(goalAmount, { goalAmount = it }, Modifier.fillMaxWidth(), label = { Text("Target KES amount (optional)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                            if (goalAmount.isNotBlank()) Row(verticalAlignment = Alignment.CenterVertically) { Switch(shareGoalAmount, { shareGoalAmount = it }); Text("Share amount with the group", Modifier.padding(start = 8.dp)) }
                            OutlinedButton(onClick = {
                                val body = JSONObject().put("title", goalTitle.trim()).put("share_amount_with_members", shareGoalAmount)
                                goalDate.trim().takeIf(String::isNotBlank)?.let { body.put("target_date", it) }
                                goalAmount.toDoubleOrNull()?.let { body.put("target_amount", it) }
                                send("collaboration/groups/$selectedGroup/moving-goals", body = body, message = "Moving goal added.")
                                goalTitle = ""; goalDate = ""; goalAmount = ""; shareGoalAmount = false
                            }, enabled = goalTitle.isNotBlank() && (goalAmount.isBlank() || goalAmount.toDoubleOrNull() != null && shareGoalAmount) && (goalDate.isBlank() || runCatching { java.time.LocalDate.parse(goalDate) }.isSuccess)) { Text("Add moving goal") }
                            if (sharedProperties.size >= 2) {
                                OutlinedButton(onClick = {
                                    val ids = JSONArray().apply { sharedProperties.take(5).forEach { put(it.optJSONObject("property")?.optString("property_id")) } }
                                    send("collaboration/groups/$selectedGroup/comparisons", body = JSONObject().put("name", "Group home comparison").put("property_ids", ids), message = "Group comparison saved.")
                                }) { Text("Compare shared homes (${sharedProperties.size.coerceAtMost(5)})") }
                            }
                        } }
                        items(sharedProperties) { row ->
                            val property = row.optJSONObject("property") ?: JSONObject()
                            Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                                InfoCard(property.optString("title", "Shared home"), "${property.optString("county")} · ${property.optString("town")} · KSh ${property.optString("rent_amount_kes")}", "Votes: ${row.optJSONArray("votes").jsonObjects().joinToString { it.optString("vote") }}\nComments: ${row.optJSONArray("comments").jsonObjects().joinToString { it.optString("body") }}")
                                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                                    OutlinedButton(onClick = { send("collaboration/groups/$selectedGroup/properties/${row.optString("id")}/vote", "PUT", JSONObject().put("vote", "interested"), "Your vote is shared.") }) { Text("Interested") }
                                    OutlinedButton(onClick = { send("collaboration/groups/$selectedGroup/properties/${row.optString("id")}/vote", "PUT", JSONObject().put("vote", "unsure"), "Your vote is shared.") }) { Text("Unsure") }
                                }
                                OutlinedTextField(sharedComment, { sharedComment = it }, Modifier.fillMaxWidth(), label = { Text("Add a group comment") }, maxLines = 2)
                                OutlinedButton(onClick = { send("collaboration/groups/$selectedGroup/properties/${row.optString("id")}/comments", body = JSONObject().put("body", sharedComment.trim()), message = "Comment shared with the group."); sharedComment = "" }, enabled = sharedComment.isNotBlank()) { Text("Post comment") }
                            }
                        }
                        items(sharedSearches) { row -> InfoCard(row.optString("name"), "Shared search", row.optJSONObject("filters")?.toString().orEmpty()) }
                        items(sharedTasks) { row ->
                            InfoCard(row.optString("title"), row.optString("details"), "${row.optString("status")} · due ${row.optString("due_at", "not set")}", action = if (row.optString("status") == "open") "Mark complete" else null, onAction = {
                                send("collaboration/groups/$selectedGroup/tasks/${row.optString("id")}", "PATCH", JSONObject().put("status", "done"), "Task marked complete.")
                            })
                        }
                        items(sharedGroupComparisons) { row ->
                            val titles = row.optJSONArray("items").jsonObjects().joinToString { "${it.optString("title")} (KSh ${it.optString("rent_amount_kes")})" }
                            InfoCard(row.optString("name"), titles, "Shared with active group members.")
                        }
                        items(goals) { row ->
                            val anotherOwner = row.optString("owner_user_id") != userId
                            val ownerShared = row.optBoolean("amount_shared_by_owner")
                            val viewerConsented = row.optBoolean("viewer_has_consented")
                            val consentAction = if (anotherOwner && ownerShared) if (viewerConsented) "Revoke amount consent" else "Consent to view amount" else null
                            InfoCard(row.optString("title"), row.optString("target_amount_kes").takeIf(String::isNotBlank)?.let { "KSh $it" } ?: "Amount hidden unless the owner shares it and you consent.", row.optString("target_date"), action = consentAction, onAction = {
                                send("collaboration/groups/$selectedGroup/moving-goals/${row.optString("id")}/financial-consent", "PUT", JSONObject().put("consent_to_view_shared_amounts", !viewerConsented), message = if (viewerConsented) "Consent revoked." else "Your consent is recorded.")
                            })
                        }
                        if (selectedGroupRecord?.optString("created_by_user_id") == userId) {
                            items(selectedGroupRecord.optJSONArray("members").jsonObjects().filter { it.optString("user_id") != userId && it.optString("status") in listOf("active", "invited") }) { member ->
                                InfoCard("Group member", "${member.optString("role")} · ${member.optString("status")}", action = "Remove access", onAction = {
                                    send("collaboration/groups/$selectedGroup/members/${member.optString("user_id")}", "DELETE", message = "Group access revoked.")
                                })
                            }
                        }
                    }
                }
                "Journal" -> {
                    val publicHomes = availableHomes.filterNot { it.optBoolean("is_demo") }
                    item { Intro("Viewing journal", "Journal notes are encrypted and private unless you explicitly share them.") }
                    item {
                        InfoCard(
                            "Random journal example",
                            "Each tap fills a new title, detailed notes, pros, cons, rating, checklist, and an available property ID when one exists.",
                            "Tap Save privately to keep the filled example in your account. A demo-only property can only be previewed, never saved as a real viewing record.",
                        )
                    }
                    item {
                            FormCard("New private entry") {
                            OutlinedButton(onClick = {
                                val example = publicHomes.randomOrNull()
                                val area = listOf("Kilimani", "Westlands", "Ruaka", "Ruiru").random()
                                propertyId = example?.optString("id")?.takeIf(String::isNotBlank)
                                    ?: "DEMO-PROPERTY-$area-${kotlin.random.Random.nextInt(100, 999)}"
                                journalViewingId = viewings.firstOrNull {
                                    it.optString("property_id") == propertyId && it.optString("status") in listOf("confirmed", "completed", "cancelled")
                                }?.optString("id").orEmpty()
                                journalExampleMode = example == null
                                journalTitle = "DEMO · $area viewing notes"
                                journalNotes = listOf(
                                    "DEMO · Check water pressure, natural light, evening noise, and phone signal before deciding.",
                                    "DEMO · Ask about the deposit, utility setup, visitor rules, and how maintenance requests are handled.",
                                    "DEMO · Confirm the commute at peak time, security arrangements, and whether the listed rent includes service charges.",
                                ).random()
                                journalPros = listOf("Bright living room, good storage", "Quiet street, practical kitchen", "Close to shops, secure entry").random()
                                journalCons = listOf("Confirm parking details", "Check water storage", "Ask about service charges").random()
                                journalRating = listOf("3", "4", "5").random()
                                waterChecked = kotlin.random.Random.nextBoolean()
                                powerChecked = kotlin.random.Random.nextBoolean()
                                securityChecked = kotlin.random.Random.nextBoolean()
                                notice = if (example == null) {
                                    "Random fields filled with a demo-only property ID. Preview stays on this screen because no public non-demo listing is available to save against."
                                } else {
                                    "Random fields filled with the real listing ID. Tap Save privately to add this clearly labeled demo note to your account."
                                }
                            }) { Text("Fill a new random example") }
                            if (journalExampleMode) Text("DEMO ID · $propertyId · display only; no record will be sent to HomeScout.", color = MaterialTheme.colorScheme.tertiary, style = MaterialTheme.typography.bodySmall)
                            else Text("Your real listing ID is filled from the available homes you loaded.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            OutlinedTextField(propertyId, { propertyId = it; journalExampleMode = false }, Modifier.fillMaxWidth(), label = { Text("Property ID") }, singleLine = true)
                            OutlinedTextField(journalViewingId, { journalViewingId = it }, Modifier.fillMaxWidth(), label = { Text("Confirmed viewing ID (optional · actual viewing only)") }, supportingText = { Text("Filled only when a confirmed viewing exists for this property.") }, singleLine = true)
                            OutlinedTextField(journalTitle, { journalTitle = it }, Modifier.fillMaxWidth(), label = { Text("Title") }, singleLine = true)
                            OutlinedTextField(journalNotes, { journalNotes = it }, Modifier.fillMaxWidth(), label = { Text("Notes") }, minLines = 3)
                            OutlinedTextField(journalPros, { journalPros = it }, Modifier.fillMaxWidth(), label = { Text("Pros (comma separated)") })
                            OutlinedTextField(journalCons, { journalCons = it }, Modifier.fillMaxWidth(), label = { Text("Cons (comma separated)") })
                            OutlinedTextField(journalRating, { journalRating = it }, Modifier.fillMaxWidth(), label = { Text("Rating from 1 to 5") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                            Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(waterChecked, { waterChecked = it }); Text("Checked water") }
                            Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(powerChecked, { powerChecked = it }); Text("Checked electricity") }
                            Row(verticalAlignment = Alignment.CenterVertically) { Checkbox(securityChecked, { securityChecked = it }); Text("Checked security") }
                            Text("Attach private photos (up to ten)", style = MaterialTheme.typography.labelLarge)
                            privateDocuments.filter { it.optString("content_type").startsWith("image/") }.take(12).forEach { document ->
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Checkbox(checked = document.optString("id") in selectedPhotoDocumentIds, onCheckedChange = { checked ->
                                        val id = document.optString("id")
                                        if (checked && selectedPhotoDocumentIds.size < 10 && id !in selectedPhotoDocumentIds) selectedPhotoDocumentIds.add(id)
                                        if (!checked) selectedPhotoDocumentIds.remove(id)
                                    })
                                    Text(document.optString("original_filename", "Private photo"))
                                }
                            }
                            if (journalExampleMode) {
                                InfoCard("Local demo preview", "$journalTitle\n$journalNotes\nPros: $journalPros\nCons: $journalCons\nRating: $journalRating / 5", "This remains a preview until you choose a real public listing ID.")
                            }
                            Button(onClick = {
                                if (journalExampleMode) {
                                    notice = "This demo journal is preview-only because it has no real public property ID. Choose a live listing to save a private journal entry."
                                } else {
                                val checklist = JSONObject().put("water_checked", waterChecked).put("electricity_checked", powerChecked).put("security_checked", securityChecked)
                                val body = JSONObject()
                                    .put("property_id", propertyId.trim())
                                    .put("title", journalTitle.trim())
                                    .put("notes", journalNotes.trim())
                                    .put("pros", JSONArray().apply { journalPros.split(',').map(String::trim).filter(String::isNotBlank).forEach(::put) })
                                    .put("cons", JSONArray().apply { journalCons.split(',').map(String::trim).filter(String::isNotBlank).forEach(::put) })
                                    .put("checklist", checklist)
                                    .put("photo_document_ids", JSONArray().apply { selectedPhotoDocumentIds.forEach(::put) })
                                journalRating.toIntOrNull()?.let { body.put("rating", it) }
                                journalViewingId.trim().takeIf(String::isNotBlank)?.let { body.put("viewing_id", it) }
                                send("viewings/journals", body = body, message = "Private journal saved.", onSuccess = {
                                    journalTitle = ""; journalNotes = ""; journalPros = ""; journalCons = ""; journalRating = ""; selectedPhotoDocumentIds.clear(); journalViewingId = ""; journalExampleMode = false
                                })
                                }
                            }, enabled = (journalExampleMode || publicHomes.any { it.optString("id") == propertyId.trim() }) && journalTitle.isNotBlank()) { Text(if (journalExampleMode) "Preview demo entry" else "Save privately") }
                        }
                    }
                    items(journals) { row ->
                        Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            InfoCard(row.optString("title"), row.optString("notes"), row.optString("property_title"))
                            if (row.optBoolean("can_edit")) {
                                OutlinedTextField(shareTarget, { shareTarget = it }, Modifier.fillMaxWidth(), label = { Text("Account ID for sharing or revoking") }, singleLine = true)
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedButton(onClick = { send("viewings/journals/${row.optString("id")}/shares", "PUT", JSONObject().put("recipient_user_id", shareTarget.trim()), "Journal shared.") }, enabled = shareTarget.isNotBlank()) { Text("Share") }
                                    OutlinedButton(onClick = { send("viewings/journals/${row.optString("id")}/shares/${shareTarget.trim()}", "DELETE", message = "Journal access revoked.") }, enabled = shareTarget.isNotBlank()) { Text("Revoke") }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun Intro(title: String, detail: String) {
    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
        Text(detail, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun MessageCard(
    title: String,
    body: String,
    supporting: String,
    onReport: (() -> Unit)?,
    onBlock: (() -> Unit)?,
    blockLabel: String,
) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(body)
            Text(supporting, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            if (onReport != null || onBlock != null) {
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    if (onReport != null) OutlinedButton(onClick = onReport) { Text("Report") }
                    if (onBlock != null) OutlinedButton(onClick = onBlock) { Text(blockLabel) }
                }
            }
        }
    }
}

@Composable
private fun InfoCard(title: String, body: String = "", supporting: String = "", action: String? = null, onAction: () -> Unit = {}) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            if (body.isNotBlank() && body != "null") Text(body)
            if (supporting.isNotBlank() && supporting != "null") Text(supporting, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            if (action != null) OutlinedButton(onClick = onAction) { Text(action) }
        }
    }
}

@Composable
private fun FormCard(title: String, content: @Composable () -> Unit) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            content()
        }
    }
}

private fun JSONArray?.jsonObjects(): List<JSONObject> = buildList {
    if (this@jsonObjects == null) return@buildList
    for (index in 0 until this@jsonObjects.length()) this@jsonObjects.optJSONObject(index)?.let(::add)
}

private fun JSONArray?.jsonStrings(): List<String> = buildList {
    if (this@jsonStrings == null) return@buildList
    for (index in 0 until this@jsonStrings.length()) this@jsonStrings.optString(index).takeIf(String::isNotBlank)?.let(::add)
}

private fun defaultViewingTime(): String {
    val dayOffset = kotlin.random.Random.nextInt(1, 15)
    val hour = listOf(10, 12, 14, 16).random()
    return ZonedDateTime.now(ZoneId.of("Africa/Nairobi"))
        .plusDays(dayOffset.toLong()).withHour(hour).withMinute(0).withSecond(0).withNano(0)
        .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
}

private fun formatDemoDateTime(value: String): String = runCatching {
    ZonedDateTime.parse(value).withZoneSameInstant(ZoneId.of("Africa/Nairobi"))
        .format(DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm"))
}.recoverCatching {
    java.time.OffsetDateTime.parse(value).atZoneSameInstant(ZoneId.of("Africa/Nairobi"))
        .format(DateTimeFormatter.ofPattern("dd-MM-yyyy HH:mm"))
}.getOrDefault(value)
