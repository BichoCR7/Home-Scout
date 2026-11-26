package ke.co.homescout.features.profile

import android.content.Intent
import android.graphics.BitmapFactory
import android.net.Uri
import android.provider.OpenableColumns
import android.util.Base64
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.ColumnScope
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.clickable
import androidx.compose.foundation.Image
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AdminPanelSettings
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Download
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.FolderOpen
import androidx.compose.material.icons.filled.HelpOutline
import androidx.compose.material.icons.filled.History
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Logout
import androidx.compose.material.icons.filled.NotificationsNone
import androidx.compose.material.icons.filled.PersonOutline
import androidx.compose.material.icons.filled.ReceiptLong
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.Settings
import androidx.compose.material.icons.filled.MoreVert
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.FilterChip
import androidx.compose.material3.HorizontalDivider
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
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.draw.clip
import androidx.compose.ui.semantics.Role
import androidx.compose.ui.graphics.ImageBitmap
import androidx.compose.ui.graphics.asImageBitmap
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.core.content.FileProvider
import ke.co.homescout.data.remote.AuthApiException
import ke.co.homescout.data.remote.PersonalHubApi
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.components.HomeScoutDateField
import ke.co.homescout.ui.components.ProfileAvatar
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.File
import java.time.ZoneId
import java.time.OffsetDateTime
import java.time.LocalDate
import java.time.LocalTime
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

data class HubAction(val key: String, val title: String, val detail: String)

private val commonActions = listOf(
    HubAction("profile", "My profile", "Personal details, role and verification"),
    HubAction("saved", "Saved items", "Homes, searches, areas and collections"),
    HubAction("activity", "My activity", "Your private HomeScout history"),
    HubAction("schedule", "My schedule", "Tasks, reminders and viewing plans"),
    HubAction("collaboration", "Messages & shared plans", "Viewings, comparisons and roommate search"),
    HubAction("notifications", "Notifications", "In-app updates and read status"),
    HubAction("records", "Orders & records", "Your own KES notes and records"),
    HubAction("documents", "My documents", "Private files stored in your account"),
    HubAction("trust-safety", "Trust & safety", "Manual verification, safe viewings and reports"),
    HubAction("support", "Help & support", "Search guidance or contact support"),
    HubAction("settings", "Settings", "Appearance, privacy and account controls"),
    HubAction("about", "About HomeScout", "Our Kenya-first approach"),
    HubAction("assistant", "HomeScout Assistant", "Housing help with privacy controls"),
    HubAction("logout", "Log out", "End your HomeScout session"),
)

