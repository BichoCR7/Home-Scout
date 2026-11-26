package ke.co.homescout.features.discover

import android.net.Uri
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AddHome
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.Upload
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.MarketplaceApi
import ke.co.homescout.data.remote.MarketplaceLocation
import ke.co.homescout.data.remote.MarketplaceProperty
import ke.co.homescout.ui.components.*
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

@Composable
fun ListingManagementScreen(
    accessToken: String?,
    onSignIn: () -> Unit,
    onNavigate: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    var listings by remember { mutableStateOf<List<MarketplaceProperty>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var submitting by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var ownerUserId by remember { mutableStateOf("") }
    var title by remember { mutableStateOf("") }
    var description by remember { mutableStateOf("") }
    var rent by remember { mutableStateOf("") }
    var bathrooms by remember { mutableStateOf("1") }
    var bedroomsLabel by remember { mutableStateOf("Bedsitter") }
    var propertyTypeLabel by remember { mutableStateOf("Apartment") }
    var furnishingLabel by remember { mutableStateOf("Unfurnished") }
    var locationQuery by remember { mutableStateOf("") }
    var locationResults by remember { mutableStateOf<List<MarketplaceLocation>>(emptyList()) }
    var selectedLocation by remember { mutableStateOf<MarketplaceLocation?>(null) }
    var selectExampleLocationWhenLoaded by remember { mutableStateOf(false) }
    var uploadTargetId by remember { mutableStateOf<String?>(null) }
    var editTarget by remember { mutableStateOf<MarketplaceProperty?>(null) }
    var editTitle by remember { mutableStateOf("") }
    var editDescription by remember { mutableStateOf("") }
    var editRent by remember { mutableStateOf("") }
    val snackbar = remember { SnackbarHostState() }

    fun loadListings() {
        val token = accessToken ?: return
        scope.launch {
            loading = true
            error = null
            try {
                listings = withContext(Dispatchers.IO) { MarketplaceApi().myListings(token) }
            } catch (exception: Exception) {
                error = exception.message ?: "Your listings could not be loaded."
            } finally {
                loading = false
            }
        }
    }

    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        val token = accessToken
        val propertyId = uploadTargetId
        if (uri != null && token != null && propertyId != null) {
            scope.launch {
                try {
                    val mime = context.contentResolver.getType(uri).orEmpty()
                    val bytes = withContext(Dispatchers.IO) {
                        context.contentResolver.openInputStream(uri)?.use { it.readBytes() }
                            ?: throw IllegalStateException("The selected image could not be opened.")
                    }
                    if (mime !in setOf("image/jpeg", "image/png", "image/webp")) {
                        throw IllegalArgumentException("Choose a JPEG, PNG, or WebP image.")
                    }
                    if (bytes.size > 10_485_760) {
                        throw IllegalArgumentException("Choose an image smaller than 10 MB.")
                    }
                    withContext(Dispatchers.IO) {
                        MarketplaceApi().uploadImage(propertyId, token, mime, bytes)
                    }
                    message = "Listing photo uploaded."
                    loadListings()
                } catch (exception: Exception) {
                    message = exception.message ?: "The listing photo could not be uploaded."
                }
            }
        }
    }

    LaunchedEffect(accessToken) { loadListings() }
    LaunchedEffect(locationQuery) {
        val query = locationQuery.trim()
        if (query.length < 2) {
            locationResults = emptyList()
            return@LaunchedEffect
        }
        delay(250)
        try {
            val results = withContext(Dispatchers.IO) { MarketplaceApi().searchLocations(query) }
            locationResults = results
            if (selectExampleLocationWhenLoaded) {
                val match = results.firstOrNull { it.name.equals("Kilimani", ignoreCase = true) && it.townId != null }
                    ?: results.firstOrNull { it.townId != null }
                if (match != null) {
                    selectedLocation = match
                    locationQuery = listOfNotNull(match.name, match.townName, match.countyName).distinct().joinToString(", ")
                    locationResults = emptyList()
                    selectExampleLocationWhenLoaded = false
                }
            }
        } catch (_: Exception) {
            locationResults = emptyList()
            selectExampleLocationWhenLoaded = false
        }
    }
    LaunchedEffect(message) {
        message?.let {
            snackbar.showSnackbar(it)
            message = null
        }
    }

    if (accessToken == null) {
        EmptyState(
            "Sign in to list a home",
            "Landlords and authorized agents can create and manage listings.",
            Modifier.fillMaxSize()
        )
        HomeScoutPrimaryButton(
            "Open profile",
            Modifier.fillMaxWidth().padding(horizontal = 20.dp),
            onClick = onSignIn
        )
        return
    }

    LazyColumn(
        Modifier.fillMaxSize().padding(horizontal = 18.dp),
        verticalArrangement = Arrangement.spacedBy(12.dp),
        contentPadding = PaddingValues(top = 10.dp, bottom = 24.dp)
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text("Manage listings", style = MaterialTheme.typography.headlineSmall)
                Text(
                    "New listings begin as drafts. Photos, availability and owner permission are checked before publishing.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
        if (error != null) {
            item { ErrorState("Listings unavailable", error.orEmpty(), onRetry = ::loadListings) }
        }
        item {
            ListingDraftForm(
                submitting = submitting,
                onFillExample = {
                    ownerUserId = ""
                    title = "[DEMO DRAFT] Kilimani two-bedroom example"
                    description = "SYNTHETIC PRESENTATION EXAMPLE ONLY. Replace with accurate owner-authorized details before any real use. This draft is not verified or confirmed available."
                    rent = "68000"
                    bathrooms = "2"
                    bedroomsLabel = "2 bedrooms"
                    propertyTypeLabel = "Apartment"
                    furnishingLabel = "Unfurnished"
                    selectedLocation = null
                    locationQuery = "Kilimani"
                    selectExampleLocationWhenLoaded = true
                    message = "Demo draft fields filled. Review and select Create draft only to save this clearly labeled presentation example."
                },
                ownerUserId = ownerUserId,
                onOwnerUserId = { ownerUserId = it },
                title = title,
                onTitle = { title = it },
                description = description,
                onDescription = { description = it },
                rent = rent,
                onRent = { rent = it.filter(Char::isDigit) },
                bathrooms = bathrooms,
                onBathrooms = { bathrooms = it },
                bedroomsLabel = bedroomsLabel,
                onBedroomsLabel = { bedroomsLabel = it },
                propertyTypeLabel = propertyTypeLabel,
                onPropertyTypeLabel = { propertyTypeLabel = it },
                furnishingLabel = furnishingLabel,
                onFurnishingLabel = { furnishingLabel = it },
                locationQuery = locationQuery,
                onLocationQuery = {
                    locationQuery = it
                    selectedLocation = null
                },
                locationResults = locationResults,
                selectedLocation = selectedLocation,
                onSelectLocation = {
                    selectedLocation = it
                    locationQuery = listOfNotNull(it.name, it.townName, it.countyName)
                        .distinct().joinToString(", ")
                    locationResults = emptyList()
                },
                onSubmit = {
                    val token = accessToken
                    if (selectedLocation == null || selectedLocation?.townId == null) {
                        message = "Choose a town or neighbourhood from the Kenyan location results."
                        return@ListingDraftForm
                    }
                    submitting = true
                    scope.launch {
                        try {
                            val unit = when (bedroomsLabel) {
                                "Studio" -> "studio"
                                "1 bedroom" -> "one_bedroom"
                                "2 bedrooms" -> "two_bedroom"
                                "3 bedrooms" -> "three_bedroom"
                                "4 bedrooms" -> "four_bedroom"
                                "5+ bedrooms" -> "five_plus_bedrooms"
                                else -> "bedsitter"
                            }
                            val count = when (unit) {
                                "one_bedroom" -> 1
                                "two_bedroom" -> 2
                                "three_bedroom" -> 3
                                "four_bedroom" -> 4
                                "five_plus_bedrooms" -> 5
                                else -> 0
                            }
                            val type = when (propertyTypeLabel) {
                                "House" -> "house"
                                "Maisonette" -> "maisonette"
                                "Villa" -> "villa"
                                "Townhouse" -> "townhouse"
                                else -> "apartment"
                            }
                            val furnishing = when (furnishingLabel) {
                                "Furnished" -> "furnished"
                                "Semi-furnished" -> "semi_furnished"
                                else -> "unfurnished"
                            }
                            val location = selectedLocation!!
                            val body = JSONObject()
                                .put("title", title)
                                .put("description", description)
                                .put("property_type", type)
                                .put("accommodation_type", "whole_property")
                                .put("unit_type", unit)
                                .put("rent_amount", rent)
                                .put("rent_frequency", "monthly")
                                .put("bedrooms", count)
                                .put("bathrooms", bathrooms)
                                .put("furnishing", furnishing)
                                .put("county_id", location.countyId)
                                .put("town_id", location.townId)
                                .put("amenities", org.json.JSONArray())
                                .put("security_features", org.json.JSONArray())
                            if (location.neighbourhoodId != null) {
                                body.put("neighbourhood_id", location.neighbourhoodId)
                            }
                            if (ownerUserId.isNotBlank()) body.put("owner_user_id", ownerUserId.trim())
                            val created = withContext(Dispatchers.IO) {
                                MarketplaceApi().createDraft(token, body)
                            }
                            message = "Draft created. Add a property photo before publishing."
                            title = ""
                            description = ""
                            rent = ""
                            ownerUserId = ""
                            loadListings()
                            uploadTargetId = created.id
                        } catch (exception: Exception) {
                            message = exception.message ?: "The draft could not be created."
                        } finally {
                            submitting = false
                        }
                    }
                }
            )
        }
        item { SectionHeading("Your listings") }
        if (loading) {
            item { LoadingState("Loading listings") }
        } else if (listings.isEmpty()) {
            item {
                EmptyState(
                    "No listings yet",
                    "Your drafts, published homes and assigned listings will appear here."
                )
            }
        } else {
            items(listings, key = MarketplaceProperty::id) { property ->
                ListingManagementCard(
                    property = property,
                    onUpload = {
                        uploadTargetId = property.id
                        imagePicker.launch("image/*")
                    },
                    onAvailable = {
                        runListingAction(scope, {
                            MarketplaceApi().updateAvailability(property.id, accessToken, true)
                        }, ::loadListings, { message = it })
                    },
                    onUnavailable = {
                        runListingAction(scope, {
                            MarketplaceApi().updateAvailability(property.id, accessToken, false)
                        }, ::loadListings, { message = it })
                    },
                    onPublish = {
                        runListingAction(scope, {
                            MarketplaceApi().publish(property.id, accessToken)
                        }, ::loadListings, { message = it })
                    },
                    onArchive = {
                        runListingAction(scope, {
                            MarketplaceApi().archive(property.id, accessToken)
                        }, ::loadListings, { message = it })
                    },
                    onDelete = {
                        runListingAction(scope, {
                            MarketplaceApi().deleteDraft(property.id, accessToken)
                        }, ::loadListings, { message = "Draft deleted." })
                    },
                    onEdit = {
                        editTarget = property
                        editTitle = property.title
                        editDescription = property.description
                        editRent = property.rentAmount.substringBefore('.')
                    },
                    onPreview = { onNavigate("property-preview/" + property.id) }
                )
            }
        }
    }
    SnackbarHost(snackbar, Modifier.fillMaxWidth())

    editTarget?.let { target ->
        AlertDialog(
            onDismissRequest = { editTarget = null },
            title = { Text("Edit listing details") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    OutlinedTextField(editTitle, { editTitle = it }, label = { Text("Title") })
                    OutlinedTextField(
                        editDescription,
                        { editDescription = it },
                        label = { Text("Description") },
                        minLines = 3
                    )
                    OutlinedTextField(
                        editRent,
                        { editRent = it.filter(Char::isDigit) },
                        label = { Text("Monthly rent (KSh)") },
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                    )
                }
            },
            confirmButton = {
                TextButton(onClick = {
                    editTarget = null
                    scope.launch {
                        try {
                            withContext(Dispatchers.IO) {
                                MarketplaceApi().updateDraft(
                                    target.id, accessToken, editTitle, editDescription, editRent
                                )
                            }
                            message = "Listing updated."
                            loadListings()
                        } catch (exception: Exception) {
                            message = exception.message ?: "The listing could not be updated."
                        }
                    }
                }) { Text("Save changes") }
            },
            dismissButton = { TextButton(onClick = { editTarget = null }) { Text("Cancel") } }
        )
    }
}

