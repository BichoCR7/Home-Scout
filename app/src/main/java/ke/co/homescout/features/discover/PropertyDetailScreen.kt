package ke.co.homescout.features.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Bed
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.ReportProblem
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.input.KeyboardCapitalization
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.AuthApiException
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.MarketplaceApi
import ke.co.homescout.BuildConfig
import ke.co.homescout.data.remote.MarketplaceFilters
import ke.co.homescout.data.remote.MarketplaceProperty
import ke.co.homescout.data.remote.PersonalHubApi
import ke.co.homescout.ui.components.*
import ke.co.homescout.ui.theme.HomeScoutColors
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.io.IOException

private suspend fun loadPropertyWithRetry(
    propertyId: String,
    accessToken: String?,
    previewOnly: Boolean
): MarketplaceProperty {
    var attempt = 0
    while (attempt < 2) {
        try {
            return withContext(Dispatchers.IO) {
                val api = MarketplaceApi()
                if (previewOnly) {
                    api.preview(propertyId, checkNotNull(accessToken))
                } else {
                    api.property(propertyId, includeDemo = BuildConfig.DEBUG)
                }
            }
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (failure: Exception) {
            attempt += 1
            val temporaryFailure = failure is IOException ||
                (failure is AuthApiException && failure.statusCode in setOf(408, 429, 500, 502, 503, 504))
            if (!temporaryFailure || attempt >= 2) throw failure
            delay(400L)
        }
    }
    error("Property could not be loaded.")
}

private suspend fun <T> optionalPropertyData(fallback: T, load: suspend () -> T): T =
    try {
        load()
    } catch (cancelled: CancellationException) {
        throw cancelled
    } catch (_: Exception) {
        fallback
    }

@Composable
fun PropertyDetailScreen(
    propertyId: String,
    accessToken: String?,
    previewOnly: Boolean = false,
    onBack: () -> Unit,
    onNavigate: (String) -> Unit
) {
    var property by remember(propertyId) { mutableStateOf<MarketplaceProperty?>(null) }
    var trustIndicators by remember(propertyId) { mutableStateOf(JSONObject()) }
    var similar by remember(propertyId) { mutableStateOf<List<MarketplaceProperty>>(emptyList()) }
    var loading by remember(propertyId) { mutableStateOf(true) }
    var error by remember(propertyId) { mutableStateOf<String?>(null) }
    var saved by remember(propertyId) { mutableStateOf(false) }
    var showEnquiry by remember { mutableStateOf(false) }
    var showReport by remember { mutableStateOf(false) }
    var enquiryText by remember { mutableStateOf("") }
    var reportDetails by remember { mutableStateOf("") }
    var reportReason by remember { mutableStateOf("inaccurate_details") }
    var message by remember { mutableStateOf<String?>(null) }
    var compareResult by remember { mutableStateOf<List<MarketplaceProperty>?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val configured = ApiConfiguration.isConfigured

    LaunchedEffect(propertyId, configured, accessToken, previewOnly) {
        if (!configured) {
            loading = false
            error = "The HomeScout API address is not configured."
            return@LaunchedEffect
        }
        if (previewOnly && accessToken == null) {
            loading = false
            error = "Sign in with the listing owner or an authorized account to preview this home."
            return@LaunchedEffect
        }
        loading = true
        error = null
        try {
            val listing = loadPropertyWithRetry(propertyId, accessToken, previewOnly)
            property = listing
            loading = false
            error = null

            // Optional related data must never prevent the selected listing from opening.
            similar = if (previewOnly) emptyList() else withContext(Dispatchers.IO) {
                optionalPropertyData(emptyList()) { MarketplaceApi().similar(propertyId) }
            }
            trustIndicators = if (previewOnly) JSONObject() else withContext(Dispatchers.IO) {
                optionalPropertyData(JSONObject()) {
                    PersonalHubApi().getPublicObject("trust/indicators/$propertyId")
                }
            }
            if (!previewOnly && accessToken != null) {
                val viewed = listing
                scope.launch(Dispatchers.IO) {
                    runCatching {
                        PersonalHubApi().send(
                            "hub/activity",
                            "POST",
                            accessToken,
                            JSONObject()
                                .put("event_type", "property_view")
                                .put("title", "Viewed ${viewed.title}")
                                .put("details", viewed.location)
                                .put("target_path", "/property/$propertyId")
                        )
                    }
                }
            }
            saved = !previewOnly && accessToken != null && withContext(Dispatchers.IO) {
                optionalPropertyData(false) { MarketplaceApi().savedPropertyIds(accessToken).contains(propertyId) }
            }
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (exception: Exception) {
            error = exception.message ?: "This home could not be opened."
        } finally {
            loading = false
        }
    }
    LaunchedEffect(message) {
        message?.let {
            snackbar.showSnackbar(it)
            message = null
        }
    }

    Column(Modifier.fillMaxSize()) {
        Row(
            Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 4.dp),
            verticalAlignment = Alignment.CenterVertically
        ) {
            IconButton(onClick = onBack) {
                Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to homes")
            }
            Text(if (previewOnly) "Listing preview" else "Home details", style = MaterialTheme.typography.titleLarge)
        }
        when {
            loading -> LoadingState("Loading home details")
            error != null -> ErrorState("Home unavailable", error.orEmpty(), onRetry = {
                loading = true
                scope.launch {
                    try {
                        property = loadPropertyWithRetry(propertyId, accessToken, previewOnly)
                        error = null
                    } catch (cancelled: CancellationException) {
                        throw cancelled
                    } catch (exception: Exception) {
                        error = exception.message
                    } finally {
                        loading = false
                    }
                }
            })
            property != null -> PropertyDetailsContent(
                property = property!!,
                similar = similar,
                trustIndicators = trustIndicators,
                saved = saved,
                previewOnly = previewOnly,
                onSave = {
                    val token = accessToken
                    if (token == null) {
                        onNavigate("profile")
                    } else {
                        scope.launch {
                            val newSaved = !saved
                            try {
                                withContext(Dispatchers.IO) { MarketplaceApi().save(propertyId, token, newSaved) }
                                saved = newSaved
                                message = if (newSaved) "Home saved." else "Home removed from saved."
                            } catch (exception: Exception) {
                                message = exception.message ?: "Home could not be saved."
                            }
                        }
                    }
                },
                onEnquire = {
                    if (accessToken == null) onNavigate("profile") else showEnquiry = true
                },
                onReport = {
                    if (accessToken == null) onNavigate("profile") else showReport = true
                },
                onPlanViewing = {
                    if (accessToken == null) onNavigate("profile")
                    else onNavigate("trust-safety?propertyId=${PersonalHubApi.query(propertyId)}")
                },
                onRequestViewing = {
                    if (accessToken == null) onNavigate("profile")
                    else onNavigate("collaboration?propertyId=${PersonalHubApi.query(propertyId)}&tab=Viewings")
                },
                onSaveComparison = {
                    if (accessToken == null) onNavigate("profile")
                    else onNavigate("collaboration?propertyId=${PersonalHubApi.query(propertyId)}&tab=Compare")
                },
                onAskAssistant = {
                    onNavigate("assistant?propertyId=" + propertyId + "&intent=property_explanation")
                },
                onMap = { onNavigate("map") },
                onCompare = { otherId ->
                    val token = accessToken
                    if (token == null) {
                        onNavigate("profile")
                    } else {
                        scope.launch {
                            try {
                                compareResult = withContext(Dispatchers.IO) {
                                    MarketplaceApi().compare(listOf(propertyId, otherId), token, includeDemo = BuildConfig.DEBUG)
                                }
                            } catch (exception: Exception) {
                                message = exception.message ?: "Homes could not be compared."
                            }
                        }
                    }
                },
                onOpenSimilar = { onNavigate("property/" + it) }
            )
            else -> EmptyState("Home not found", "It may no longer be published.", Modifier.weight(1f))
        }
    }
    SnackbarHost(snackbar, Modifier.fillMaxWidth())

    if (showEnquiry) {
        AlertDialog(
            onDismissRequest = { showEnquiry = false },
            title = { Text("Message about this home") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    TextButton(onClick = {
                        enquiryText = "Hello, I’m interested in this home. Could you share the viewing options and any details I should confirm before visiting?"
                    }) { Text("Fill example enquiry") }
                    OutlinedTextField(
                        value = enquiryText,
                        onValueChange = { enquiryText = it },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("Your message") },
                        placeholder = { Text("Ask about a viewing or property details") },
                        minLines = 3,
                        maxLines = 5,
                        keyboardOptions = KeyboardOptions(capitalization = KeyboardCapitalization.Sentences)
                    )
                }
            },
            confirmButton = {
                TextButton(
                    enabled = enquiryText.trim().length >= 10,
                    onClick = {
                        val token = accessToken ?: return@TextButton
                        showEnquiry = false
                        scope.launch {
                            try {
                                val enquiryMessage = enquiryText
                                val conversationId = withContext(Dispatchers.IO) {
                                    val enquiryId = MarketplaceApi().createEnquiry(propertyId, token, enquiryMessage)
                                    PersonalHubApi().send(
                                        "communications/property-enquiries/$enquiryId/conversation",
                                        "POST",
                                        token
                                    ).optString("id")
                                }
                                enquiryText = ""
                                message = "Your enquiry was sent. Your private chat with the authorized listing contact is ready."
                                if (conversationId.isNotBlank()) {
                                    onNavigate("collaboration?conversationId=${PersonalHubApi.query(conversationId)}&tab=Messages")
                                }
                            } catch (exception: Exception) {
                                message = exception.message ?: "Your enquiry could not be sent."
                            }
                        }
                    }
                ) { Text("Send enquiry") }
            },
            dismissButton = { TextButton(onClick = { showEnquiry = false }) { Text("Cancel") } }
        )
    }

    if (showReport) {
        AlertDialog(
            onDismissRequest = { showReport = false },
            title = { Text("Report this listing") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Choose a reason. A report is recorded for review; this screen does not show a moderation outcome.")
                    listOf(
                        "inaccurate_details" to "Inaccurate details",
                        "suspected_scam" to "Possible scam",
                        "unsafe_or_prohibited" to "Unsafe or prohibited",
                        "duplicate" to "Duplicate listing",
                        "other" to "Other"
                    ).forEach { (value, label) ->
                        Row(
                            Modifier.fillMaxWidth().clickable { reportReason = value },
                            verticalAlignment = Alignment.CenterVertically
                        ) {
                            RadioButton(selected = reportReason == value, onClick = { reportReason = value })
                            Text(label)
                        }
                    }
                    OutlinedTextField(
                        reportDetails,
                        { reportDetails = it },
                        Modifier.fillMaxWidth(),
                        label = { Text("Details (optional)") },
                        minLines = 2,
                        maxLines = 4
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    val token = accessToken ?: return@TextButton
                    showReport = false
                    scope.launch {
                        try {
                            val result = withContext(Dispatchers.IO) {
                                MarketplaceApi().report(propertyId, token, reportReason, reportDetails)
                            }
                            message = "Report " + result + "."
                            reportDetails = ""
                        } catch (exception: Exception) {
                            message = exception.message ?: "The report could not be submitted."
                        }
                    }
                }) { Text("Submit report") }
            },
            dismissButton = { TextButton(onClick = { showReport = false }) { Text("Cancel") } }
        )
    }

    compareResult?.let { rows ->
        AlertDialog(
            onDismissRequest = { compareResult = null },
            title = { Text("Compare homes") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    rows.forEach { row ->
                        Text(
                            row.title + "\n" + formatKes(row.rentAmount) + " / " + row.rentFrequency +
                                "\n" + row.location + "\n" + row.bedrooms + " bedrooms · " +
                                row.bathrooms + " baths"
                        )
                        HorizontalDivider()
                    }
                }
            },
            confirmButton = { TextButton(onClick = { compareResult = null }) { Text("Done") } }
        )
    }
}