@Composable
fun PersonalHubScreen(
    section: String,
    collectionId: String? = null,
    accessToken: String?,
    onBack: () -> Unit,
    onNavigate: (String) -> Unit,
    onAppearanceChange: (String) -> Unit,
    onLargerTextChange: (Boolean) -> Unit,
    onSignOut: () -> Unit,
) {
    val context = LocalContext.current
    val api = remember { PersonalHubApi() }
    val scope = rememberCoroutineScope()
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var notice by remember { mutableStateOf<String?>(null) }
    var profile by remember { mutableStateOf(JSONObject()) }
    var profilePhoto by remember { mutableStateOf<ImageBitmap?>(null) }
    var selectedCollection by remember { mutableStateOf(JSONObject()) }
    var collectionShareIds by remember { mutableStateOf(emptyList<String>()) }
    var preferences by remember { mutableStateOf(JSONObject()) }
    var rows by remember { mutableStateOf(emptyList<JSONObject>()) }
    var savedHomes by remember { mutableStateOf(emptyList<JSONObject>()) }
    var savedSearches by remember { mutableStateOf(emptyList<JSONObject>()) }
    var searchHistory by remember { mutableStateOf(emptyList<JSONObject>()) }
    var collections by remember { mutableStateOf(emptyList<JSONObject>()) }
    var helpArticles by remember { mutableStateOf(emptyList<JSONObject>()) }
    var allNotifications by remember { mutableStateOf(emptyList<JSONObject>()) }
    var filter by rememberSaveable(section) { mutableStateOf("all") }
    var dateFilter by rememberSaveable(section) { mutableStateOf("all") }
    var search by rememberSaveable(section) { mutableStateOf("") }
    var dialog by remember { mutableStateOf<String?>(null) }
    var draftTitle by rememberSaveable(section) { mutableStateOf("") }
    var draftBody by rememberSaveable(section) { mutableStateOf("") }
    var draftAmount by rememberSaveable(section) { mutableStateOf("") }
    var passwordDraft by rememberSaveable { mutableStateOf("") }
    var confirmationDraft by rememberSaveable { mutableStateOf("") }
    var editingCollectionId by rememberSaveable { mutableStateOf("") }
    var editingTicketId by rememberSaveable { mutableStateOf("") }
    var draftCategory by rememberSaveable(section) { mutableStateOf("other") }
    var documentCategory by rememberSaveable { mutableStateOf("other") }
    var savedKind by rememberSaveable(section) { mutableStateOf("neighbourhood") }
    var selectedCollectionId by rememberSaveable(section) { mutableStateOf("") }
    var scheduleDate by rememberSaveable(section) {
        mutableStateOf(LocalDate.now(ZoneId.of("Africa/Nairobi")).plusDays(1).toString())
    }
    var scheduleTime by rememberSaveable(section) { mutableStateOf("10:00") }
    var reminderMinutes by rememberSaveable(section) { mutableStateOf("") }

    suspend fun load() {
        if (accessToken == null) return
        loading = true
        error = null
        try {
            withContext(Dispatchers.IO) {
                when (section) {
                    "hub" -> profile = api.getObject("hub/profile", accessToken)
                    "profile" -> {
                        profile = api.getObject("hub/profile", accessToken)
                        profilePhoto = if (profile.optBoolean("profile_photo_available")) {
                            val bytes = api.download("hub/profile/photo", accessToken)
                            BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
                        } else null
                    }
                    "settings" -> preferences = api.getObject("hub/preferences", accessToken)
                    "saved" -> {
                        rows = api.getArray("hub/saved", accessToken).objects()
                        collections = api.getArray("hub/collections", accessToken).objects()
                        savedHomes = api.getObject("marketplace/saved", accessToken)
                            .optJSONArray("items").objects()
                        savedSearches = api.getArray("marketplace/alerts", accessToken).objects()
                        searchHistory = api.getArray("marketplace/search-history", accessToken).objects()
                    }
                    "collection" -> {
                        profile = api.getObject("hub/profile", accessToken)
                        selectedCollection = api.getObject("hub/collections/$collectionId", accessToken)
                        rows = api.getArray("hub/collections/$collectionId/items", accessToken).objects()
                    }
                    "activity" -> {
                        val now = ZonedDateTime.now(ZoneId.of("Africa/Nairobi"))
                        val days = when (dateFilter) {
                            "today" -> 1L
                            "7 days" -> 7L
                            "30 days" -> 30L
                            else -> null
                        }
                        val query = buildList {
                            if (filter != "all") add("event_type=${PersonalHubApi.query(filter)}")
                            if (days != null) {
                                add("after=${PersonalHubApi.query(now.minusDays(days).toOffsetDateTime().toString())}")
                                add("before=${PersonalHubApi.query(now.toOffsetDateTime().toString())}")
                            }
                        }.joinToString("&")
                        val path = "hub/activity" + if (query.isBlank()) "" else "?$query"
                        rows = api.getArray(path, accessToken).objects()
                    }
                    "schedule" -> {
                        val zone = ZoneId.of("Africa/Nairobi")
                        val today = ZonedDateTime.now(zone).toLocalDate()
                        val begin = when (filter) {
                            "week" -> today.minusDays(today.dayOfWeek.value - 1L).atStartOfDay(zone)
                            "month" -> today.withDayOfMonth(1).atStartOfDay(zone)
                            else -> today.atStartOfDay(zone)
                        }
                        val end = when (filter) {
                            "week" -> begin.plusWeeks(1)
                            "month" -> begin.plusMonths(1)
                            else -> begin.plusDays(1)
                        }
                        val path = "hub/schedule?after=${PersonalHubApi.query(begin.toOffsetDateTime().toString())}" +
                            "&before=${PersonalHubApi.query(end.toOffsetDateTime().toString())}"
                        rows = api.getArray(path, accessToken).objects()
                    }
                    "notifications" -> {
                        allNotifications = api.getArray("hub/notifications", accessToken).objects()
                        rows = when (filter) {
                            "unread" -> allNotifications.filter { it.isNull("read_at") }
                            "all" -> allNotifications
                            else -> allNotifications.filter { it.optString("category") == filter }
                        }
                    }
                    "records" -> {
                        profile = api.getObject("hub/profile", accessToken)
                        rows = api.getArray("hub/records", accessToken).objects()
                    }
                    "documents" -> rows = api.getArray("hub/documents", accessToken).objects()
                    "support" -> {
                        rows = api.getArray("hub/support/tickets", accessToken).objects()
                        val q = if (search.isBlank()) "" else "?q=${PersonalHubApi.query(search)}"
                        helpArticles = api.getArray("hub/support/articles$q", accessToken).objects()
                    }
                }
            }
        } catch (failure: Exception) {
            error = failure.message ?: "The HomeScout service could not load this section."
        } finally {
            loading = false
        }
    }

    fun submit(path: String, method: String = "POST", body: JSONObject? = null, successText: String) {
        val token = accessToken ?: run { error = "Sign in to use your personal hub."; return }
        scope.launch {
            loading = true
            error = null
            try {
                withContext(Dispatchers.IO) { api.send(path, method, token, body) }
                notice = successText
                load()
            } catch (failure: Exception) {
                error = failure.message ?: "That change could not be saved."
            } finally {
                loading = false
            }
        }
    }

    val documentPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null && accessToken != null) {
            scope.launch {
                loading = true
                try {
                    val filename = contentName(context, uri)
                    val bytes = withContext(Dispatchers.IO) { readLimited(context, uri, 15_728_640) }
                    withContext(Dispatchers.IO) {
                        api.upload("hub/documents?category=$documentCategory&filename=${PersonalHubApi.query(filename)}", accessToken, bytes)
                    }
                    notice = "The document was added to your private files."
                    load()
                } catch (failure: Exception) {
                    error = failure.message ?: "The document could not be uploaded."
                } finally {
                    loading = false
                }
            }
        }
    }
    val photoPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        if (uri != null && accessToken != null) {
            scope.launch {
                loading = true
                try {
                    val bytes = withContext(Dispatchers.IO) { readLimited(context, uri, 5_242_880) }
                    withContext(Dispatchers.IO) { api.upload("hub/profile/photo", accessToken, bytes) }
                    profilePhoto = withContext(Dispatchers.IO) {
                        BitmapFactory.decodeByteArray(bytes, 0, bytes.size)?.asImageBitmap()
                    }
                    profile = withContext(Dispatchers.IO) { api.getObject("hub/profile", accessToken) }
                    notice = "Profile photo updated."
                } catch (failure: Exception) {
                    error = failure.message ?: "The profile photo could not be updated."
                } finally {
                    loading = false
                }
            }
        }
    }

    LaunchedEffect(section, accessToken, filter, dateFilter, search) { load() }

    val title = when (section) {
        "hub" -> "Your HomeScout hub"
        "collection" -> "Saved collection"
        "profile" -> "My profile"
        "saved" -> "Saved items"
        "activity" -> "My activity"
        "schedule" -> "My schedule"
        "notifications" -> "Notifications"
        "records" -> "Orders & records"
        "documents" -> "My documents"
        "support" -> "Help & support"
        "settings" -> "Settings"
        "assistant" -> "HomeScout Assistant"
        "logout" -> "Log out"
        else -> "About HomeScout"
    }
    val subtitle = when (section) {
        "hub" -> "Your account, home search and personal records in one place."
        "collection" -> selectedCollection.optString("name").ifBlank { "Shortlist items you can access." }
        "saved" -> "Your saves stay private unless you explicitly share a collection."
        "schedule" -> "Plans use East Africa Time. Reminder times are stored; delivery is not scheduled in this build."
        "notifications" -> "These are in-app updates. Email and push delivery are not configured."
        "records" -> "Personal notes only. HomeScout does not process or confirm these payments."
        "documents" -> "Only your signed-in account can access uploaded files."
        "about" -> "A Kenya-first guide to finding your next place."
        else -> "Manage this part of your HomeScout account."
    }

    Column(Modifier.fillMaxSize(), horizontalAlignment = Alignment.CenterHorizontally) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) { Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back") }
            Column(Modifier.weight(1f)) {
                Text(title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                Text(subtitle, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            IconButton(onClick = { scope.launch { load() } }, enabled = !loading) {
                Icon(Icons.Filled.Refresh, contentDescription = "Refresh")
            }
        }
        HorizontalDivider()
        when {
            accessToken == null -> HubMessage("Sign in to open your HomeScout hub.", error = true)
            loading && rows.isEmpty() && section !in setOf("profile", "settings", "hub") ->
                CircularProgressIndicator(Modifier.padding(32.dp))
            else -> HubSectionContent(
                section = section,
                profile = profile,
                profilePhoto = profilePhoto,
                preferences = preferences,
                rows = rows,
                savedHomes = savedHomes,
                savedSearches = savedSearches,
                searchHistory = searchHistory,
                collections = collections,
                helpArticles = helpArticles,
                selectedCollection = selectedCollection,
                draftCategory = draftCategory,
                recordCategories = recordCategories(profile.optJSONArray("roles").strings()),
                documentCategory = documentCategory,
                savedKind = savedKind,
                selectedCollectionId = selectedCollectionId,
                ownCollections = collections.filter { it.optBoolean("can_edit") },
                notificationCategories = allNotifications.map { it.optString("category") }
                    .filter(String::isNotBlank).distinct(),
                filter = filter,
                dateFilter = dateFilter,
                search = search,
                loading = loading,
                error = error,
                notice = notice,
                onFilterChange = { filter = it },
                onDateFilterChange = { dateFilter = it },
                onSearchChange = { search = it },
                onNavigate = onNavigate,
                onOpenDialog = { type ->
                    dialog = type
                    if (type == "ticket") draftCategory = "technical"
                    if (type == "record") draftCategory = "expense"
                    if (type == "saved") {
                        savedKind = "neighbourhood"
                        selectedCollectionId = ""
                    }
                },
                onCollectionAction = { action, row ->
                    editingCollectionId = row.optString("id")
                    draftTitle = row.optString("name")
                    draftBody = if (action == "collection-edit") row.optString("description") else ""
                    collectionShareIds = row.optJSONArray("shared_with_user_ids").strings()
                    dialog = action
                },
                onTicketReply = { row ->
                    editingTicketId = row.optString("id")
                    draftTitle = row.optString("subject")
                    draftBody = ""
                    dialog = "ticket-reply"
                },
                onDraftCategoryChange = { draftCategory = it },
                onDocumentCategoryChange = { documentCategory = it },
                onSavedKindChange = { savedKind = it },
                onCollectionSelect = { selectedCollectionId = it },
                onDelete = { path -> submit(path, "DELETE", successText = "Removed from your HomeScout account.") },
                onSaveSearchAlert = { filters ->
                    submit(
                        "marketplace/alerts",
                        "POST",
                        JSONObject().put("filters", filters),
                        "Saved search criteria recorded. Alert delivery is not active in this build."
                    )
                },
                onOpenSearch = { filters ->
                    val query = filters.optString("query")
                    val encodedFilters = Base64.encodeToString(
                        filters.toString().toByteArray(Charsets.UTF_8),
                        Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
                    )
                    onNavigate("discover?query=${PersonalHubApi.query(query)}&savedFilters=$encodedFilters")
                },
                onReadAll = { submit("hub/notifications/read-all", successText = "Notifications marked as read.") },
                onRead = { id -> submit("hub/notifications/$id/read", successText = "Notification marked as read.") },
                onDismissNotification = { id -> submit("hub/notifications/$id/dismiss", "POST", successText = "Notification dismissed.") },
                onDone = { id -> submit("hub/schedule/$id", "PATCH", JSONObject().put("status", "done"), "Schedule item marked done.") },
                onReschedule = { row ->
                    runCatching {
                        val start = OffsetDateTime.parse(row.optString("starts_at"))
                        val body = JSONObject().put("starts_at", start.plusDays(1).toString())
                        row.optString("ends_at").takeIf(String::isNotBlank)?.let {
                            body.put("ends_at", OffsetDateTime.parse(it).plusDays(1).toString())
                        }
                        submit("hub/schedule/${row.optString("id")}", "PATCH", body, "Schedule item moved one day later.")
                    }.onFailure { failure -> error = failure.message ?: "This item could not be rescheduled." }
                },
                onSaveProfile = { body -> submit("hub/profile", "PATCH", body, "Profile updated.") },
                onSavePreferences = { body ->
                    val roleCode = body.optString("active_role_code")
                    if (roleCode.isNotBlank()) {
                        submit("hub/profile/active-role", "PUT", JSONObject().put("role_code", roleCode), "Active profile changed.")
                    } else {
                        submit("hub/preferences", "PATCH", body, "Preferences saved.")
                    }
                    body.optString("appearance").takeIf(String::isNotBlank)?.let(onAppearanceChange)
                    body.optJSONObject("accessibility_preferences")?.let {
                        onLargerTextChange(it.optBoolean("larger_text"))
                    }
                },
                onExport = {
                    val token = checkNotNull(accessToken)
                    scope.launch {
                        try {
                            val json = withContext(Dispatchers.IO) { api.raw("hub/account/export", token) }
                            val intent = Intent(Intent.ACTION_SEND).setType("application/json")
                                .putExtra(Intent.EXTRA_SUBJECT, "HomeScout account data export")
                                .putExtra(Intent.EXTRA_TEXT, json)
                            context.startActivity(Intent.createChooser(intent, "Share your HomeScout export"))
                        } catch (failure: Exception) { error = failure.message }
                    }
                },
                onDocumentPick = { documentPicker.launch("*/*") },
                onPhotoPick = { photoPicker.launch("image/*") },
                onDownload = { row ->
                    val token = checkNotNull(accessToken)
                    scope.launch {
                        loading = true
                        try {
                            val bytes = withContext(Dispatchers.IO) {
                                api.download("hub/documents/${row.optString("id")}/download", token)
                            }
                            val folder = File(context.cacheDir, "shared-documents").apply { mkdirs() }
                            val safeName = row.optString("original_filename").replace(Regex("[^A-Za-z0-9._ -]"), "_")
                            val localFile = File(folder, safeName.ifBlank { "homescout-document" })
                            withContext(Dispatchers.IO) { localFile.writeBytes(bytes) }
                            val uri = FileProvider.getUriForFile(context, "${context.packageName}.files", localFile)
                            val view = Intent(Intent.ACTION_VIEW).setDataAndType(uri, row.optString("content_type"))
                                .addFlags(Intent.FLAG_GRANT_READ_URI_PERMISSION)
                            context.startActivity(Intent.createChooser(view, "Open private document"))
                        } catch (failure: Exception) {
                            error = failure.message ?: "The file could not be opened."
                        } finally { loading = false }
                    }
                },
                onAppearanceChange = { onAppearanceChange(it) },
                onLargerTextChange = onLargerTextChange
            )
        }
        if (error != null) HubMessage(error.orEmpty(), error = true)
        if (notice != null) HubMessage(notice.orEmpty())
    }

    if (dialog != null) {
        PersonalHubDialog(
            type = dialog.orEmpty(),
            title = draftTitle,
            body = draftBody,
            amount = draftAmount,
            password = passwordDraft,
            confirmation = confirmationDraft,
            savedKind = savedKind,
            selectedCollectionId = selectedCollectionId,
            collections = collections.filter { it.optBoolean("can_edit") },
            collectionShareIds = collectionShareIds,
            category = draftCategory,
            recordCategories = recordCategories(profile.optJSONArray("roles").strings()),
            scheduleDate = scheduleDate,
            scheduleTime = scheduleTime,
            reminderMinutes = reminderMinutes,
            onTitleChange = { draftTitle = it },
            onBodyChange = { draftBody = it },
            onAmountChange = { draftAmount = it },
            onSavedKindChange = { savedKind = it },
            onCollectionSelect = { selectedCollectionId = it },
            onCategoryChange = { draftCategory = it },
            onScheduleDateChange = { scheduleDate = it },
            onScheduleTimeChange = { scheduleTime = it },
            onReminderChange = { reminderMinutes = it },
            onPasswordChange = { passwordDraft = it },
            onConfirmationChange = { confirmationDraft = it },
            onDismiss = { dialog = null },
            onConfirm = { type ->
                val token = accessToken
                if (token != null) {
                    val action = when (type) {
                        "task", "viewing" -> {
                            val starts = LocalDate.parse(scheduleDate).atTime(LocalTime.parse(scheduleTime))
                                .atZone(ZoneId.of("Africa/Nairobi"))
                            "hub/schedule" to JSONObject()
                                .put("title", draftTitle)
                                .put("category", if (type == "viewing") "viewing" else "task")
                                .put("starts_at", starts.toOffsetDateTime().toString())
                                .put("timezone", "Africa/Nairobi")
                                .put("reminder_minutes", reminderMinutes.toIntOrNull() ?: JSONObject.NULL)
                        }
                        "record" -> "hub/records" to JSONObject()
                            .put("title", draftTitle).put("category", draftCategory)
                            .put("amount", draftAmount.toBigDecimalOrNull()?.toPlainString() ?: JSONObject.NULL)
                            .put("record_date", ZonedDateTime.now(ZoneId.of("Africa/Nairobi")).toOffsetDateTime().toString())
                            .put("notes", draftBody.ifBlank { JSONObject.NULL })
                        "ticket" -> "hub/support/tickets" to JSONObject()
                            .put("subject", draftTitle).put("category", draftCategory).put("message", draftBody)
                        "ticket-reply" -> "hub/support/tickets/$editingTicketId/messages" to JSONObject()
                            .put("body", draftBody)
                        "collection" -> "hub/collections" to JSONObject()
                            .put("name", draftTitle).put("description", draftBody.ifBlank { JSONObject.NULL })
                        "collection-edit" -> "hub/collections/$editingCollectionId" to JSONObject()
                            .put("name", draftTitle).put("description", draftBody)
                        "collection-share" -> "hub/collections/$editingCollectionId/share" to JSONObject()
                            .put("user_id", draftBody.trim()).put("can_edit", false)
                        "collection-unshare" -> "hub/collections/$editingCollectionId/share/${draftBody.trim()}" to JSONObject()
                        "saved" -> {
                            val path = when (savedKind) {
                                "search" -> "/discover?query=${PersonalHubApi.query(draftTitle)}"
                                "provider" -> "/services"
                                "lesson" -> "/finance"
                                "comparison" -> "/discover"
                                else -> "/discover?query=${PersonalHubApi.query(draftTitle)}"
                            }
                            "hub/saved" to JSONObject()
                                .put("kind", savedKind).put("title", draftTitle)
                                .put("target_path", path)
                                .put("personal_note", draftBody.ifBlank { JSONObject.NULL })
                                .put("collection_id", selectedCollectionId.ifBlank { JSONObject.NULL })
                        }
                        "delete-account" -> "hub/account/deletion-requests" to JSONObject()
                            .put("current_password", passwordDraft).put("confirmation", confirmationDraft)
                        "clear-activity" -> "hub/activity" to JSONObject()
                        else -> "" to JSONObject()
                    }
                    if (type == "logout") {
                        onSignOut()
                    } else {
                        val method = when (type) {
                            "collection-edit" -> "PATCH"
                            "collection-unshare" -> "DELETE"
                            "clear-activity" -> "DELETE"
                            else -> "POST"
                        }
                        val success = when (type) {
                            "delete-account" -> "Account deletion request recorded. This request awaits review."
                            "collection-share" -> "Read-only collection access granted."
                            "collection-unshare" -> "Collection access removed."
                            "collection-edit" -> "Collection updated."
                            "ticket-reply" -> "Your support reply was added."
                            "clear-activity" -> "Your activity history was cleared."
                            else -> "Saved to your HomeScout account."
                        }
                        submit(action.first, method, action.second, success)
                    }
                }
                dialog = null
                draftTitle = ""
                draftBody = ""
                draftAmount = ""
                passwordDraft = ""
                confirmationDraft = ""
            }
        )
    }
}

@Composable
private fun ColumnScope.HubSectionContent(
    section: String,
    profile: JSONObject,
    profilePhoto: ImageBitmap?,
    preferences: JSONObject,
    rows: List<JSONObject>,
    savedHomes: List<JSONObject>,
    savedSearches: List<JSONObject>,
    searchHistory: List<JSONObject>,
    collections: List<JSONObject>,
    helpArticles: List<JSONObject>,
    selectedCollection: JSONObject,
    draftCategory: String,
    recordCategories: List<String>,
    documentCategory: String,
    savedKind: String,
    selectedCollectionId: String,
    ownCollections: List<JSONObject>,
    notificationCategories: List<String>,
    filter: String,
    dateFilter: String,
    search: String,
    loading: Boolean,
    error: String?,
    notice: String?,
    onFilterChange: (String) -> Unit,
    onDateFilterChange: (String) -> Unit,
    onSearchChange: (String) -> Unit,
    onNavigate: (String) -> Unit,
    onOpenDialog: (String) -> Unit,
    onCollectionAction: (String, JSONObject) -> Unit,
    onTicketReply: (JSONObject) -> Unit,
    onDraftCategoryChange: (String) -> Unit,
    onDocumentCategoryChange: (String) -> Unit,
    onSavedKindChange: (String) -> Unit,
    onCollectionSelect: (String) -> Unit,
    onDelete: (String) -> Unit,
    onSaveSearchAlert: (JSONObject) -> Unit,
    onOpenSearch: (JSONObject) -> Unit,
    onReadAll: () -> Unit,
    onRead: (String) -> Unit,
    onDismissNotification: (String) -> Unit,
    onDone: (String) -> Unit,
    onReschedule: (JSONObject) -> Unit,
    onSaveProfile: (JSONObject) -> Unit,
    onSavePreferences: (JSONObject) -> Unit,
    onExport: () -> Unit,
    onDocumentPick: () -> Unit,
    onPhotoPick: () -> Unit,
    onDownload: (JSONObject) -> Unit,
    onAppearanceChange: (String) -> Unit,
    onLargerTextChange: (Boolean) -> Unit
) {
    LazyColumn(
        modifier = Modifier.fillMaxWidth().weight(1f).padding(horizontal = 16.dp),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(top = 16.dp, bottom = 24.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        when (section) {
            "hub" -> {
                item {
                    val roles = profile.optJSONArray("roles").strings()
                    HubInfoCard(
                        title = profile.optString("given_name").ifBlank { "Welcome to your HomeScout hub" },
                        body = "Active role: ${profile.optString("active_role_code").ifBlank { roles.firstOrNull() ?: "guest" }.replace('_', ' ')}",
                        supporting = "Role access comes from approved account assignments. This selector never grants a role."
                    )
                }
                item {
                    val roles = profile.optJSONArray("roles").strings()
                    val actions = buildList {
                        addAll(commonActions)
                        if (roles.any { it in setOf("landlord", "real_estate_agent", "property_manager") }) {
                            add(HubAction("listings", "Manage listings", "Your authorized property workspace"))
                        }
                        if (roles.any { it in setOf("moderator", "admin", "super_admin") }) {
                            add(HubAction("operations", "Platform operations", "Restricted tools for approved staff"))
                        }
                    }
                    HubActionList(actions) { action ->
                        when (action.key) {
                            "logout" -> onOpenDialog("logout")
                            "trust-safety" -> onNavigate("trust-safety")
                            "collaboration" -> onNavigate("collaboration")
                            "listings" -> onNavigate("listing-management")
                            "operations" -> onNavigate("admin-operations")
                            else -> onNavigate("hub/${action.key}")
                        }
                    }
                }
            }
            "profile" -> {
                item {
                    ProfileEditor(profile, profilePhoto, loading, onSaveProfile, onPhotoPick)
                }
                item {
                    val roles = profile.optJSONArray("roles").strings()
                    HubInfoCard(
                        "Account access",
                        roles.joinToString(" · ").ifBlank { "No assigned role" },
                        "Email ${if (profile.optBoolean("email_verified")) "verified" else "not verified"} · Phone ${if (profile.optBoolean("phone_verified")) "verified" else "not verified"}" +
                            profile.optString("requested_role_code").takeIf(String::isNotBlank)?.let { " · $it role request is pending review" }.orEmpty()
                    )
                }
                items(profile.optJSONArray("roles").strings()) { role ->
                    OutlinedButton(
                        onClick = { onSavePreferences(JSONObject().put("active_role_code", role)) },
                        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
                    ) { Text("Use ${role.replace('_', ' ')} profile") }
                }
            }
            "saved" -> {
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { onOpenDialog("saved") }) { Icon(Icons.Filled.Add, null); Text("Save item") }
                        OutlinedButton(onClick = { onOpenDialog("collection") }) { Icon(Icons.Filled.FolderOpen, null); Text("New collection") }
                    }
                }
                if (savedHomes.isNotEmpty()) item { Text("Saved homes", style = MaterialTheme.typography.titleMedium) }
                items(savedHomes) { row ->
                    val property = row.optString("id")
                    val location = row.optJSONObject("location") ?: JSONObject()
                    val address = listOf(
                        location.optString("neighbourhood_name"),
                        location.optString("town_name"),
                        location.optString("county_name")
                    ).filter(String::isNotBlank).distinct().joinToString(", ")
                    HubInfoCard(
                        row.optString("title").ifBlank { "Saved HomeScout property" },
                        "KSh ${row.optString("rent_amount", "Not available")} / ${row.optString("rent_frequency", "monthly")}",
                        address.ifBlank { "Property details" },
                        onClick = { if (property.isNotBlank()) onNavigate("property/$property") },
                        trailing = {
                            IconButton(onClick = { onDelete("marketplace/saved/$property") }) {
                                Icon(Icons.Filled.DeleteOutline, "Remove saved property")
                            }
                        }
                    )
                }
                if (collections.isNotEmpty()) item { Text("Collections", style = MaterialTheme.typography.titleMedium) }
                items(collections) { row ->
                    var expanded by remember(row.optString("id")) { mutableStateOf(false) }
                    HubInfoCard(
                        row.optString("name"),
                        row.optString("description"),
                        if (row.optString("owner_user_id") == profile.optString("id")) {
                            val count = row.optJSONArray("shared_with_user_ids")?.length() ?: 0
                            if (count == 0) "Private to you" else "Shared with $count account(s)"
                        } else if (row.optBoolean("can_edit")) "Shared with you · can edit" else "Shared with you · read-only",
                        onClick = { onNavigate("hub/collection/${row.optString("id")}") },
                        trailing = if (row.optString("owner_user_id") == profile.optString("id")) {
                            {
                            Box {
                                IconButton(onClick = { expanded = true }) {
                                    Icon(Icons.Filled.MoreVert, "Collection actions")
                                }
                                DropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
                                    DropdownMenuItem(text = { Text("Edit collection") }, onClick = {
                                        expanded = false
                                        onCollectionAction("collection-edit", row)
                                    })
                                    DropdownMenuItem(text = { Text("Share read-only") }, onClick = {
                                        expanded = false
                                        onCollectionAction("collection-share", row)
                                    })
                                    if ((row.optJSONArray("shared_with_user_ids")?.length() ?: 0) > 0) {
                                        DropdownMenuItem(text = { Text("Remove shared access") }, onClick = {
                                            expanded = false
                                            onCollectionAction("collection-unshare", row)
                                        })
                                    }
                                    DropdownMenuItem(text = { Text("Delete collection") }, onClick = {
                                        expanded = false
                                        onDelete("hub/collections/${row.optString("id")}")
                                    })
                                }
                            }
                            }
                        } else null
                    )
                }
                if (rows.isNotEmpty()) item { Text("Other saved items", style = MaterialTheme.typography.titleMedium) }
                items(rows) { row ->
                    HubInfoCard(
                        row.optString("title"),
                        "${row.optString("kind").replace('_', ' ')}${row.optString("personal_note").takeIf(String::isNotBlank)?.let { " · $it" }.orEmpty()}",
                        "Saved ${row.optString("created_at")}",
                        onClick = { row.optString("target_path").takeIf(String::isNotBlank)?.let { onNavigate(it.trimStart('/')) } }
                    )
                }
                if (savedSearches.isNotEmpty()) item { Text("Saved search alerts", style = MaterialTheme.typography.titleMedium) }
                items(savedSearches) { row ->
                    val id = row.optString("id")
                    val filters = row.optJSONObject("filters") ?: JSONObject()
                    HubInfoCard(
                        "Saved search",
                        describeSearch(filters),
                        "Stored criteria · delivery is not configured",
                        onClick = { onOpenSearch(filters) },
                        trailing = {
                            IconButton(onClick = { onDelete("marketplace/alerts/$id") }) {
                                Icon(Icons.Filled.DeleteOutline, "Delete saved search alert")
                            }
                        }
                    )
                }
                if (searchHistory.isNotEmpty()) item { Text("Recent searches", style = MaterialTheme.typography.titleMedium) }
                items(searchHistory) { row ->
                    val filters = row.optJSONObject("filters") ?: JSONObject()
                    HubInfoCard(
                        filters.optString("query").ifBlank { "Home search" },
                        describeSearch(filters),
                        "${row.optInt("result_count")} results · ${row.optString("created_at")}",
                        onClick = { onOpenSearch(filters) },
                        trailing = { TextButton(onClick = { onSaveSearchAlert(filters) }) { Text("Save alert") } }
                    )
                }
                if (rows.isEmpty() && savedHomes.isEmpty() && collections.isEmpty() && savedSearches.isEmpty() && searchHistory.isEmpty()) item { HubEmpty("Nothing saved yet", "Save an item or start a shortlist collection.") }
            }
            "collection" -> {
                item { HubInfoCard(selectedCollection.optString("name"), selectedCollection.optString("description"), if (selectedCollection.optBoolean("can_edit")) "You can organize items in this collection." else "This collection is shared with you as read-only.") }
                items(rows) { row ->
                    val target = row.optString("target_path")
                    HubInfoCard(
                        row.optString("title"),
                        "${row.optString("kind").replace('_', ' ')} · ${row.optString("personal_note")}",
                        "Saved ${row.optString("created_at")}",
                        onClick = { target.takeIf(String::isNotBlank)?.let { onNavigate(it.trimStart('/')) } },
                        trailing = if (selectedCollection.optBoolean("can_edit")) {
                            { IconButton(onClick = { onDelete("hub/saved/${row.optString("id")}") }) { Icon(Icons.Filled.DeleteOutline, "Remove saved item") } }
                        } else null
                    )
                }
                if (rows.isEmpty()) item { HubEmpty("This collection is empty", "Save items from the Saved Items page.") }
            }
            "activity" -> {
                item { ChipRow(listOf("all", "property_view", "saved_item", "search", "comparison", "viewing", "message", "finance", "report", "account"), filter, onFilterChange) }
                item { ChipRow(listOf("all", "today", "7 days", "30 days"), dateFilter, onDateFilterChange) }
                item { OutlinedButton(onClick = { onOpenDialog("clear-activity") }) { Icon(Icons.Filled.DeleteOutline, null); Text("Clear activity history") } }
                items(rows) { row -> HubInfoCard(row.optString("title"), row.optString("details"), "${row.optString("event_type").replace('_', ' ')} · ${row.optString("created_at")}", onClick = { row.optString("target_path").takeIf(String::isNotBlank)?.let { onNavigate(it.trimStart('/')) } }) }
                if (rows.isEmpty()) item { HubEmpty("No activity recorded", "Your HomeScout activity history will appear here.") }
            }
            "schedule" -> {
                item {
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        Button(onClick = { onOpenDialog("task") }) { Icon(Icons.Filled.Add, null); Text("Add task") }
                        OutlinedButton(onClick = { onOpenDialog("viewing") }) { Text("Plan a viewing") }
                    }
                }
                item { ChipRow(listOf("day", "week", "month"), filter, onFilterChange) }
                item { HubInfoCard("Reminder delivery", "Reminders can be attached to an agenda item.", "This build stores the reminder preference but does not schedule or send it.") }
                items(rows) { row ->
                    HubInfoCard(
                        row.optString("title"),
                        "${row.optString("category").replace('_', ' ')} · ${row.optString("status")}",
                        "${row.optString("starts_at")} · ${row.optString("timezone", "Africa/Nairobi")}",
                        trailing = {
                            if (row.optString("status") == "planned") Row {
                                IconButton(onClick = { onReschedule(row) }) { Icon(Icons.Filled.CalendarMonth, "Move one day later") }
                                IconButton(onClick = { onDone(row.optString("id")) }) { Icon(Icons.Filled.Check, "Mark done") }
                                IconButton(onClick = { onDelete("hub/schedule/${row.optString("id")}") }) { Icon(Icons.Filled.DeleteOutline, "Delete schedule item") }
                            }
                        }
                    )
                }
                if (rows.isEmpty()) item { HubEmpty("Your schedule is clear", "Add a task or keep a viewing plan here.") }
            }
            "notifications" -> {
                item { ChipRow(listOf("all", "unread") + notificationCategories, filter, onFilterChange) }
                item { OutlinedButton(onClick = onReadAll, enabled = rows.any { it.isNull("read_at") }) { Icon(Icons.Filled.Check, null); Text("Mark all as read") } }
                items(rows) { row -> HubInfoCard(row.optString("title"), row.optString("body"), "${row.optString("category")} · ${row.optString("created_at")}", onClick = { onRead(row.optString("id")); row.optString("target_path").takeIf(String::isNotBlank)?.let { onNavigate(it.trimStart('/')) } }, trailing = { Row(verticalAlignment = Alignment.CenterVertically) { if (row.isNull("read_at")) Text("New", color = MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.labelMedium); IconButton(onClick = { onDismissNotification(row.optString("id")) }) { Icon(Icons.Filled.DeleteOutline, "Dismiss notification") } } }) }
                if (rows.isEmpty()) item { HubEmpty("You're all caught up", "In-app updates will be shown here when available.") }
            }
            "records" -> {
                item { Button(onClick = { onOpenDialog("record") }) { Icon(Icons.Filled.Add, null); Text("Add personal record") } }
                item { Text("Available record types", style = MaterialTheme.typography.labelLarge) }
                item { ChipRow(recordCategories, draftCategory, onDraftCategoryChange) }
                items(rows) { row -> HubInfoCard(row.optString("title"), row.optString("amount").takeIf(String::isNotBlank)?.let { "KSh $it" } ?: "Amount not entered", row.optString("notes").ifBlank { "${row.optString("category")} · ${row.optString("record_date")} · ${row.optString("evidence_status")}" }) }
                if (rows.isEmpty()) item { HubEmpty("No personal records", "Record keeping here is private and does not process or verify payments.") }
            }
            "documents" -> {
                item { Text("Document type", style = MaterialTheme.typography.labelLarge) }
                item { ChipRow(listOf("agreement", "receipt", "inspection", "checklist", "moving", "verification", "other"), documentCategory, onDocumentCategoryChange) }
                item { Button(onClick = onDocumentPick, enabled = !loading) { Icon(Icons.Filled.Add, null); Text("Upload a document") } }
                item { Text("PDF, JPEG, PNG and WebP · private local storage in this development setup", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                items(rows) { row -> HubInfoCard(row.optString("original_filename"), "${row.optString("category")} · ${row.optInt("size_bytes")} bytes", "Uploaded ${row.optString("uploaded_at")}", onClick = { onDownload(row) }, trailing = { IconButton(onClick = { onDelete("hub/documents/${row.optString("id")}") }) { Icon(Icons.Filled.DeleteOutline, "Delete document") } }) }
                if (rows.isEmpty()) item { HubEmpty("No documents yet", "Files you add are accessible only to your account.") }
            }
            "support" -> {
                item {
                    OutlinedTextField(value = search, onValueChange = onSearchChange, modifier = Modifier.fillMaxWidth(), label = { Text("Search help articles") }, leadingIcon = { Icon(Icons.Filled.Search, null) }, singleLine = true)
                    Button(onClick = { onOpenDialog("ticket") }, modifier = Modifier.padding(top = 8.dp)) { Text("Contact support") }
                    TextButton(onClick = { onNavigate("assistant") }) {
                        Text("Ask HomeScout Assistant")
                    }
                }
                if (helpArticles.isNotEmpty()) item { Text("Help articles", style = MaterialTheme.typography.titleMedium) }
                items(helpArticles) { row -> HubInfoCard(row.optString("title"), row.optString("body"), row.optString("category")) }
                if (rows.isNotEmpty()) item { Text("Your support tickets", style = MaterialTheme.typography.titleMedium) }
                items(rows) { row ->
                    HubInfoCard(
                        row.optString("subject"),
                        row.optString("category"),
                        "${row.optString("status")} · ${row.optJSONArray("messages")?.length() ?: 0} messages",
                        trailing = {
                            if (row.optString("status") != "closed") TextButton(onClick = { onTicketReply(row) }) { Text("Reply") }
                        }
                    )
                }
            }
            "settings" -> {
                item {
                    Text("Appearance", style = MaterialTheme.typography.titleMedium)
                    ChipRow(listOf("system", "light", "dark"), preferences.optString("appearance", "system"), { choice ->
                        onAppearanceChange(choice)
                        onSavePreferences(JSONObject().put("appearance", choice))
                    })
                }
                item {
                    val access = preferences.optJSONObject("accessibility_preferences") ?: JSONObject()
                    SettingSwitch("Larger text", "Use larger text across the app", access.optBoolean("larger_text")) { enabled ->
                        val updated = JSONObject(access.toString()).put("larger_text", enabled)
                        onLargerTextChange(enabled)
                        onSavePreferences(JSONObject().put("accessibility_preferences", updated))
                    }
                }
                item {
                    val notifications = preferences.optJSONObject("notification_preferences") ?: JSONObject()
                    SettingSwitch("In-app notifications", "Show account updates inside HomeScout", notifications.optBoolean("in_app", true)) { enabled ->
                        onSavePreferences(JSONObject().put("notification_preferences", JSONObject(notifications.toString()).put("in_app", enabled)))
                    }
                }
                item { OutlinedButton(onClick = onExport) { Icon(Icons.Filled.Download, null); Text("Export my data") } }
                item { OutlinedButton(onClick = { onOpenDialog("delete-account") }) { Icon(Icons.Filled.Security, null); Text("Request account deletion") } }
                item { HubInfoCard("Privacy and account security", "Review signed-in devices in the Profile tab.", "Deletion requests require your current password and are recorded for review.") }
            }
            "about" -> {
                item { HubInfoCard("Our mission", "Make it easier to find a place to call home.", "HomeScout brings Kenyan location discovery and useful rental tools together.") }
                item { HubInfoCard("Our vision", "A clearer, more confident home search for people across Kenya.", "County, town and neighbourhood discovery is designed around Kenyan renters and property owners.") }
                item { HubInfoCard("Trust", "Trust is earned through specific checks and clear evidence.", "Sample homes are illustrative. Email verification does not verify identity, ownership or tenancy.") }
                item { HubInfoCard("SmartRent and finance", "HomeScout can help people organize rental information.", "This screen is informational. It does not offer lending, financial advice or payment processing.") }
                item { HubInfoCard("HomeScout Assistant", "Ask about home search, budgeting, viewings and moving.", "Availability depends on secure server provider configuration and your consent.") }
                item { HubInfoCard("Privacy and community", "Personal hub data belongs to the signed-in account.", "Terms, data protection details and community rules need legal and operational review before launch.") }
            }
            "assistant" -> {
                item { HubInfoCard("HomeScout Assistant", "Get help with housing questions and HomeScout workflows.", "Messages are sent to the configured AI provider only after you agree to the privacy notice. Optional account context starts off.") }
                item {
                    OutlinedButton(onClick = { onNavigate("assistant") }, modifier = Modifier.fillMaxWidth()) {
                        Text("Open HomeScout Assistant")
                    }
                }
            }
        }
    }
}