@Composable
private fun ListingDraftForm(
    submitting: Boolean,
    onFillExample: () -> Unit,
    ownerUserId: String,
    onOwnerUserId: (String) -> Unit,
    title: String,
    onTitle: (String) -> Unit,
    description: String,
    onDescription: (String) -> Unit,
    rent: String,
    onRent: (String) -> Unit,
    bathrooms: String,
    onBathrooms: (String) -> Unit,
    bedroomsLabel: String,
    onBedroomsLabel: (String) -> Unit,
    propertyTypeLabel: String,
    onPropertyTypeLabel: (String) -> Unit,
    furnishingLabel: String,
    onFurnishingLabel: (String) -> Unit,
    locationQuery: String,
    onLocationQuery: (String) -> Unit,
    locationResults: List<MarketplaceLocation>,
    selectedLocation: MarketplaceLocation?,
    onSelectLocation: (MarketplaceLocation) -> Unit,
    onSubmit: () -> Unit
) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                Icon(Icons.Filled.AddHome, null, tint = MaterialTheme.colorScheme.primary)
                Text("Create a listing draft", style = MaterialTheme.typography.titleLarge)
            }
            OutlinedButton(onClick = onFillExample, enabled = !submitting, modifier = Modifier.fillMaxWidth()) {
                Text("Fill presentation example · clearly marked draft")
            }
            OutlinedTextField(title, onTitle, Modifier.fillMaxWidth(), label = { Text("Listing title") }, singleLine = true)
            OutlinedTextField(
                description,
                onDescription,
                Modifier.fillMaxWidth(),
                label = { Text("Description") },
                minLines = 3,
                maxLines = 5
            )
            OutlinedTextField(
                rent,
                onRent,
                Modifier.fillMaxWidth(),
                label = { Text("Monthly rent (KSh)") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
            )
            HomeScoutDropdown(
                "Property type",
                listOf("Apartment", "House", "Maisonette", "Villa", "Townhouse"),
                propertyTypeLabel,
                onPropertyTypeLabel
            )
            HomeScoutDropdown(
                "Bedrooms",
                listOf("Bedsitter", "Studio", "1 bedroom", "2 bedrooms", "3 bedrooms", "4 bedrooms", "5+ bedrooms"),
                bedroomsLabel,
                onBedroomsLabel
            )
            OutlinedTextField(
                bathrooms,
                onBathrooms,
                Modifier.fillMaxWidth(),
                label = { Text("Bathrooms") },
                keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal)
            )
            HomeScoutDropdown(
                "Furnishing",
                listOf("Unfurnished", "Furnished", "Semi-furnished"),
                furnishingLabel,
                onFurnishingLabel
            )
            OutlinedTextField(
                locationQuery,
                onLocationQuery,
                Modifier.fillMaxWidth(),
                label = { Text("Kenyan town or neighbourhood") },
                placeholder = { Text("Search e.g. Kilimani or Ruaka") }
            )
            selectedLocation?.let {
                HomeScoutBadge(
                    "Selected · " + it.name + (it.townName?.let { town -> ", " + town } ?: "") +
                        ", " + it.countyName
                )
            }
            locationResults.filter { it.townId != null }.take(6).forEach { result ->
                TextButton(
                    onClick = { onSelectLocation(result) },
                    modifier = Modifier.fillMaxWidth()
                ) {
                    Column(Modifier.fillMaxWidth()) {
                        Text(result.name)
                        Text(
                            listOfNotNull(result.townName, result.countyName).distinct().joinToString(", "),
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
            OutlinedTextField(
                ownerUserId,
                onOwnerUserId,
                Modifier.fillMaxWidth(),
                label = { Text("Owner account ID (agent mandate, optional)") },
                supportingText = { Text("Leave blank for your own landlord listing.") },
                singleLine = true
            )
            HomeScoutPrimaryButton(
                if (submitting) "Creating draft…" else "Create draft",
                Modifier.fillMaxWidth(),
                onClick = onSubmit
            )
        }
    }
}

@Composable
private fun ListingManagementCard(
    property: MarketplaceProperty,
    onUpload: () -> Unit,
    onAvailable: () -> Unit,
    onUnavailable: () -> Unit,
    onPublish: () -> Unit,
    onArchive: () -> Unit,
    onDelete: () -> Unit,
    onEdit: () -> Unit,
    onPreview: () -> Unit
) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(15.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.HomeWork, null, tint = MaterialTheme.colorScheme.primary)
                Column(Modifier.weight(1f)) {
                    Text(property.title, style = MaterialTheme.typography.titleMedium)
                    Text(
                        property.location + " · KSh " + property.rentAmount,
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                HomeScoutBadge(property.listingStatus.replace('_', ' ').uppercase())
            }
            Text(
                "Availability: " + property.availabilityStatus.replace('_', ' ') +
                    " · Verification: " + property.verificationStatus.replace('_', ' '),
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Row(
                Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                horizontalArrangement = Arrangement.spacedBy(5.dp),
                verticalAlignment = Alignment.CenterVertically
            ) {
                TextButton(onClick = onUpload) { Icon(Icons.Filled.Upload, null); Text("Add photo") }
                TextButton(onClick = onEdit) { Icon(Icons.Filled.Edit, null); Text("Edit") }
                TextButton(onClick = onPreview) { Text("Preview") }
                if (property.availabilityStatus != "available") {
                    TextButton(onClick = onAvailable) { Text("Mark available") }
                } else {
                    TextButton(onClick = onUnavailable) { Text("Mark unavailable") }
                }
                TextButton(onClick = onPublish) { Text("Publish") }
                TextButton(onClick = onArchive) { Text("Archive") }
                if (property.listingStatus == "draft") TextButton(onClick = onDelete) { Text("Delete draft") }
            }
            if (property.listingStatus == "draft") {
                Text(
                    "A real listing photo is required before publishing. Publishing does not mark the property as verified.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }
    }
}

private fun runListingAction(
    scope: kotlinx.coroutines.CoroutineScope,
    action: () -> Unit,
    refresh: () -> Unit,
    showMessage: (String) -> Unit
) {
    scope.launch {
        try {
            withContext(Dispatchers.IO) { action() }
            showMessage("Listing updated.")
            refresh()
        } catch (exception: Exception) {
            showMessage(exception.message ?: "The listing could not be updated.")
        }
    }
}