@Composable
private fun PropertyDetailsContent(
    property: MarketplaceProperty,
    similar: List<MarketplaceProperty>,
    trustIndicators: JSONObject,
    saved: Boolean,
    previewOnly: Boolean,
    onSave: () -> Unit,
    onEnquire: () -> Unit,
    onReport: () -> Unit,
    onPlanViewing: () -> Unit,
    onRequestViewing: () -> Unit,
    onSaveComparison: () -> Unit,
    onAskAssistant: () -> Unit,
    onMap: () -> Unit,
    onCompare: (String) -> Unit,
    onOpenSimilar: (String) -> Unit
) {
    Column(
        Modifier.fillMaxSize().padding(horizontal = 18.dp).verticalScroll(rememberScrollState()),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        if (property.photos.isNotEmpty()) {
            Row(
                Modifier.fillMaxWidth().height(238.dp).horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                property.photos.forEach { photo ->
                    Box(
                        Modifier.width(320.dp).fillMaxHeight()
                            .background(Brush.linearGradient(listOf(HomeScoutColors.paleBlue, Color(0xFFCADBE8))))
                    ) {
                        RemotePhoto(photo.url, photo.description ?: "Property image", Modifier.fillMaxSize()) {
                            Icon(Icons.Filled.HomeWork, null, Modifier.size(54.dp), tint = HomeScoutColors.navy)
                        }
                        if (photo.illustrative) {
                            HomeScoutBadge(
                                "ILLUSTRATIVE PHOTO",
                                modifier = Modifier.align(Alignment.TopStart).padding(10.dp)
                            )
                        }
                    }
                }
            }
        } else {
            Box(
                Modifier.fillMaxWidth().height(210.dp)
                    .background(Brush.linearGradient(listOf(HomeScoutColors.paleBlue, Color(0xFFCADBE8)))),
                contentAlignment = Alignment.Center
            ) {
                Icon(Icons.Filled.HomeWork, null, Modifier.size(70.dp), tint = HomeScoutColors.navy.copy(alpha = .7f))
            }
        }
        if (property.demo) {
            HomeScoutBadge(
                "DEMO ONLY · NOT A REAL OR AVAILABLE HOME",
                color = HomeScoutColors.navy,
                background = HomeScoutColors.paleBlue
            )
        }
        if (previewOnly) {
            HomeScoutBadge(
                "PRIVATE LISTING PREVIEW · " + property.listingStatus.replace('_', ' ').uppercase(),
                color = HomeScoutColors.navy,
                background = HomeScoutColors.paleBlue
            )
        }
        Row(
            Modifier.fillMaxWidth(),
            horizontalArrangement = Arrangement.SpaceBetween,
            verticalAlignment = Alignment.Top
        ) {
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text(property.title, style = MaterialTheme.typography.headlineSmall)
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                    Icon(Icons.Filled.LocationOn, null, Modifier.size(17.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(property.location, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
            }
            if (!previewOnly) {
                IconButton(onClick = onSave) {
                    Icon(
                        if (saved) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                        contentDescription = if (saved) "Remove saved home" else "Save home",
                        tint = if (saved) Color(0xFFB42345) else MaterialTheme.colorScheme.primary
                    )
                }
            }
        }
        Text(
            formatKes(property.rentAmount) + " / " + property.rentFrequency,
            style = MaterialTheme.typography.headlineSmall,
            color = MaterialTheme.colorScheme.primary
        )
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(12.dp)) {
            PropertyDetailsFact(Icons.Filled.Bed, property.bedrooms.toString() + " bedrooms")
            PropertyDetailsFact(Icons.Filled.HomeWork, property.bathrooms + " bathrooms")
            property.sizeSqm?.let { PropertyDetailsFact(Icons.Filled.HomeWork, it + " m²") }
        }
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Text("Listing details", style = MaterialTheme.typography.titleLarge)
                DetailLine("Property type", property.propertyType.replace('_', ' '))
                DetailLine("Furnishing", property.furnishing.replace('_', ' '))
                DetailLine("Deposit", property.depositAmount?.let(::formatKes) ?: "Not specified")
                DetailLine("Availability", property.availabilityStatus.replace('_', ' '))
                DetailLine(
                    "Property review",
                    trustIndicators.optString("property_verification")
                        .ifBlank { "not_submitted" }
                        .replace('_', ' ')
                        .replaceFirstChar(Char::uppercase)
                )
                DetailLine(
                    "Listing contact account check",
                    trustIndicators.optString("listing_contact_account_check")
                        .ifBlank { "not_verified" }
                        .replace('_', ' ')
                        .replaceFirstChar(Char::uppercase)
                )
                DetailLine(
                    "Authorized agent account check",
                    trustIndicators.optString("authorized_agent_account_check")
                        .ifBlank { "not_verified" }
                        .replace('_', ' ')
                        .replaceFirstChar(Char::uppercase)
                )
                Text(
                    trustIndicators.optString("note").ifBlank {
                        "Verification is shown only when HomeScout records a completed reviewer check."
                    },
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                DetailLine("Water", property.waterAvailability.replace('_', ' '))
                property.electricityAvailable?.let { DetailLine("Electricity", if (it) "Available" else "Not available") }
                property.internetAvailable?.let { DetailLine("Internet", if (it) "Available" else "Not available") }
                DetailLine(
                    "Pets",
                    if (property.petPolicy == "unknown") "Ask the listing contact"
                    else property.petPolicy.replace('_', ' ')
                )
            }
        }
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("About this home", style = MaterialTheme.typography.titleLarge)
                Text(property.description, style = MaterialTheme.typography.bodyMedium)
            }
        }
        if (property.amenities.isNotEmpty()) {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Amenities", style = MaterialTheme.typography.titleLarge)
                    Text(property.amenities.joinToString(" · "))
                }
            }
        }
        if (property.securityFeatures.isNotEmpty()) {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Security information", style = MaterialTheme.typography.titleLarge)
                    Text(property.securityFeatures.joinToString(" · "))
                }
            }
        }
        if (!previewOnly) {
            HomeScoutOutlinedButton(
                "Ask HomeScout Assistant about this home",
                Modifier.fillMaxWidth(),
                onClick = onAskAssistant
            )
            HomeScoutOutlinedButton("View homes on map", Modifier.fillMaxWidth(), onClick = onMap)
            HomeScoutOutlinedButton("Plan a safer viewing", Modifier.fillMaxWidth(), onClick = onPlanViewing)
            HomeScoutOutlinedButton("Request a viewing time", Modifier.fillMaxWidth(), onClick = onRequestViewing)
            HomeScoutOutlinedButton("Save to a comparison", Modifier.fillMaxWidth(), onClick = onSaveComparison)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                HomeScoutPrimaryButton("Message about this home", Modifier.weight(1f), onClick = onEnquire)
                IconButton(onClick = onReport) {
                    Icon(Icons.Filled.ReportProblem, contentDescription = "Report this listing", tint = MaterialTheme.colorScheme.error)
                }
            }
        }
        if (!previewOnly && similar.isNotEmpty()) {
            SectionHeading("Similar homes")
            similar.forEach { other ->
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Row(
                        Modifier.fillMaxWidth().clickable { onOpenSimilar(other.id) }.padding(12.dp),
                        horizontalArrangement = Arrangement.spacedBy(12.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        Box(
                            Modifier.size(width = 96.dp, height = 76.dp)
                                .background(HomeScoutColors.paleBlue)
                        ) {
                            other.primaryPhoto?.let { photo ->
                                RemotePhoto(photo.url, "Similar home", Modifier.fillMaxSize()) {
                                    Icon(Icons.Filled.HomeWork, null, tint = HomeScoutColors.navy)
                                }
                            } ?: Icon(Icons.Filled.HomeWork, null, Modifier.align(Alignment.Center))
                        }
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                            Text(other.title, style = MaterialTheme.typography.titleSmall, maxLines = 2)
                            Text(other.location, style = MaterialTheme.typography.bodySmall)
                            Text(formatKes(other.rentAmount) + " / " + other.rentFrequency, color = MaterialTheme.colorScheme.primary)
                        }
                        IconButton(onClick = { onCompare(other.id) }) {
                            Icon(Icons.Filled.SwapHoriz, contentDescription = "Compare with this home")
                        }
                    }
                }
            }
        }
        Spacer(Modifier.height(24.dp))
    }
}

@Composable
private fun PropertyDetailsFact(icon: androidx.compose.ui.graphics.vector.ImageVector, text: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Icon(icon, null, Modifier.size(17.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(text, style = MaterialTheme.typography.bodySmall)
    }
}

@Composable
private fun DetailLine(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(value, style = MaterialTheme.typography.bodyMedium)
    }
}

private fun formatKes(amount: String): String {
    val number = amount.toDoubleOrNull()?.toLong() ?: return "KSh " + amount
    return "KSh " + "%,d".format(number)
}