@Composable
private fun ProfileEditor(
    profile: JSONObject,
    profilePhoto: ImageBitmap?,
    loading: Boolean,
    onSave: (JSONObject) -> Unit,
    onPhotoPick: () -> Unit
) {
    var given by remember(profile.optString("given_name")) { mutableStateOf(profile.optString("given_name")) }
    var family by remember(profile.optString("family_name")) { mutableStateOf(profile.optString("family_name")) }
    var preferred by remember(profile.optString("preferred_name")) { mutableStateOf(profile.optString("preferred_name")) }
    var phone by remember(profile.optString("phone_number")) { mutableStateOf(profile.optString("phone_number")) }
    var location by remember(profile.optString("location_label")) { mutableStateOf(profile.optString("location_label")) }
    var bio by remember(profile.optString("bio")) { mutableStateOf(profile.optString("bio")) }
    val initials = listOf(preferred.ifBlank { given }, family)
        .mapNotNull { it.trim().firstOrNull() }
        .joinToString("")
    HubCard {
        if (profilePhoto != null) {
            Image(
                bitmap = profilePhoto,
                contentDescription = "Your HomeScout profile photo",
                modifier = Modifier.size(76.dp).clip(CircleShape)
            )
        } else {
            ProfileAvatar(
                initials = initials.ifBlank { "HS" },
                contentDescription = "Profile photo placeholder"
            )
        }
        Text("Profile details", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Text(
            "Your personal details are private to this signed-in account. Press Save profile to store your changes.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        HubInfoCard(
            "Sign-in email",
            profile.optString("email").ifBlank { "No email on this account" },
            if (profile.optBoolean("email_verified")) "Verified" else "Not verified · changing this requires the account verification flow"
        )
        OutlinedButton(onClick = onPhotoPick, enabled = !loading) { Text("Add or change profile photo") }
        HubInput("First name", given, maxLength = 100, onValueChange = { given = it })
        HubInput("Last name", family, maxLength = 100, onValueChange = { family = it })
        HubInput("Preferred name", preferred, maxLength = 100, onValueChange = { preferred = it })
        HubInput("Phone number (e.g. +254 7xx xxx xxx)", phone, maxLength = 32, onValueChange = { phone = it })
        HubInput("Location (neighbourhood, town, county)", location, maxLength = 120, onValueChange = { location = it })
        HubInput("About you", bio, singleLine = false, maxLength = 1000, onValueChange = { bio = it })
        Text(
            "Adding a phone number does not mark it as verified.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
        Button(onClick = {
            onSave(JSONObject().put("given_name", given).put("family_name", family)
                .put("preferred_name", preferred).put("phone_number", phone)
                .put("location_label", location).put("bio", bio))
        }, enabled = !loading, modifier = Modifier.fillMaxWidth()) { Text("Save profile") }
    }
}

@Composable
private fun PersonalHubDialog(
    type: String,
    title: String,
    body: String,
    amount: String,
    password: String,
    confirmation: String,
    category: String,
    recordCategories: List<String>,
    savedKind: String,
    selectedCollectionId: String,
    collections: List<JSONObject>,
    collectionShareIds: List<String>,
    scheduleDate: String,
    scheduleTime: String,
    reminderMinutes: String,
    onTitleChange: (String) -> Unit,
    onBodyChange: (String) -> Unit,
    onAmountChange: (String) -> Unit,
    onCategoryChange: (String) -> Unit,
    onSavedKindChange: (String) -> Unit,
    onCollectionSelect: (String) -> Unit,
    onScheduleDateChange: (String) -> Unit,
    onScheduleTimeChange: (String) -> Unit,
    onReminderChange: (String) -> Unit,
    onPasswordChange: (String) -> Unit,
    onConfirmationChange: (String) -> Unit,
    onDismiss: () -> Unit,
    onConfirm: (String) -> Unit
) {
    val heading = when (type) {
        "task" -> "Add a task"
        "viewing" -> "Plan a viewing"
        "record" -> "Add a personal record"
        "ticket" -> "Contact HomeScout support"
        "ticket-reply" -> "Reply to support ticket"
        "collection" -> "Create a collection"
        "collection-edit" -> "Edit collection"
        "collection-share" -> "Share collection read-only"
        "collection-unshare" -> "Remove collection access"
        "saved" -> "Save a neighbourhood"
        "clear-activity" -> "Clear activity history?"
        "logout" -> "Sign out of HomeScout?"
        else -> "Request account deletion"
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(heading) },
        text = {
            Column(Modifier.verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                when (type) {
                    "task", "viewing" -> {
                        OutlinedButton(onClick = {
                            onTitleChange("DEMO · ${listOf("Confirm viewing details", "Arrange moving van", "Collect keys", "Check utility setup").random()}")
                            onScheduleDateChange(LocalDate.now(ZoneId.of("Africa/Nairobi")).plusDays(kotlin.random.Random.nextLong(2, 22)).toString())
                            onScheduleTimeChange(listOf("09:00", "11:30", "14:00", "16:30").random())
                            onReminderChange(listOf("15", "30", "60").random())
                        }, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                        Text("DEMO event · review it, then save to add it to your schedule.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        HubInput("Title", title, onTitleChange)
                        HomeScoutDateField(scheduleDate, onScheduleDateChange, "Date · DD-MM-YYYY", Modifier.fillMaxWidth())
                        HubInput("Time (HH:MM)", scheduleTime, onScheduleTimeChange)
                        Text("Optional reminder, in minutes before the event")
                        ChipRow(listOf("none", "15", "30", "60"), reminderMinutes.ifBlank { "none" }) {
                            onReminderChange(if (it == "none") "" else it)
                        }
                    }
                    "record" -> {
                        HubInput("Record title", title, onTitleChange)
                        Text("Record type")
                        ChipRow(recordCategories, category, onCategoryChange)
                        HubInput("Amount in KES (optional)", amount, onAmountChange)
                        HubInput("Notes", body, onBodyChange)
                    }
                    "ticket" -> {
                        HubInput("Subject", title, onTitleChange)
                        Text("Support topic")
                        ChipRow(listOf("account", "property", "safety", "privacy", "technical", "feedback", "other"), category, onCategoryChange)
                        HubInput("How can we help?", body, onBodyChange, singleLine = false)
                    }
                    "ticket-reply" -> HubInput("Your reply", body, onBodyChange, singleLine = false)
                    "collection" -> {
                        HubInput("Collection name", title, onTitleChange)
                        HubInput("Description (optional)", body, onBodyChange)
                    }
                    "collection-edit" -> {
                        HubInput("Collection name", title, onTitleChange)
                        HubInput("Description (optional)", body, onBodyChange)
                    }
                    "collection-share" -> {
                        Text("Share this collection with another HomeScout account. Access is read-only.")
                        HubInput("Account ID", body, onBodyChange)
                    }
                    "collection-unshare" -> {
                        Text("Choose a shared account to remove from this collection.")
                        if (collectionShareIds.isEmpty()) Text("No accounts currently have access.")
                        else ChipRow(collectionShareIds, body, onBodyChange)
                    }
                    "saved" -> {
                        Text("Type of item")
                        ChipRow(listOf("neighbourhood", "search", "provider", "lesson", "comparison"), savedKind, onSavedKindChange)
                        HubInput(if (savedKind == "neighbourhood") "Neighbourhood" else "Title", title, onTitleChange)
                        HubInput("Private note (optional)", body, onBodyChange)
                        if (collections.isNotEmpty()) {
                            Text("Add to collection")
                            ChipRow(
                                listOf("none") + collections.map { it.optString("name") },
                                collections.firstOrNull { it.optString("id") == selectedCollectionId }?.optString("name") ?: "none"
                            ) { choice ->
                                onCollectionSelect(collections.firstOrNull { it.optString("name") == choice }?.optString("id").orEmpty())
                            }
                        }
                    }
                    "delete-account" -> {
                        Text("This records a deletion request for review. Confirming does not erase your data immediately.")
                        HubInput("Current password", password, onPasswordChange)
                        HubInput("Type DELETE to confirm", confirmation, onConfirmationChange)
                    }
                    "clear-activity" -> Text("This permanently removes the activity history for your account.")
                    "logout" -> Text("You will be signed out of this device.")
                }
            }
        },
        confirmButton = {
                TextButton(
                    onClick = { onConfirm(type) },
                    enabled = when (type) {
                        "delete-account" -> confirmation == "DELETE" && password.isNotBlank()
                        "collection-share", "collection-unshare" -> body.isNotBlank()
                        "task", "viewing" -> title.isNotBlank() && runCatching {
                            LocalDate.parse(scheduleDate)
                            LocalTime.parse(scheduleTime)
                        }.isSuccess
                        "record", "collection", "collection-edit" -> title.isNotBlank()
                        "ticket" -> title.length >= 3 && body.length >= 5
                        "ticket-reply" -> body.isNotBlank()
                        else -> true
                    }
                ) {
                    Text(when (type) {
                        "delete-account" -> "Request deletion"
                        "collection-share" -> "Share read-only"
                        "collection-unshare" -> "Remove access"
                        "logout" -> "Sign out"
                        "clear-activity" -> "Clear history"
                        else -> "Save"
                    })
            }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun HubActionList(actions: List<HubAction>, onAction: (HubAction) -> Unit) {
    if (actions.isEmpty()) return

    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(vertical = 4.dp)) {
            actions.forEachIndexed { index, action ->
                val icon = when (action.key) {
                    "hub", "listings" -> Icons.Filled.PersonOutline
                    "saved" -> Icons.Filled.FolderOpen
                    "activity" -> Icons.Filled.History
                    "schedule" -> Icons.Filled.CalendarMonth
                    "collaboration" -> Icons.Filled.ChatBubbleOutline
                    "notifications" -> Icons.Filled.NotificationsNone
                    "records" -> Icons.Filled.ReceiptLong
                    "documents" -> Icons.Filled.FolderOpen
                    "trust-safety" -> Icons.Filled.Security
                    "support" -> Icons.Filled.HelpOutline
                    "settings" -> Icons.Filled.Settings
                    "about" -> Icons.Filled.Info
                    "assistant" -> Icons.Filled.Search
                    "logout" -> Icons.Filled.Logout
                    "operations" -> Icons.Filled.AdminPanelSettings
                    else -> Icons.Filled.PersonOutline
                }
                Row(
                    modifier = Modifier.fillMaxWidth()
                        .clickable(role = Role.Button) { onAction(action) }
                        .padding(horizontal = 16.dp, vertical = 13.dp),
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Surface(
                        modifier = Modifier.size(42.dp),
                        shape = CircleShape,
                        color = MaterialTheme.colorScheme.primaryContainer
                    ) {
                        Box(contentAlignment = Alignment.Center) {
                            Icon(icon, contentDescription = null, tint = MaterialTheme.colorScheme.onPrimaryContainer)
                        }
                    }
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                        Text(action.title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                        Text(action.detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    Icon(
                        Icons.AutoMirrored.Filled.ArrowForward,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.onSurfaceVariant,
                        modifier = Modifier.size(18.dp)
                    )
                }
                if (index < actions.lastIndex) HorizontalDivider(Modifier.padding(start = 72.dp, end = 16.dp))
            }
        }
    }
}

@Composable
private fun HubInfoCard(
    title: String,
    body: String,
    supporting: String,
    onClick: (() -> Unit)? = null,
    trailing: @Composable (() -> Unit)? = null
) {
    HubCard(onClick = onClick) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                if (body.isNotBlank() && body != "null") Text(body, style = MaterialTheme.typography.bodyMedium)
                if (supporting.isNotBlank() && supporting != "null") Text(supporting, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            trailing?.invoke()
        }
    }
}

@Composable
private fun HubCard(onClick: (() -> Unit)? = null, content: @Composable () -> Unit) {
    Card(onClick = { onClick?.invoke() }, enabled = onClick != null, modifier = Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) { content() }
    }
}

@Composable
private fun HubInput(
    label: String,
    value: String,
    onValueChange: (String) -> Unit,
    singleLine: Boolean = true,
    maxLength: Int? = null
) {
    OutlinedTextField(
        value,
        onValueChange = { input -> onValueChange(if (maxLength == null) input else input.take(maxLength)) },
        modifier = Modifier.fillMaxWidth(),
        label = { Text(label) },
        singleLine = singleLine,
        minLines = if (singleLine) 1 else 3
    )
}

@Composable
private fun ChipRow(options: List<String>, selected: String, onSelect: (String) -> Unit) {
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
        options.forEach { option -> FilterChip(selected == option, onClick = { onSelect(option) }, label = { Text(option.replace('_', ' ').replaceFirstChar(Char::uppercase)) }) }
    }
}

@Composable
private fun SettingSwitch(title: String, detail: String, checked: Boolean, onChange: (Boolean) -> Unit) {
    Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
        Column(Modifier.weight(1f)) {
            Text(title, style = MaterialTheme.typography.titleSmall)
            Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        }
        Switch(checked, onChange)
    }
}

@Composable
private fun HubEmpty(title: String, detail: String) {
    HubCard {
        Icon(Icons.Filled.CalendarMonth, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
        Text(title, style = MaterialTheme.typography.titleMedium)
        Text(detail, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun HubMessage(message: String, error: Boolean = false) {
    Surface(color = if (error) MaterialTheme.colorScheme.errorContainer else MaterialTheme.colorScheme.secondaryContainer, modifier = Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 8.dp), shape = MaterialTheme.shapes.medium) {
        Text(message, Modifier.padding(14.dp), color = if (error) MaterialTheme.colorScheme.onErrorContainer else MaterialTheme.colorScheme.onSecondaryContainer)
    }
}

private fun JSONArray?.objects(): List<JSONObject> = buildList {
    if (this@objects != null) for (index in 0 until this@objects.length()) {
        this@objects.optJSONObject(index)?.let(::add)
    }
}

private fun describeSearch(filters: JSONObject): String = buildList {
    filters.optString("query").takeIf(String::isNotBlank)?.let(::add)
    val minRent = filters.optString("rent_min")
    val maxRent = filters.optString("rent_max")
    if (minRent.isNotBlank() || maxRent.isNotBlank()) {
        val lower = minRent.takeIf(String::isNotBlank)?.let { "KSh $it" } ?: "Any"
        val upper = maxRent.takeIf(String::isNotBlank)?.let { "KSh $it" } ?: "Any"
        add("Rent $lower–$upper")
    }
    filters.optString("bedrooms").takeIf(String::isNotBlank)?.let { add("$it bedrooms") }
    filters.optString("bedrooms_min").takeIf(String::isNotBlank)?.let { add("$it+ bedrooms") }
    filters.optString("property_type").takeIf(String::isNotBlank)?.let { add(it.replace('_', ' ')) }
    filters.optString("furnishing").takeIf(String::isNotBlank)?.let { add(it.replace('_', ' ')) }
    if (filters.optBoolean("verified_only")) add("Verified only")
}.joinToString(" · ").ifBlank { "No text filter" }

private fun JSONArray?.strings(): List<String> = buildList {
    if (this@strings != null) for (index in 0 until this@strings.length()) {
        this@strings.optString(index).takeIf(String::isNotBlank)?.let(::add)
    }
}

private fun recordCategories(roles: List<String>): List<String> = buildSet {
    add("other")
    if (roles.any { it in setOf("tenant", "roommate") }) {
        addAll(setOf("rent", "deposit", "expense", "receipt"))
    }
    if ("service_provider" in roles) addAll(setOf("booking", "order", "expense", "receipt"))
    if (roles.any { it in setOf("landlord", "real_estate_agent", "property_manager") }) {
        addAll(setOf("viewing", "expense", "receipt", "order"))
    }
}.toList().sorted()

private fun contentName(context: android.content.Context, uri: Uri): String {
    val cursor = context.contentResolver.query(uri, arrayOf(OpenableColumns.DISPLAY_NAME), null, null, null)
    cursor?.use { if (it.moveToFirst()) return it.getString(0).orEmpty().ifBlank { "document" } }
    return uri.lastPathSegment?.substringAfterLast('/')?.takeIf(String::isNotBlank) ?: "document"
}

private fun readLimited(context: android.content.Context, uri: Uri, maxBytes: Int): ByteArray {
    val input = context.contentResolver.openInputStream(uri) ?: error("The selected file could not be opened.")
    input.use { stream ->
        val output = java.io.ByteArrayOutputStream()
        val buffer = ByteArray(8192)
        var total = 0
        while (true) {
            val count = stream.read(buffer)
            if (count < 0) break
            total += count
            require(total <= maxBytes) { "The document is larger than 15 MB." }
            output.write(buffer, 0, count)
        }
        return output.toByteArray()
    }
}
