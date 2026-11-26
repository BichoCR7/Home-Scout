package ke.co.homescout.features.discover

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.lazy.rememberLazyListState
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Bed
import androidx.compose.material.icons.filled.Favorite
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.SwapHoriz
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.animation.core.animateFloatAsState
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.input.nestedscroll.NestedScrollConnection
import androidx.compose.ui.input.nestedscroll.NestedScrollSource
import androidx.compose.ui.input.nestedscroll.nestedScroll
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.Velocity
import androidx.compose.ui.platform.LocalDensity
import android.util.Base64
import org.json.JSONObject
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.MarketplaceApi
import ke.co.homescout.data.remote.MarketplaceApiException
import ke.co.homescout.data.remote.MarketplaceFilters
import ke.co.homescout.data.remote.MarketplaceProperty
import ke.co.homescout.features.home.DemoProperty
import ke.co.homescout.features.home.demoProperties
import ke.co.homescout.ui.components.*
import ke.co.homescout.ui.theme.HomeScoutColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import ke.co.homescout.BuildConfig

@Composable
fun DiscoverScreen(
    onNavigate: (String) -> Unit,
    initialQuery: String = "",
    initialFilters: String = "",
    accessToken: String? = null
) {
    val restoredFilters = remember(initialFilters) {
        runCatching {
            if (initialFilters.isBlank()) JSONObject()
            else JSONObject(String(Base64.decode(initialFilters, Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING), Charsets.UTF_8))
        }.getOrDefault(JSONObject())
    }
    var query by remember(initialQuery, initialFilters) { mutableStateOf(initialQuery.ifBlank { restoredFilters.optString("query") }) }
    var countyId by remember(initialFilters) { mutableStateOf(restoredFilters.optString("county_id").takeIf(String::isNotBlank)) }
    var townId by remember(initialFilters) { mutableStateOf(restoredFilters.optString("town_id").takeIf(String::isNotBlank)) }
    var neighbourhoodId by remember(initialFilters) { mutableStateOf(restoredFilters.optString("neighbourhood_id").takeIf(String::isNotBlank)) }
    var rentMin by remember(initialFilters) { mutableStateOf(restoredFilters.optString("rent_min")) }
    var rentMax by remember(initialFilters) { mutableStateOf(restoredFilters.optString("rent_max")) }
    var bedrooms by remember(initialFilters) {
        mutableStateOf(when {
            restoredFilters.has("bedrooms_min") || restoredFilters.optInt("bedrooms", -1) >= 4 -> "4+ bedrooms"
            restoredFilters.optInt("bedrooms", -1) == 0 -> "Studio / bedsitter"
            restoredFilters.optInt("bedrooms", -1) in 1..3 -> "${restoredFilters.optInt("bedrooms")} bedroom${if (restoredFilters.optInt("bedrooms") == 1) "" else "s"}"
            else -> "Any"
        })
    }
    var propertyType by remember(initialFilters) {
        mutableStateOf(when (restoredFilters.optString("property_type")) {
            "apartment" -> "Apartment"; "house" -> "House"; "maisonette" -> "Maisonette"
            "villa" -> "Villa"; "townhouse" -> "Townhouse"; else -> "All homes"
        })
    }
    var furnishing by remember(initialFilters) {
        mutableStateOf(when (restoredFilters.optString("furnishing")) {
            "furnished" -> "Furnished"; "unfurnished" -> "Unfurnished"
            "semi_furnished" -> "Semi-furnished"; else -> "Any"
        })
    }
    var sortBy by remember(initialFilters) {
        mutableStateOf(when (restoredFilters.optString("sort_by")) {
            "rent_low" -> "Rent: low to high"; "rent_high" -> "Rent: high to low"
            "bedrooms" -> "Bedrooms"; else -> "Newest"
        })
    }
    var verifiedOnly by remember(initialFilters) { mutableStateOf(restoredFilters.optBoolean("verified_only")) }
    var amenities by remember(initialFilters) {
        mutableStateOf(buildSet {
            val items = restoredFilters.optJSONArray("amenities")
            if (items != null) for (index in 0 until items.length()) items.optString(index).takeIf(String::isNotBlank)?.let(::add)
        })
    }
    var properties by remember { mutableStateOf<List<MarketplaceProperty>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var refreshing by remember { mutableStateOf(false) }
    var refreshRequest by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var locationFallbackUsed by remember { mutableStateOf(false) }
    var savedIds by remember { mutableStateOf<Set<String>>(emptySet()) }
    var compareIds by remember { mutableStateOf<List<String>>(emptyList()) }
    var compareResult by remember { mutableStateOf<List<MarketplaceProperty>?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    val snackbar = remember { SnackbarHostState() }
    val scope = rememberCoroutineScope()
    val configured = ApiConfiguration.isConfigured
    val filters = MarketplaceFilters(
        query = query,
        countyId = countyId,
        townId = townId,
        neighbourhoodId = neighbourhoodId,
        rentMin = rentMin,
        rentMax = rentMax,
        bedrooms = when (bedrooms) {
            "Studio / bedsitter" -> 0
            "1 bedroom" -> 1
            "2 bedrooms" -> 2
            "3 bedrooms" -> 3
            else -> null
        },
        bedroomsMin = if (bedrooms == "4+ bedrooms") 4 else null,
        propertyType = when (propertyType) {
            "Apartment" -> "apartment"
            "House" -> "house"
            "Maisonette" -> "maisonette"
            "Villa" -> "villa"
            "Townhouse" -> "townhouse"
            else -> null
        },
        furnishing = when (furnishing) {
            "Furnished" -> "furnished"
            "Unfurnished" -> "unfurnished"
            "Semi-furnished" -> "semi_furnished"
            else -> null
        },
        amenities = amenities.toList(),
        verifiedOnly = verifiedOnly,
        sortBy = when (sortBy) {
            "Rent: low to high" -> "rent_low"
            "Rent: high to low" -> "rent_high"
            "Bedrooms" -> "bedrooms"
            else -> "newest"
        },
        includeDemo = BuildConfig.DEBUG
    )
    val sampleProperties = demoProperties.filter { sample ->
        val localQuery = query.replace("Nairobi City", "Nairobi", ignoreCase = true)
            .replace("Mombasa City", "Mombasa", ignoreCase = true)
            .replace("Kisumu City", "Kisumu", ignoreCase = true)
        val matchesQuery = localQuery.isBlank() || listOf(sample.title, sample.area, sample.type).any { it.contains(localQuery, true) }
        val matchesMin = rentMin.toIntOrNull()?.let { sample.price >= it } ?: true
        val matchesMax = rentMax.toIntOrNull()?.let { sample.price <= it } ?: true
        val matchesBedrooms = when (bedrooms) {
            "Studio / bedsitter" -> sample.beds == 0
            "1 bedroom" -> sample.beds == 1
            "2 bedrooms" -> sample.beds == 2
            "3 bedrooms" -> sample.beds == 3
            "4+ bedrooms" -> sample.beds >= 4
            else -> true
        }
        val matchesType = propertyType == "All homes" || sample.type.equals(propertyType, ignoreCase = true)
        matchesQuery && matchesMin && matchesMax && matchesBedrooms && matchesType &&
            furnishing == "Any" && amenities.isEmpty() && !verifiedOnly
    }

    LaunchedEffect(filters, configured, accessToken, refreshRequest) {
        if (!configured) {
            properties = emptyList()
            error = null
            loading = false
            refreshing = false
            return@LaunchedEffect
        }
        loading = true
        error = null
        locationFallbackUsed = false
        try {
            if (!refreshing) delay(350)
            val (result, usedLocationFallback) = withContext(Dispatchers.IO) {
                val api = MarketplaceApi()
                val exact = api.search(filters)
                if (exact.isNotEmpty() || filters.neighbourhoodId.isNullOrBlank()) {
                    exact to false
                } else {
                    // Some synthetic development listings have county/town data but no
                    // neighbourhood foreign key. Keep the county and town restrictions,
                    // and use the selected neighbourhood name to find those examples.
                    api.search(filters.copy(neighbourhoodId = null)) to true
                }
            }
            properties = result
            locationFallbackUsed = usedLocationFallback
            if (accessToken != null) {
                withContext(Dispatchers.IO) {
                    val recordedFilters = if (usedLocationFallback) filters.copy(neighbourhoodId = null) else filters
                    runCatching { MarketplaceApi().recordSearch(recordedFilters, result.size, accessToken) }
                    savedIds = runCatching { MarketplaceApi().savedPropertyIds(accessToken) }
                        .getOrDefault(savedIds)
                }
            }
        } catch (exception: Exception) {
            error = exception.message ?: "Homes could not be loaded."
            properties = emptyList()
        } finally {
            loading = false
            refreshing = false
        }
    }
    LaunchedEffect(message) {
        message?.let {
            snackbar.showSnackbar(it)
            message = null
        }
    }

    fun requestRefresh() {
        if (loading || refreshing) return
        refreshing = true
        refreshRequest += 1
    }

    val listState = rememberLazyListState()
    val density = LocalDensity.current
    val refreshThresholdPx = with(density) { 72.dp.toPx() }
    var pullDistancePx by remember { mutableFloatStateOf(0f) }
    val refreshConnection = remember(listState, refreshing, loading, refreshThresholdPx) {
        object : NestedScrollConnection {
            override fun onPreScroll(available: Offset, source: NestedScrollSource): Offset {
                if (pullDistancePx > 0f && available.y < 0f) {
                    val released = minOf(pullDistancePx, -available.y)
                    pullDistancePx = (pullDistancePx - released).coerceAtLeast(0f)
                    return Offset(0f, -released)
                }
                return Offset.Zero
            }

            override fun onPostScroll(
                consumed: Offset,
                available: Offset,
                source: NestedScrollSource
            ): Offset {
                if (
                    available.y > 0f && !refreshing && !loading &&
                    listState.firstVisibleItemIndex == 0 && listState.firstVisibleItemScrollOffset == 0
                ) {
                    val accepted = minOf(available.y, refreshThresholdPx * 1.5f - pullDistancePx)
                    if (accepted > 0f) {
                        pullDistancePx += accepted
                        return Offset(0f, accepted)
                    }
                }
                return Offset.Zero
            }

            override suspend fun onPreFling(available: Velocity): Velocity {
                if (pullDistancePx >= refreshThresholdPx && !refreshing && !loading) requestRefresh()
                pullDistancePx = 0f
                return Velocity.Zero
            }
        }
    }

    BoxWithConstraints(Modifier.fillMaxSize()) {
        val width = maxWidth
        val contentWidth = if (width > 960.dp) 920.dp else width
        Box(Modifier.fillMaxSize().nestedScroll(refreshConnection)) {
            LazyColumn(
                state = listState,
                modifier = Modifier.fillMaxSize().widthIn(max = contentWidth).align(Alignment.TopCenter)
                    .padding(horizontal = 18.dp),
                contentPadding = PaddingValues(top = 10.dp, bottom = 28.dp),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                        Text("Find a place to call home", style = MaterialTheme.typography.headlineSmall)
                        Text(
                            "Search homes across Kenya. Development examples are clearly labelled; prices are in KES.",
                            style = MaterialTheme.typography.bodyMedium,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
                item {
                    HomeScoutSearchField(
                        query,
                        { query = it },
                        "Search a county, town or neighbourhood",
                        Modifier.fillMaxWidth(),
                        leading = { Icon(Icons.Filled.Search, null) }
                    )
                }
                item {
                    OutlinedButton(onClick = {
                        query = "Kilimani"
                        rentMin = "60000"
                        rentMax = "80000"
                        bedrooms = "2 bedrooms"
                        propertyType = "Apartment"
                        furnishing = "Any"
                        sortBy = "Rent: low to high"
                        amenities = emptySet()
                        verifiedOnly = false
                    }, modifier = Modifier.fillMaxWidth()) {
                        Text("Fill example search · Kilimani")
                    }
                }
                item {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        HomeScoutDropdown(
                            "Property type",
                            listOf("All homes", "Apartment", "House", "Maisonette", "Villa", "Townhouse"),
                            propertyType,
                            { propertyType = it },
                            Modifier.weight(1f)
                        )
                        HomeScoutDropdown(
                            "Bedrooms",
                            listOf("Any", "Studio / bedsitter", "1 bedroom", "2 bedrooms", "3 bedrooms", "4+ bedrooms"),
                            bedrooms,
                            { bedrooms = it },
                            Modifier.weight(1f)
                        )
                    }
                }
                item {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        OutlinedTextField(
                            rentMin,
                            { rentMin = it.filter(Char::isDigit) },
                            Modifier.weight(1f),
                            label = { Text("Min KSh") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                        )
                        OutlinedTextField(
                            rentMax,
                            { rentMax = it.filter(Char::isDigit) },
                            Modifier.weight(1f),
                            label = { Text("Max KSh") },
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number)
                        )
                    }
                }
                item {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.spacedBy(8.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        HomeScoutDropdown(
                            "Furnishing",
                            listOf("Any", "Furnished", "Unfurnished", "Semi-furnished"),
                            furnishing,
                            { furnishing = it },
                            Modifier.weight(1f)
                        )
                        HomeScoutDropdown(
                            "Sort by",
                            listOf("Newest", "Rent: low to high", "Rent: high to low", "Bedrooms"),
                            sortBy,
                            { sortBy = it },
                            Modifier.weight(1f)
                        )
                    }
                }
                item {
                    Row(
                        Modifier.fillMaxWidth().horizontalScroll(rememberScrollState()),
                        horizontalArrangement = Arrangement.spacedBy(6.dp),
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        listOf("balcony", "parking", "gym", "swimming pool").forEach { amenity ->
                            FilterChip(
                                selected = amenity in amenities,
                                onClick = {
                                    amenities = if (amenity in amenities) amenities - amenity else amenities + amenity
                                },
                                label = { Text(amenity.replaceFirstChar(Char::uppercase)) }
                            )
                        }
                        FilterChip(
                            selected = verifiedOnly,
                            onClick = { verifiedOnly = !verifiedOnly },
                            label = { Text("Verified") }
                        )
                    }
                }
                item {
                    Row(
                        Modifier.fillMaxWidth(),
                        horizontalArrangement = Arrangement.SpaceBetween,
                        verticalAlignment = Alignment.CenterVertically
                    ) {
                        TextButton(onClick = { onNavigate("map") }) {
                            Icon(Icons.Filled.Map, null)
                            Text("Map")
                        }
                        TextButton(onClick = { onNavigate("listing-management") }) {
                            Icon(Icons.Filled.HomeWork, null)
                            Text("List a home")
                        }
                        if (accessToken != null) {
                            TextButton(onClick = {
                                scope.launch {
                                    try {
                                        withContext(Dispatchers.IO) { MarketplaceApi().saveSearchAlert(filters, accessToken) }
                                        message = "Search alert saved. Delivery is not active yet."
                                    } catch (exception: Exception) {
                                        message = exception.message ?: "The alert could not be saved."
                                    }
                                }
                            }) { Text("Save search") }
                        }
                        TextButton(onClick = {
                            query = ""; rentMin = ""; rentMax = ""; bedrooms = "Any"
                            propertyType = "All homes"; furnishing = "Any"; sortBy = "Newest"
                            countyId = null; townId = null; neighbourhoodId = null
                            amenities = emptySet(); verifiedOnly = false
                        }) { Text("Clear filters") }
                    }
                }
                if (query.isNotBlank()) {
                    item {
                        Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.SpaceBetween) {
                            Text("Homes matching “$query”", style = MaterialTheme.typography.titleSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            TextButton(onClick = { query = ""; countyId = null; townId = null; neighbourhoodId = null }) { Text("Clear location") }
                        }
                    }
                }
                if (locationFallbackUsed && properties.isNotEmpty()) {
                    item {
                        Text(
                            "Showing matching homes in this town. Some development listings do not have a neighbourhood tag yet.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }

                if (!configured) {
                    item {
                        HomeScoutBadge(
                            "SAMPLE HOMES · API NOT CONFIGURED",
                            color = HomeScoutColors.navy,
                            background = HomeScoutColors.paleBlue
                        )
                    }
                    if (sampleProperties.isEmpty()) {
                        item { EmptyState("No sample homes match", "Try another area or clear your search.") }
                    } else {
                        items(sampleProperties) { sample ->
                            SamplePropertyCard(sample, onClick = {
                                message = "This offline preview has no listing record to open. Connect the HomeScout API to view property details."
                            })
                        }
                    }
                } else if (loading) {
                    item { LoadingState("Searching homes") }
                } else if (error != null) {
                    item {
                        ErrorState("Homes could not be loaded", error.orEmpty(), onRetry = ::requestRefresh)
                    }
                } else if (properties.isEmpty()) {
                    item {
                        EmptyState(
                            "No matching homes found",
                            "Try a different location, rent range or filter combination. The result count reflects the listings returned by the API."
                        )
                    }
                } else {
                    item {
                        Text(
                            properties.size.toString() + " homes found",
                            modifier = Modifier.padding(vertical = 4.dp),
                            style = MaterialTheme.typography.labelLarge,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                    if (compareIds.size >= 2) {
                        item {
                            HomeScoutPrimaryButton(
                                "Compare " + compareIds.size + " homes",
                                Modifier.fillMaxWidth(),
                                onClick = {
                                    if (accessToken == null) {
                                        onNavigate("profile")
                                    } else {
                                        scope.launch {
                                            try {
                                                compareResult = withContext(Dispatchers.IO) {
                                                    MarketplaceApi().compare(compareIds, accessToken, includeDemo = BuildConfig.DEBUG)
                                                }
                                            } catch (exception: Exception) {
                                                message = exception.message ?: "Homes could not be compared."
                                            }
                                        }
                                    }
                                }
                            )
                        }
                    }
                    items(properties, key = MarketplaceProperty::id) { property ->
                        MarketplacePropertyCard(
                            property = property,
                            saved = property.id in savedIds,
                            compared = property.id in compareIds,
                            canSave = accessToken != null,
                            onClick = { onNavigate("property/" + property.id) },
                            onSave = {
                                val token = accessToken
                                if (token == null) {
                                    onNavigate("profile")
                                } else {
                                    scope.launch {
                                        val newSaved = property.id !in savedIds
                                        try {
                                            withContext(Dispatchers.IO) {
                                                MarketplaceApi().save(property.id, token, newSaved)
                                            }
                                            savedIds = if (newSaved) savedIds + property.id else savedIds - property.id
                                            message = if (newSaved) "Home saved." else "Home removed from saved."
                                        } catch (exception: Exception) {
                                            message = exception.message ?: "Home could not be saved."
                                        }
                                    }
                                }
                            },
                            onCompare = {
                                compareIds = if (property.id in compareIds) {
                                    compareIds - property.id
                                } else if (compareIds.size < 4) {
                                    compareIds + property.id
                                } else {
                                    message = "Compare up to four homes at a time."
                                    compareIds
                                }
                            }
                        )
                    }
                }
            }
            if (refreshing || pullDistancePx > 0f) {
                Surface(
                    modifier = Modifier.align(Alignment.TopCenter)
                        .padding(top = with(density) { (8.dp.toPx() + (pullDistancePx * 0.45f).coerceAtMost(refreshThresholdPx)).toDp() })
                        .size(44.dp),
                    shape = androidx.compose.foundation.shape.CircleShape,
                    color = MaterialTheme.colorScheme.primaryContainer,
                    shadowElevation = 4.dp
                ) {
                    Box(contentAlignment = Alignment.Center) {
                        if (refreshing) {
                            CircularProgressIndicator(Modifier.size(21.dp), strokeWidth = 2.dp)
                        } else {
                            Icon(
                                Icons.Filled.Refresh,
                                contentDescription = if (pullDistancePx >= refreshThresholdPx) "Release to refresh homes" else "Pull down to refresh homes",
                                tint = MaterialTheme.colorScheme.primary
                            )
                        }
                    }
                }
            }
        }
        SnackbarHost(snackbar, Modifier.align(Alignment.BottomCenter))
    }

    compareResult?.let { rows ->
        AlertDialog(
            onDismissRequest = { compareResult = null },
            title = { Text("Compare homes") },
            text = {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    rows.forEach { row ->
                        Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text(row.title, style = MaterialTheme.typography.titleSmall)
                            Text(formatKes(row.rentAmount) + " / " + row.rentFrequency)
                            Text(row.location, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text(
                                row.bedrooms.toString() + " bedrooms · " + row.bathrooms + " baths" +
                                    (row.sizeSqm?.let { " · " + it + " m²" } ?: "")
                            )
                            HorizontalDivider()
                        }
                    }
                }
            },
            confirmButton = { TextButton(onClick = { compareResult = null }) { Text("Done") } }
        )
    }
}

@Composable
internal fun MarketplacePropertyCard(
    property: MarketplaceProperty,
    saved: Boolean,
    compared: Boolean,
    canSave: Boolean,
    onClick: () -> Unit,
    onSave: () -> Unit,
    onCompare: () -> Unit
) {
    val heartScale by animateFloatAsState(
        targetValue = if (saved) 1.08f else 1f,
        label = "saved home heart"
    )
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Box(
            Modifier.fillMaxWidth().height(182.dp)
                .background(Brush.linearGradient(listOf(HomeScoutColors.paleBlue, Color(0xFFCADBE8))))
                .clickable(onClick = onClick),
            contentAlignment = Alignment.Center
        ) {
            val image = property.primaryPhoto
            if (image != null) {
                RemotePhoto(image.url, image.description ?: "Property photo", Modifier.fillMaxSize()) {
                    Icon(Icons.Filled.HomeWork, null, Modifier.size(54.dp), tint = HomeScoutColors.navy.copy(alpha = .65f))
                }
            } else {
                Icon(Icons.Filled.HomeWork, null, Modifier.size(54.dp), tint = HomeScoutColors.navy.copy(alpha = .65f))
            }
            if (property.demo) {
                HomeScoutBadge(
                    "DEMO · NOT AVAILABLE",
                    color = HomeScoutColors.navy,
                    background = Color.White.copy(alpha = .94f),
                    modifier = Modifier.align(Alignment.TopStart).padding(10.dp)
                )
            } else if (property.verificationStatus == "verified") {
                HomeScoutBadge(
                    "VERIFIED",
                    modifier = Modifier.align(Alignment.TopStart).padding(10.dp)
                )
            }
            if (property.availabilityStatus == "available" && !property.demo) {
                HomeScoutBadge(
                    "AVAILABLE",
                    color = HomeScoutColors.greenText,
                    background = Color.White.copy(alpha = .94f),
                    modifier = Modifier.align(Alignment.BottomStart).padding(10.dp)
                )
            }
            IconButton(
                onClick = onSave,
                modifier = Modifier.align(Alignment.TopEnd).padding(4.dp)
                    .graphicsLayer { scaleX = heartScale; scaleY = heartScale }
            ) {
                Icon(
                    if (saved) Icons.Filled.Favorite else Icons.Filled.FavoriteBorder,
                    contentDescription = if (canSave) {
                        if (saved) "Remove saved home" else "Save home"
                    } else {
                        "Sign in to save home"
                    },
                    tint = if (saved) Color(0xFFB42345) else HomeScoutColors.navy
                )
            }
        }
        Column(
            Modifier.fillMaxWidth().clickable(onClick = onClick).padding(horizontal = 14.dp, vertical = 12.dp),
            verticalArrangement = Arrangement.spacedBy(5.dp)
        ) {
            Text(property.title, style = MaterialTheme.typography.titleMedium, maxLines = 2)
            Text(property.location, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                formatKes(property.rentAmount) + " / " + property.rentFrequency,
                style = MaterialTheme.typography.titleMedium,
                color = MaterialTheme.colorScheme.primary
            )
            Row(horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                PropertyFact(Icons.Filled.Bed, property.bedrooms.toString() + " bedrooms")
                PropertyFact(Icons.Filled.HomeWork, property.bathrooms + " baths")
                property.sizeSqm?.let { PropertyFact(Icons.Filled.HomeWork, it + " m²") }
            }
            if (property.amenities.isNotEmpty()) {
                Text(
                    property.amenities.take(3).joinToString(" · "),
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant,
                    maxLines = 1
                )
            }
            if (property.verificationStatus != "verified" && !property.demo) {
                Text("Not verified", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        TextButton(
            onClick = onCompare,
            modifier = Modifier.align(Alignment.End).padding(end = 8.dp, bottom = 3.dp)
        ) {
            Icon(Icons.Filled.SwapHoriz, null)
            Text(if (compared) "Remove compare" else "Compare")
        }
    }
}

@Composable
private fun SamplePropertyCard(property: DemoProperty, onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Box(Modifier.fillMaxWidth().height(160.dp).background(HomeScoutColors.paleBlue), contentAlignment = Alignment.Center) {
            RemotePhoto(property.photo, "Sample home photo", Modifier.fillMaxSize()) {
                Icon(Icons.Filled.HomeWork, null, Modifier.size(50.dp), tint = HomeScoutColors.navy)
            }
            HomeScoutBadge("SAMPLE ONLY", modifier = Modifier.align(Alignment.TopStart).padding(10.dp))
        }
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
            Text(property.title, style = MaterialTheme.typography.titleMedium)
            Text(property.area, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text("KSh " + "%,d".format(property.price) + " / month", style = MaterialTheme.typography.titleMedium, color = MaterialTheme.colorScheme.primary)
            Text("Illustrative sample — not a real or available listing.", style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = onClick) { Text("Why can’t I open this?") }
        }
    }
}

@Composable
private fun PropertyFact(icon: androidx.compose.ui.graphics.vector.ImageVector, label: String) {
    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(4.dp)) {
        Icon(icon, null, Modifier.size(15.dp), tint = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

private fun formatKes(amount: String): String {
    val number = amount.toDoubleOrNull()?.toLong() ?: return "KSh " + amount
    return "KSh " + "%,d".format(number)
}
