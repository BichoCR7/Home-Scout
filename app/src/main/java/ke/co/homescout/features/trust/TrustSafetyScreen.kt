package ke.co.homescout.features.trust

import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.layout.wrapContentWidth
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AttachFile
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.VerifiedUser
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Checkbox
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.FilterChip
import androidx.compose.material3.Icon
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.SnackbarHost
import androidx.compose.material3.SnackbarHostState
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateListOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.PersonalHubApi
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.components.HomeScoutDateTimeField
import ke.co.homescout.ui.components.HomeScoutPrimaryButton
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.time.OffsetDateTime
import java.time.ZoneId

private val trustSections = listOf("Safety", "Verification", "Viewings", "Reports", "Staff review")

private data class TrustScreenData(
    val verifications: List<JSONObject>,
    val viewings: List<JSONObject>,
    val listingReports: List<JSONObject>,
    val safetyReports: List<JSONObject>,
    val moderationRows: List<JSONObject>,
    val verificationQueue: List<JSONObject>,
    val error: String?
)

@Composable
fun TrustSafetyScreen(
    accessToken: String?,
    initialPropertyId: String = "",
    initialSection: String = "Safety"
) {
    val context = LocalContext.current
    val api = remember { PersonalHubApi() }
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    val uploads = remember { mutableStateListOf<JSONObject>() }
    var section by rememberSaveable(initialSection) {
        mutableStateOf(initialSection.takeIf { it in trustSections } ?: "Safety")
    }
    var busy by remember { mutableStateOf(false) }
    var refreshKey by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var confirmation by remember { mutableStateOf<JSONObject?>(null) }
    var verifications by remember { mutableStateOf(emptyList<JSONObject>()) }
    var viewings by remember { mutableStateOf(emptyList<JSONObject>()) }
    var listingReports by remember { mutableStateOf(emptyList<JSONObject>()) }
    var safetyReports by remember { mutableStateOf(emptyList<JSONObject>()) }
    var moderationRows by remember { mutableStateOf(emptyList<JSONObject>()) }
    var verificationQueue by remember { mutableStateOf(emptyList<JSONObject>()) }
    var verificationType by rememberSaveable { mutableStateOf("landlord") }
    var propertyId by rememberSaveable { mutableStateOf(initialPropertyId) }
    var verificationNote by rememberSaveable { mutableStateOf("") }
    var reportPropertyId by rememberSaveable { mutableStateOf(initialPropertyId) }
    var reportReason by rememberSaveable { mutableStateOf("suspected_scam") }
    var reportDetails by rememberSaveable { mutableStateOf("") }
    var incidentCategory by rememberSaveable { mutableStateOf("viewing_safety") }
    var incidentDetails by rememberSaveable { mutableStateOf("") }
    var incidentViewingId by rememberSaveable { mutableStateOf("") }
    var incidentPropertyId by rememberSaveable { mutableStateOf(initialPropertyId) }
    var viewingTitle by rememberSaveable { mutableStateOf("Home viewing") }
    var viewingDate by rememberSaveable {
        mutableStateOf(
            OffsetDateTime.now(ZoneId.of("Africa/Nairobi")).plusDays(1)
                .withSecond(0).withNano(0).toString()
        )
    }
    var meetingPoint by rememberSaveable { mutableStateOf("") }
    var trustedName by rememberSaveable { mutableStateOf("") }
    var trustedPhone by rememberSaveable { mutableStateOf("") }
    var viewingNotes by rememberSaveable { mutableStateOf("") }
    var shareAccountId by rememberSaveable { mutableStateOf("") }
    var shareConsent by rememberSaveable { mutableStateOf(false) }
    var reviewMessage by rememberSaveable {
        mutableStateOf("We reviewed your report and updated its status.")
    }

    LaunchedEffect(accessToken, refreshKey, section) {
        val token = accessToken ?: return@LaunchedEffect
        error = null
        val result = withContext(Dispatchers.IO) {
            val failures = mutableListOf<String>()
            fun getRows(path: String): List<JSONObject> = try {
                api.getArray(path, token).objects()
            } catch (failure: Exception) {
                failures += failure.message ?: "Some HomeScout safety records could not load."
                emptyList()
            }
            TrustScreenData(
                verifications = getRows("trust/verifications/mine"),
                viewings = getRows("trust/viewings"),
                listingReports = getRows("trust/listing-reports/mine"),
                safetyReports = getRows("trust/safety-reports/mine"),
                moderationRows = if (section == "Staff review") getRows("trust/moderation/queue") else emptyList(),
                verificationQueue = if (section == "Staff review") getRows("trust/verifications/queue") else emptyList(),
                error = failures.firstOrNull()
            )
        }
        verifications = result.verifications
        viewings = result.viewings
        listingReports = result.listingReports
        safetyReports = result.safetyReports
        moderationRows = result.moderationRows
        verificationQueue = result.verificationQueue
        error = result.error
    }

    fun perform(action: () -> Unit) {
        val token = accessToken
        if (token.isNullOrBlank()) {
            scope.launch { snackbar.showSnackbar("Sign in to use HomeScout safety tools.") }
            return
        }
        scope.launch {
            busy = true
            error = null
            try {
                withContext(Dispatchers.IO) { action() }
                refreshKey += 1
                snackbar.showSnackbar("HomeScout updated your trust and safety record.")
            } catch (failure: Exception) {
                error = failure.message ?: "HomeScout could not save that change. Try again."
            } finally {
                busy = false
            }
        }
    }

    val pickDocument = rememberLauncherForActivityResult(
        contract = ActivityResultContracts.OpenDocument()
    ) { uri ->
        if (uri != null) {
            scope.launch {
                busy = true
                try {
                    val doc = withContext(Dispatchers.IO) {
                        val filename = context.contentResolver.query(uri, null, null, null, null)?.use { cursor ->
                            val index = cursor.getColumnIndex(android.provider.OpenableColumns.DISPLAY_NAME)
                            if (cursor.moveToFirst() && index >= 0) cursor.getString(index) else "evidence"
                        } ?: "evidence"
                        val bytes = context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                            ?: throw IllegalStateException("This file could not be opened.")
                        require(bytes.size <= 15_728_640) { "Choose a file no larger than 15 MB." }
                        val response = api.upload(
                            "hub/documents?category=verification&filename=${PersonalHubApi.query(filename)}",
                            checkNotNull(accessToken),
                            bytes
                        )
                        JSONObject(response)
                    }
                    uploads.add(doc)
                    snackbar.showSnackbar("Private evidence uploaded securely.")
                } catch (failure: Exception) {
                    error = failure.message ?: "The private file could not be uploaded."
                } finally {
                    busy = false
                }
            }
        }
    }

    Box(Modifier.fillMaxSize(), contentAlignment = Alignment.TopCenter) {
        LazyColumn(
            modifier = Modifier.fillMaxWidth().widthIn(max = 760.dp),
            contentPadding = androidx.compose.foundation.layout.PaddingValues(18.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text(
                        "Trust & safety",
                        style = MaterialTheme.typography.headlineSmall,
                        fontWeight = FontWeight.SemiBold
                    )
                    Text(
                        "Clear checks, private plans, and a fair review process.",
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            item {
                Row(
                    modifier = Modifier.horizontalScroll(rememberScrollState()),
                    horizontalArrangement = Arrangement.spacedBy(7.dp)
                ) {
                    trustSections.forEach { label ->
                        FilterChip(
                            selected = section == label,
                            onClick = { section = label },
                            label = { Text(label) }
                        )
                    }
                }
            }
            if (error != null) {
                item { TrustMessageCard("Could not load or save", error.orEmpty(), isError = true) }
            }
            if (busy) {
                item {
                    CircularProgressIndicator(
                        modifier = Modifier.fillMaxWidth().wrapContentWidth(Alignment.CenterHorizontally)
                    )
                }
            }
            when (section) {
                "Safety" -> {
                    item {
                        TrustMessageCard(
                            "Practical viewing safety",
                            "These steps can reduce risk but cannot guarantee safety or verify a person or home. In immediate danger, move somewhere safe and contact local emergency services directly."
                        )
                    }
                    item {
                        TrustChecklistCard(
                            "Before you go",
                            listOf(
                                "Arrange a daytime visit where practical and tell someone you trust.",
                                "Confirm who may rent the home and ask for written terms before paying.",
                                "Never share your M-Pesa PIN, one-time codes, or passwords."
                            )
                        )
                    }
                    item {
                        TrustChecklistCard(
                            "At the viewing",
                            listOf(
                                "Meet at the agreed place, keep your phone charged, and leave if pressured.",
                                "Bring someone you trust where possible; do not hand over original documents or cash.",
                                "Check-in and check-out only update your own record. HomeScout does not send emergency alerts."
                            )
                        )
                    }
                    item {
                        TrustChecklistCard(
                            "After the viewing",
                            listOf(
                                "Keep written terms and receipts, and independently confirm a payment recipient.",
                                "Reports are reviewed as evidence arrives; a report is not proof of wrongdoing.",
                                "Use the Reports tab to tell HomeScout about a concerning listing or incident."
                            )
                        )
                    }
                    item {
                        TrustMessageCard(
                            "Trust indicators",
                            "A verified label is shown only after a reviewer approves a specific check. Email or phone confirmation alone does not prove identity, property ownership, or listing authority."
                        )
                    }
                    item { if (accessToken == null) SignInNotice() }
                }
                "Verification" -> {
                    item {
                        TrustMessageCard(
                            "Request a review",
                            "Reviews are manual. Upload documents only when you are ready; verification files are encrypted at rest and available to you and authorized reviewers."
                        )
                    }
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            Text("What needs review?", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                            Row(
                                modifier = Modifier.horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(7.dp)
                            ) {
                                listOf("landlord", "agent", "property", "service_provider").forEach { type ->
                                    FilterChip(
                                        verificationType == type,
                                        onClick = { verificationType = type },
                                        label = { Text(type.replace('_', ' ')) }
                                    )
                                }
                            }
                            if (verificationType == "property") {
                                OutlinedTextField(
                                    propertyId,
                                    { propertyId = it },
                                    Modifier.fillMaxWidth(),
                                    label = { Text("Your property ID") },
                                    singleLine = true
                                )
                            }
                            OutlinedTextField(
                                verificationNote,
                                { verificationNote = it },
                                Modifier.fillMaxWidth(),
                                label = { Text("Note for the reviewer (optional)") },
                                minLines = 2,
                                maxLines = 4
                            )
                            TrustUploadButton(!busy, onClick = {
                                pickDocument.launch(arrayOf("application/pdf", "image/jpeg", "image/png", "image/webp"))
                            })
                            UploadList(uploads)
                            HomeScoutPrimaryButton(
                                "Submit for manual review",
                                Modifier.fillMaxWidth(),
                                enabled = !busy && accessToken != null && uploads.isNotEmpty() &&
                                    (verificationType != "property" || propertyId.isNotBlank()),
                                onClick = {
                                    val token = accessToken ?: return@HomeScoutPrimaryButton
                                    val body = JSONObject()
                                        .put("subject_type", verificationType)
                                        .put(
                                            "evidence_document_ids",
                                            JSONArray().apply { uploads.forEach { put(it.optString("id")) } }
                                        )
                                        .put("submission_note", verificationNote)
                                    if (verificationType == "property") body.put("property_id", propertyId.trim())
                                    perform { api.send("trust/verifications", "POST", token, body) }
                                }
                            )
                        }
                    }
                    item { Text("Your requests", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
                    if (verifications.isEmpty()) {
                        item {
                            TrustMessageCard(
                                "No verification requests",
                                "Nothing has been submitted from this account yet. An email or phone check is not a property or identity verification."
                            )
                        }
                    }
                    items(verifications, key = { it.optString("id") }) { VerificationItem(it) }
                    item { if (accessToken == null) SignInNotice() }
                }
                "Viewings" -> {
                    item {
                        TrustMessageCard(
                            "Plan a safer viewing",
                            "Your meeting details and trusted contact are encrypted and private. HomeScout stores check-in status but does not send push, SMS, or emergency alerts."
                        )
                    }
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                            OutlinedTextField(viewingTitle, { viewingTitle = it }, Modifier.fillMaxWidth(), label = { Text("Viewing title") }, singleLine = true)
                            OutlinedTextField(propertyId, { propertyId = it }, Modifier.fillMaxWidth(), label = { Text("Property ID (optional)") }, singleLine = true)
                            HomeScoutDateTimeField(viewingDate, { viewingDate = it }, "Date and time · DD-MM-YYYY", Modifier.fillMaxWidth())
                            OutlinedTextField(meetingPoint, { meetingPoint = it }, Modifier.fillMaxWidth(), label = { Text("Meeting point") }, singleLine = true)
                            OutlinedTextField(trustedName, { trustedName = it }, Modifier.fillMaxWidth(), label = { Text("Trusted contact name") }, singleLine = true)
                            OutlinedTextField(trustedPhone, { trustedPhone = it }, Modifier.fillMaxWidth(), label = { Text("Trusted contact phone") }, singleLine = true)
                            OutlinedTextField(viewingNotes, { viewingNotes = it }, Modifier.fillMaxWidth(), label = { Text("Private notes (optional)") }, minLines = 2)
                            OutlinedTextField(
                                shareAccountId,
                                { shareAccountId = it },
                                Modifier.fillMaxWidth(),
                                label = { Text("Share with HomeScout account ID (optional)") },
                                singleLine = true
                            )
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Checkbox(shareConsent, { shareConsent = it })
                                Text("I consent to share the viewing details with this account.")
                            }
                            HomeScoutPrimaryButton(
                                "Save private viewing plan",
                                Modifier.fillMaxWidth(),
                                enabled = !busy && accessToken != null && meetingPoint.isNotBlank() &&
                                    trustedName.isNotBlank() && trustedPhone.isNotBlank(),
                                onClick = {
                                    val token = accessToken ?: return@HomeScoutPrimaryButton
                                    val startsAt = runCatching {
                                        OffsetDateTime.parse(viewingDate).toString()
                                    }.getOrNull()
                                    if (startsAt == null) {
                                        error = "Choose a date and time using the calendar."
                                        return@HomeScoutPrimaryButton
                                    }
                                    val body = JSONObject()
                                        .put("title", viewingTitle)
                                        .put("starts_at", startsAt)
                                        .put("meeting_point", meetingPoint)
                                        .put("trusted_contact_name", trustedName)
                                        .put("trusted_contact_phone", trustedPhone)
                                        .put("notes", viewingNotes)
                                        .put("consent_to_share_details", shareConsent)
                                    if (propertyId.isNotBlank()) body.put("property_id", propertyId.trim())
                                    if (shareAccountId.isNotBlank()) body.put("share_with_user_id", shareAccountId.trim())
                                    perform { api.send("trust/viewings", "POST", token, body) }
                                }
                            )
                        }
                    }
                    item { Text("Your viewing plans", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
                    if (viewings.isEmpty()) {
                        item { TrustMessageCard("No viewing plans", "You can add a private viewing plan above or open Trust & safety from a property listing.") }
                    }
                    items(viewings, key = { it.optString("id") }) { row ->
                        ViewingItem(
                            row,
                            onAction = { action ->
                                val token = accessToken ?: return@ViewingItem
                                perform { api.send("trust/viewings/${row.optString("id")}/$action", "POST", token) }
                            },
                            onReport = { viewing ->
                                incidentViewingId = viewing.optString("id")
                                if (viewing.optString("property_id").isNotBlank()) incidentPropertyId = viewing.optString("property_id")
                                confirmation = JSONObject().put("kind", "incident")
                            }
                        )
                    }
                    item { if (accessToken == null) SignInNotice() }
                }
                "Reports" -> {
                    item {
                        TrustMessageCard(
                            "Report carefully",
                            "Reports are reviewed by authorized staff. A report does not automatically label a person or remove a listing. Give specific facts and attach only relevant evidence."
                        )
                    }
                    item {
                        Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                            OutlinedTextField(reportPropertyId, { reportPropertyId = it }, Modifier.fillMaxWidth(), label = { Text("Listing property ID") }, singleLine = true)
                            Row(
                                modifier = Modifier.horizontalScroll(rememberScrollState()),
                                horizontalArrangement = Arrangement.spacedBy(6.dp)
                            ) {
                                listOf("suspected_scam", "duplicate", "inaccurate_details", "unsafe_or_prohibited", "other").forEach { choice ->
                                    FilterChip(reportReason == choice, onClick = { reportReason = choice }, label = { Text(choice.replace('_', ' ')) })
                                }
                            }
                            OutlinedTextField(reportDetails, { reportDetails = it }, Modifier.fillMaxWidth(), label = { Text("What happened?") }, minLines = 3, maxLines = 5)
                            TrustUploadButton(!busy, "Attach evidence file", onClick = {
                                pickDocument.launch(arrayOf("application/pdf", "image/jpeg", "image/png", "image/webp"))
                            })
                            UploadList(uploads)
                            HomeScoutPrimaryButton(
                                "Submit listing report",
                                Modifier.fillMaxWidth(),
                                enabled = !busy && accessToken != null && reportPropertyId.isNotBlank() &&
                                    reportDetails.trim().length >= 10,
                                onClick = {
                                    val token = accessToken ?: return@HomeScoutPrimaryButton
                                    val body = JSONObject()
                                        .put("reason", reportReason)
                                        .put("details", reportDetails.trim())
                                        .put(
                                            "evidence_document_ids",
                                            JSONArray().apply { uploads.forEach { put(it.optString("id")) } }
                                        )
                                    perform {
                                        api.send("trust/properties/${reportPropertyId.trim()}/reports", "POST", token, body)
                                    }
                                }
                            )
                            OutlinedButton(
                                onClick = { confirmation = JSONObject().put("kind", "incident") },
                                modifier = Modifier.fillMaxWidth()
                            ) { Text("Report a safety incident") }
                        }
                    }
                    item { Text("Listing reports", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
                    if (listingReports.isEmpty()) item { TrustMessageCard("No listing reports", "Reports you submit will appear here with their review status.") }
                    items(listingReports, key = { it.optString("id") }) { ReportItem(it, "Listing report") }
                    item { Text("Safety incident reports", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
                    if (safetyReports.isEmpty()) item { TrustMessageCard("No safety reports", "Submitted incident reports and their current status will appear here.") }
                    items(safetyReports, key = { it.optString("id") }) { ReportItem(it, "Safety report") }
                    item { if (accessToken == null) SignInNotice() }
                }
                else -> {
                    item {
                        Text("Verification requests", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    }
                    if (verificationQueue.isEmpty()) {
                        item {
                            TrustMessageCard(
                                "No verification review access or no pending requests",
                                "Only authorized reviewers can inspect evidence and approve or reject requests."
                            )
                        }
                    }
                    items(verificationQueue, key = { "verification:${it.optString("id")}" }) { row ->
                        VerificationReviewItem(
                            row,
                            reviewMessage,
                            onMessageChange = { reviewMessage = it },
                            onReview = { decision ->
                                val token = accessToken ?: return@VerificationReviewItem
                                val body = JSONObject()
                                    .put("decision", decision)
                                    .put("review_note", reviewMessage)
                                perform {
                                    api.send(
                                        "trust/verifications/${row.optString("id")}/review",
                                        "POST",
                                        token,
                                        body
                                    )
                                }
                            }
                        )
                    }
                    item {
                        Text("Fraud and safety reports", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    }
                    item {
                        TrustMessageCard(
                            "Restricted staff tools",
                            "Verification and moderation queues are shown only to accounts with the required review permissions. A reported issue is not proof of misconduct."
                        )
                    }
                    items(moderationRows, key = { it.optString("report_type") + ":" + it.optString("id") }) { row ->
                        ModerationItem(
                            row,
                            reviewMessage,
                            onMessageChange = { reviewMessage = it },
                            onReview = { action ->
                                val token = accessToken ?: return@ModerationItem
                                val body = JSONObject().put("action", action)
                                if (action == "resolved" || action == "dismissed") {
                                    body.put("public_message", reviewMessage)
                                }
                                perform {
                                    api.send(
                                        "trust/moderation/${row.optString("report_type")}/${row.optString("id")}/review",
                                        "POST",
                                        token,
                                        body
                                    )
                                }
                            }
                        )
                    }
                    if (moderationRows.isEmpty()) {
                        item { TrustMessageCard("No review access or no pending reports", "The review queue is available only to authorized moderators.") }
                    }
                    item { if (accessToken == null) SignInNotice() }
                }
            }
            item { Spacer(Modifier.height(12.dp)) }
        }
    }
    SnackbarHost(snackbar, Modifier.fillMaxWidth())

    if (confirmation?.optString("kind") == "incident") {
        AlertDialog(
            onDismissRequest = { confirmation = null },
            title = { Text("Report a safety incident") },
            text = {
                Column(
                    Modifier.verticalScroll(rememberScrollState()),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text("Only authorized reviewers can access these details. A report is a request for review, not a finding.")
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf("viewing_safety", "impersonation", "pressure_or_threat", "payment_request", "privacy", "other").forEach { choice ->
                            FilterChip(incidentCategory == choice, onClick = { incidentCategory = choice }, label = { Text(choice.replace('_', ' ')) })
                        }
                    }
                    OutlinedTextField(incidentViewingId, { incidentViewingId = it }, Modifier.fillMaxWidth(), label = { Text("Viewing ID (optional)") }, singleLine = true)
                    OutlinedTextField(incidentPropertyId, { incidentPropertyId = it }, Modifier.fillMaxWidth(), label = { Text("Property ID (if not linked to viewing)") }, singleLine = true)
                    OutlinedTextField(incidentDetails, { incidentDetails = it }, Modifier.fillMaxWidth(), label = { Text("What happened? (at least 10 characters)") }, minLines = 3)
                }
            },
            confirmButton = {
                TextButton(enabled = incidentDetails.trim().length >= 10, onClick = {
                    val token = accessToken ?: return@TextButton
                    val body = JSONObject()
                        .put("category", incidentCategory)
                        .put("details", incidentDetails.trim())
                        .put("evidence_document_ids", JSONArray().apply { uploads.forEach { put(it.optString("id")) } })
                    if (incidentViewingId.isNotBlank()) body.put("viewing_id", incidentViewingId.trim())
                    else if (incidentPropertyId.isNotBlank()) body.put("property_id", incidentPropertyId.trim())
                    else {
                        error = "Add the viewing ID or listing property ID."
                        return@TextButton
                    }
                    confirmation = null
                    perform { api.send("trust/safety-reports", "POST", token, body) }
                }) { Text("Submit privately") }
            },
            dismissButton = { TextButton(onClick = { confirmation = null }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun TrustMessageCard(title: String, body: String, isError: Boolean = false) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Row(
            Modifier.padding(16.dp),
            horizontalArrangement = Arrangement.spacedBy(12.dp),
            verticalAlignment = Alignment.Top
        ) {
            Icon(
                if (isError) Icons.Filled.Security else Icons.Filled.VerifiedUser,
                contentDescription = null,
                tint = if (isError) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary
            )
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text(body, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun TrustChecklistCard(title: String, points: List<String>) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            points.forEach { point ->
                Row(horizontalArrangement = Arrangement.spacedBy(8.dp), verticalAlignment = Alignment.Top) {
                    Icon(Icons.Filled.CheckCircle, null, tint = MaterialTheme.colorScheme.primary)
                    Text(point, Modifier.weight(1f), color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
        }
    }
}

@Composable
private fun VerificationItem(row: JSONObject) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(
                row.optString("property_title").ifBlank {
                    row.optString("subject_type").replace('_', ' ').replaceFirstChar(Char::uppercase)
                },
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                "Status · ${row.optString("status").replace('_', ' ')} · submission ${row.optInt("submission_number")}",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            row.optString("review_note").takeIf(String::isNotBlank)?.let { Text("Reviewer update: $it") }
            val history = row.optJSONArray("history")
            if (history != null && history.length() > 0) {
                Text(
                    "History · " + (0 until history.length())
                        .mapNotNull { history.optJSONObject(it)?.optString("action") }
                        .joinToString(" → "),
                    style = MaterialTheme.typography.bodySmall
                )
            }
            if ((row.optJSONArray("evidence")?.length() ?: 0) > 0) {
                Text("Private evidence attached", style = MaterialTheme.typography.labelMedium)
            }
        }
    }
}

@Composable
private fun ViewingItem(row: JSONObject, onAction: (String) -> Unit, onReport: (JSONObject) -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text(row.optString("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                row.optString("starts_at").replace('T', ' ') + " · " + row.optString("status").replace('_', ' '),
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                if (row.optBoolean("is_owner")) "Private to you" else "Shared with you by consent",
                style = MaterialTheme.typography.labelMedium
            )
            if (row.optBoolean("is_owner")) {
                Row(horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                    when (row.optString("status")) {
                        "planned" -> {
                            OutlinedButton(onClick = { onAction("check-in") }) { Text("Check in") }
                            OutlinedButton(onClick = { onAction("cancel") }) { Text("Cancel") }
                        }
                        "checked_in" -> OutlinedButton(onClick = { onAction("check-out") }) { Text("Check out") }
                    }
                    TextButton(onClick = { onReport(row) }) { Text("Report issue") }
                }
            }
        }
    }
}

@Composable
private fun ReportItem(row: JSONObject, title: String) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
            Text("Status · ${row.optString("status").replace('_', ' ')}", color = MaterialTheme.colorScheme.onSurfaceVariant)
            row.optString("resolution_message").takeIf(String::isNotBlank)?.let { Text(it) }
            Text(
                "Submitted ${row.optString("created_at").take(10)} · evidence ${row.optJSONArray("evidence_document_ids")?.length() ?: 0}",
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun ModerationItem(
    row: JSONObject,
    reviewMessage: String,
    onMessageChange: (String) -> Unit,
    onReview: (String) -> Unit
) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text(
                row.optString("property_title").ifBlank { row.optString("reason").replace('_', ' ') },
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                "${row.optString("report_type").replace('_', ' ')} · ${row.optString("status").replace('_', ' ')} · ${row.optString("reason").replace('_', ' ')}",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            row.optString("details").takeIf(String::isNotBlank)?.let { Text(it) }
            val signals = row.optJSONArray("signals")
            if (signals != null) for (index in 0 until signals.length()) {
                val signal = signals.optJSONObject(index) ?: continue
                Text(
                    "Review signal · ${signal.optString("label")} · ${signal.optString("detail")}",
                    style = MaterialTheme.typography.bodySmall
                )
            }
            OutlinedTextField(reviewMessage, onMessageChange, Modifier.fillMaxWidth(), label = { Text("Update for reporter") }, minLines = 2)
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                TextButton(onClick = { onReview("in_review") }) { Text("Review") }
                TextButton(onClick = { onReview("escalated") }) { Text("Escalate") }
                TextButton(onClick = { onReview("resolved") }) { Text("Resolve") }
                TextButton(onClick = { onReview("dismissed") }) { Text("Dismiss") }
            }
            Text(
                "Signals are review prompts only; they do not identify a person as a fraudster.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun VerificationReviewItem(
    row: JSONObject,
    reviewNote: String,
    onMessageChange: (String) -> Unit,
    onReview: (String) -> Unit
) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text(
                row.optString("property_title").ifBlank {
                    row.optString("subject_type").replace('_', ' ')
                },
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.SemiBold
            )
            Text(
                "Submitted · ${row.optString("submitted_at").take(10)} · evidence ${row.optJSONArray("evidence")?.length() ?: 0}",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            OutlinedTextField(
                reviewNote,
                onMessageChange,
                Modifier.fillMaxWidth(),
                label = { Text("Reviewer note (required for rejection)") },
                minLines = 2
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                TextButton(onClick = { onReview("approved") }) { Text("Approve") }
                TextButton(onClick = { onReview("rejected") }) { Text("Reject") }
            }
            Text(
                "Approval records a specific check only. Review the submitted evidence before deciding.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun TrustUploadButton(
    enabled: Boolean,
    label: String = "Attach private evidence",
    onClick: () -> Unit
) {
    OutlinedButton(
        enabled = enabled,
        onClick = onClick,
        modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)
    ) {
        Icon(Icons.Filled.AttachFile, contentDescription = null)
        Text(label, modifier = Modifier.padding(start = 8.dp))
    }
}

@Composable
private fun UploadList(files: List<JSONObject>) {
    files.forEach { file ->
        Surface(color = MaterialTheme.colorScheme.surfaceVariant, shape = MaterialTheme.shapes.small) {
            Text(
                "Private file · ${file.optString("original_filename").ifBlank { file.optString("filename") }}",
                Modifier.padding(horizontal = 12.dp, vertical = 8.dp),
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun SignInNotice() {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Text("Sign in to continue", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(
                "Your safety plans, reports, and verification requests are private to your HomeScout account.",
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

private fun JSONArray.objects(): List<JSONObject> =
    (0 until length()).mapNotNull { index -> optJSONObject(index) }
