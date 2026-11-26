package ke.co.homescout.features.map

import android.Manifest
import android.content.pm.PackageManager
import android.location.Location
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Check
import androidx.compose.material.icons.filled.FilterList
import androidx.compose.material.icons.filled.Fullscreen
import androidx.compose.material.icons.filled.FullscreenExit
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.List
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.MyLocation
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.compose.ui.viewinterop.AndroidView
import androidx.core.content.ContextCompat
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import com.google.android.gms.location.LocationServices
import ke.co.homescout.ui.components.homeScoutSuccessTextColor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.maplibre.android.MapLibre
import org.maplibre.android.annotations.MarkerOptions
import org.maplibre.android.camera.CameraPosition
import org.maplibre.android.camera.CameraUpdateFactory
import org.maplibre.android.geometry.LatLng
import org.maplibre.android.maps.MapLibreMap
import org.maplibre.android.maps.MapView
import org.maplibre.android.maps.Style

private data class MapArea(val viewport: MapViewport, val center: LatLng)
private enum class ListingPresentation { Map, List }

@Composable
fun MapScreen(
    onBrowseDiscover: () -> Unit,
    onFullscreenChange: (Boolean) -> Unit,
    onOpenProperty: (String) -> Unit
) {
    val context = LocalContext.current
    val scope = rememberCoroutineScope()
    val geocoder = remember { MapGeocoder() }
    val propertyApi = remember { MapPropertyApi() }
    val snackbar = remember { SnackbarHostState() }
    var searchText by remember { mutableStateOf("") }
    var placeOptions by remember { mutableStateOf<List<GeocodedPlace>>(emptyList()) }
    var selectedPlace by remember { mutableStateOf<GeocodedPlace?>(null) }
    var selectedListing by remember { mutableStateOf<MapListing?>(null) }
    var properties by remember { mutableStateOf<List<MapListing>>(emptyList()) }
    var area by remember { mutableStateOf<MapArea?>(null) }
    var styleOption by remember { mutableStateOf(MapStyleOption.Liberty) }
    var presentation by remember { mutableStateOf(ListingPresentation.Map) }
    var filters by remember { mutableStateOf(MapFilters()) }
    var showFilters by remember { mutableStateOf(false) }
    var loadingSearch by remember { mutableStateOf(false) }
    var loadingProperties by remember { mutableStateOf(false) }
    var mapLoaded by remember { mutableStateOf(false) }
    var mapError by remember { mutableStateOf<String?>(null) }
    var message by remember { mutableStateOf<String?>(null) }
    var fullscreen by remember { mutableStateOf(false) }
    var mapRetry by remember { mutableIntStateOf(0) }
    val hasLocationPermission =
        ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_FINE_LOCATION) == PackageManager.PERMISSION_GRANTED ||
            ContextCompat.checkSelfPermission(context, Manifest.permission.ACCESS_COARSE_LOCATION) == PackageManager.PERMISSION_GRANTED

    fun readDeviceLocation() {
        try {
            LocationServices.getFusedLocationProviderClient(context).lastLocation
                .addOnSuccessListener { location: Location? ->
                    if (location == null) {
                        message = "Your device has not provided a location yet. Search for a Kenyan area instead."
                    } else {
                        selectedPlace = GeocodedPlace(
                            id = "device-location",
                            name = "Your location",
                            label = "Approximate position from this device",
                            latitude = location.latitude,
                            longitude = location.longitude
                        )
                        placeOptions = emptyList()
                        message = null
                    }
                }
                .addOnFailureListener { message = "Location is unavailable right now. Search for an area instead." }
        } catch (_: SecurityException) {
            message = "Allow location access to center the map on your device."
        }
    }

    val locationPermissionLauncher = rememberLauncherForActivityResult(
        ActivityResultContracts.RequestMultiplePermissions()
    ) { permissions ->
        if (permissions[Manifest.permission.ACCESS_FINE_LOCATION] == true ||
            permissions[Manifest.permission.ACCESS_COARSE_LOCATION] == true
        ) readDeviceLocation()
        else message = "Location access was not granted. You can still search for a Kenyan area."
    }

    fun searchLocation() {
        val query = searchText.trim()
        if (query.length < 2) {
            message = "Enter a county, town, or neighbourhood to search."
            return
        }
        scope.launch {
            loadingSearch = true
            placeOptions = emptyList()
            message = null
            try {
                placeOptions = withContext(Dispatchers.IO) { geocoder.searchKenya(query) }
                if (placeOptions.isEmpty()) message = "No matching Kenyan place was found. Try a town or neighbourhood name."
            } catch (failure: Exception) {
                message = failure.message ?: "Area search is unavailable. Check your connection and try again."
            } finally {
                loadingSearch = false
            }
        }
    }

    fun selectPlace(place: GeocodedPlace) {
        selectedPlace = place
        searchText = place.name
        placeOptions = emptyList()
        selectedListing = null
        properties = emptyList()
        area = null
        presentation = ListingPresentation.Map
        mapError = null
    }

    fun searchThisArea() {
        val visibleArea = area ?: return
        scope.launch {
            loadingProperties = true
            message = null
            try {
                properties = withContext(Dispatchers.IO) { propertyApi.search(visibleArea.viewport, filters) }
                presentation = ListingPresentation.Map
                if (properties.isEmpty()) {
                    message = "No published, available homes with sourced coordinates were found in this map area."
                }
            } catch (failure: Exception) {
                message = failure.message ?: "Homes in this area could not be loaded."
            } finally {
                loadingProperties = false
            }
        }
    }

    LaunchedEffect(message) { message?.let { snackbar.showSnackbar(it) } }
    LaunchedEffect(mapLoaded, styleOption) {
        if (!mapLoaded) {
            delay(15_000)
            if (!mapLoaded) mapError = "The map tiles have not loaded. Check your internet connection and retry."
        }
    }
    SideEffect { onFullscreenChange(fullscreen) }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { contentPadding ->
        Column(
            Modifier.fillMaxSize().padding(contentPadding).padding(horizontal = 14.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Explore the map", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                    Text(
                        selectedPlace?.name ?: "OpenStreetMap data · HomeScout homes",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant,
                        maxLines = 1
                    )
                }
                IconButton(onClick = { showFilters = true }) {
                    Icon(Icons.Filled.FilterList, contentDescription = "Map filters")
                }
                IconButton(onClick = { fullscreen = !fullscreen }) {
                    Icon(
                        if (fullscreen) Icons.Filled.FullscreenExit else Icons.Filled.Fullscreen,
                        contentDescription = if (fullscreen) "Exit map fullscreen" else "Enter map fullscreen"
                    )
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                OutlinedTextField(
                    value = searchText,
                    onValueChange = { searchText = it },
                    modifier = Modifier.weight(1f),
                    placeholder = { Text("County, town, or neighbourhood") },
                    leadingIcon = { Icon(Icons.Filled.Search, contentDescription = null) },
                    singleLine = true,
                    shape = RoundedCornerShape(16.dp),
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Text)
                )
                FilledIconButton(
                    onClick = ::searchLocation,
                    enabled = searchText.isNotBlank() && !loadingSearch,
                    modifier = Modifier.size(52.dp).semantics { contentDescription = "Search Kenyan areas" }
                ) {
                    if (loadingSearch) CircularProgressIndicator(Modifier.size(20.dp), strokeWidth = 2.dp)
                    else Icon(Icons.Filled.Search, contentDescription = "Search")
                }
            }
            if (placeOptions.isNotEmpty()) {
                Surface(
                    shape = RoundedCornerShape(16.dp),
                    color = MaterialTheme.colorScheme.surface,
                    border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
                ) {
                    Column {
                        placeOptions.forEachIndexed { index, place ->
                            Row(
                                Modifier.fillMaxWidth().clickable { selectPlace(place) }.padding(12.dp),
                                verticalAlignment = Alignment.CenterVertically,
                                horizontalArrangement = Arrangement.spacedBy(10.dp)
                            ) {
                                Icon(Icons.Filled.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                                Column(Modifier.weight(1f)) {
                                    Text(place.name, style = MaterialTheme.typography.titleSmall, maxLines = 1)
                                    Text(place.label, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2)
                                }
                            }
                            if (index != placeOptions.lastIndex) HorizontalDivider()
                        }
                    }
                }
            }
            Row(
                Modifier.fillMaxWidth(),
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.SpaceBetween
            ) {
                Text(
                    "Search runs only when you tap the button. Place lookup uses OpenStreetMap Nominatim.",
                    Modifier.weight(1f),
                    style = MaterialTheme.typography.labelSmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                TextButton(onClick = {
                    if (hasLocationPermission) readDeviceLocation()
                    else locationPermissionLauncher.launch(
                        arrayOf(Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION)
                    )
                }) {
                    Icon(Icons.Filled.MyLocation, contentDescription = null, modifier = Modifier.size(18.dp))
                    Spacer(Modifier.width(5.dp))
                    Text("My location")
                }
            }

            if (presentation == ListingPresentation.Map) {
                Box(Modifier.fillMaxWidth().weight(1f).clip(RoundedCornerShape(22.dp))) {
                    key(mapRetry) {
                        OpenFreeMapCanvas(
                            properties = properties,
                            selectedPlace = selectedPlace,
                            styleOption = styleOption,
                            onCameraIdle = { area = it },
                            onMapLoaded = { mapLoaded = true; mapError = null },
                            onMapError = { mapError = it },
                            onSelectListing = { selectedListing = it }
                        )
                    }
                    Column(Modifier.align(Alignment.TopStart).padding(10.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        MapStyleChips(styleOption) { styleOption = it; mapLoaded = false }
                        Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surface.copy(alpha = .96f)) {
                            Text(
                                "OpenFreeMap · OpenMapTiles · © OpenStreetMap contributors",
                                Modifier.padding(horizontal = 10.dp, vertical = 6.dp),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                    Column(
                        Modifier.align(Alignment.BottomCenter).fillMaxWidth().padding(12.dp),
                        horizontalAlignment = Alignment.CenterHorizontally,
                        verticalArrangement = Arrangement.spacedBy(8.dp)
                    ) {
                        if (mapError != null) {
                            Surface(shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.errorContainer) {
                                Row(
                                    Modifier.fillMaxWidth().padding(8.dp),
                                    verticalAlignment = Alignment.CenterVertically,
                                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                                ) {
                                    Text(mapError.orEmpty(), Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onErrorContainer)
                                    TextButton(onClick = { mapError = null; mapLoaded = false; mapRetry++ }) { Text("Retry") }
                                }
                            }
                        } else if (!mapLoaded) {
                            Surface(shape = CircleShape, color = MaterialTheme.colorScheme.surface.copy(alpha = .96f)) {
                                Row(Modifier.padding(horizontal = 14.dp, vertical = 9.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    CircularProgressIndicator(Modifier.size(17.dp), strokeWidth = 2.dp)
                                    Text("Loading OpenStreetMap tiles…", style = MaterialTheme.typography.labelMedium)
                                }
                            }
                        }
                        Button(
                            onClick = ::searchThisArea,
                            enabled = area != null && !loadingProperties,
                            modifier = Modifier.heightIn(min = 48.dp)
                        ) {
                            if (loadingProperties) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                            else Icon(Icons.Filled.Search, contentDescription = null, modifier = Modifier.size(18.dp))
                            Spacer(Modifier.width(8.dp))
                            Text(if (loadingProperties) "Searching homes…" else "Search this area")
                        }
                    }
                }
            } else if (loadingProperties) {
                Box(Modifier.weight(1f).fillMaxWidth(), contentAlignment = Alignment.Center) {
                    CircularProgressIndicator()
                }
            } else if (properties.isEmpty()) {
                Column(
                    Modifier.weight(1f).fillMaxWidth().padding(24.dp),
                    verticalArrangement = Arrangement.Center,
                    horizontalAlignment = Alignment.CenterHorizontally
                ) {
                    Icon(Icons.Filled.HomeWork, null, Modifier.size(42.dp), tint = MaterialTheme.colorScheme.primary)
                    Spacer(Modifier.height(10.dp))
                    Text("No homes loaded yet", style = MaterialTheme.typography.titleMedium)
                    Text(
                        "Search the visible map area first. Only published, available listings with publisher-supplied coordinates can appear here.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    TextButton(onClick = onBrowseDiscover) { Text("Browse homes") }
                }
            } else {
                LazyColumn(
                    Modifier.weight(1f).fillMaxWidth(),
                    contentPadding = PaddingValues(vertical = 4.dp, horizontal = 2.dp),
                    verticalArrangement = Arrangement.spacedBy(9.dp)
                ) {
                    item { Text("${properties.size} homes in this map area", style = MaterialTheme.typography.titleMedium) }
                    items(properties, key = { it.id }) { property ->
                        MapListingRow(property) {
                            selectedListing = property
                            presentation = ListingPresentation.Map
                        }
                    }
                }
            }
            MapViewSwitcher(presentation, properties.size) { presentation = it }
        }
    }

    if (showFilters) {
        MapFilterSheet(
            current = filters,
            onDismiss = { showFilters = false },
            onApply = {
                filters = it
                showFilters = false
                if (area != null) searchThisArea()
            }
        )
    }
    selectedListing?.let { property ->
        ListingPreviewSheet(
            property = property,
            onDismiss = { selectedListing = null },
            onOpenDetails = { onOpenProperty(property.id); selectedListing = null }
        )
    }
}

@Composable
private fun OpenFreeMapCanvas(
    properties: List<MapListing>,
    selectedPlace: GeocodedPlace?,
    styleOption: MapStyleOption,
    onCameraIdle: (MapArea) -> Unit,
    onMapLoaded: () -> Unit,
    onMapError: (String) -> Unit,
    onSelectListing: (MapListing) -> Unit
) {
    val context = LocalContext.current
    val lifecycleOwner = LocalLifecycleOwner.current
    val mapView = remember(context) {
        MapLibre.getInstance(context)
        MapView(context).apply { onCreate(null) }
    }
    var map by remember { mutableStateOf<MapLibreMap?>(null) }
    var activeStyle by remember { mutableStateOf<Style?>(null) }
    val latestProperties by rememberUpdatedState(properties)
    val latestOnCameraIdle by rememberUpdatedState(onCameraIdle)
    val latestOnMapLoaded by rememberUpdatedState(onMapLoaded)
    val latestOnSelectListing by rememberUpdatedState(onSelectListing)

    DisposableEffect(mapView, lifecycleOwner) {
        val observer = LifecycleEventObserver { _, event ->
            when (event) {
                Lifecycle.Event.ON_START -> mapView.onStart()
                Lifecycle.Event.ON_RESUME -> mapView.onResume()
                Lifecycle.Event.ON_PAUSE -> mapView.onPause()
                Lifecycle.Event.ON_STOP -> mapView.onStop()
                else -> Unit
            }
        }
        lifecycleOwner.lifecycle.addObserver(observer)
        onDispose {
            lifecycleOwner.lifecycle.removeObserver(observer)
            mapView.onPause()
            mapView.onStop()
            mapView.onDestroy()
        }
    }
    AndroidView(factory = { mapView }, modifier = Modifier.fillMaxSize())

    LaunchedEffect(mapView) {
        mapView.getMapAsync { loadedMap ->
            map = loadedMap
            loadedMap.uiSettings.isCompassEnabled = true
            loadedMap.uiSettings.isAttributionEnabled = true
            loadedMap.cameraPosition = CameraPosition.Builder().target(KENYA_VIEWPORT_CENTER).zoom(5.1).build()
            loadedMap.addOnCameraIdleListener {
                val bounds = loadedMap.projection.visibleRegion.latLngBounds
                val viewport = runCatching {
                    MapViewport(bounds.latitudeSouth, bounds.longitudeWest, bounds.latitudeNorth, bounds.longitudeEast)
                }.getOrNull() ?: return@addOnCameraIdleListener
                val center = loadedMap.cameraPosition.target ?: return@addOnCameraIdleListener
                latestOnCameraIdle(MapArea(viewport, center))
            }
            loadedMap.setOnMarkerClickListener { marker ->
                val property = latestProperties.firstOrNull { it.id == marker.snippet }
                if (property != null) latestOnSelectListing(property)
                property != null
            }
        }
    }

    LaunchedEffect(map, styleOption) {
        val activeMap = map ?: return@LaunchedEffect
        activeStyle = null
        try {
            activeMap.setStyle(styleOption.url) { loadedStyle ->
                activeStyle = loadedStyle
                latestOnMapLoaded()
                val bounds = activeMap.projection.visibleRegion.latLngBounds
                val viewport = runCatching {
                    MapViewport(bounds.latitudeSouth, bounds.longitudeWest, bounds.latitudeNorth, bounds.longitudeEast)
                }.getOrNull()
                val center = activeMap.cameraPosition.target
                if (viewport != null && center != null) latestOnCameraIdle(MapArea(viewport, center))
            }
        } catch (_: Exception) {
            onMapError("The public map style could not be loaded. Check the internet connection and retry.")
        }
    }

    LaunchedEffect(activeStyle, properties, selectedPlace) {
        val activeMap = map ?: return@LaunchedEffect
        if (activeStyle == null) return@LaunchedEffect
        activeMap.clear()
        selectedPlace?.let { place ->
            activeMap.addMarker(
                MarkerOptions().position(LatLng(place.latitude, place.longitude))
                    .title(place.name).snippet(place.label)
            )
        }
        properties.forEach { property ->
            activeMap.addMarker(
                MarkerOptions().position(LatLng(property.latitude, property.longitude))
                    .title("${formatKes(property.rentAmount)} / ${property.rentFrequency}")
                    .snippet(property.id)
            )
        }
    }
    LaunchedEffect(map, selectedPlace) {
        val place = selectedPlace ?: return@LaunchedEffect
        map?.animateCamera(CameraUpdateFactory.newLatLngZoom(LatLng(place.latitude, place.longitude), 14.0), 650)
    }
}

private val KENYA_VIEWPORT_CENTER = LatLng(0.0, 37.0)

@Composable
private fun MapStyleChips(selected: MapStyleOption, onSelect: (MapStyleOption) -> Unit) {
    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(5.dp)) {
        MapStyleOption.entries.forEach { option ->
            FilterChip(
                selected = option == selected,
                onClick = { onSelect(option) },
                label = { Text(option.label) },
                leadingIcon = if (selected == option) ({ Icon(Icons.Filled.Check, null, Modifier.size(15.dp)) }) else null,
                colors = FilterChipDefaults.filterChipColors(
                    containerColor = MaterialTheme.colorScheme.surface.copy(alpha = .96f),
                    selectedContainerColor = MaterialTheme.colorScheme.primaryContainer
                )
            )
        }
    }
}

@Composable
private fun MapViewSwitcher(presentation: ListingPresentation, listingCount: Int, onSelect: (ListingPresentation) -> Unit) {
    Surface(color = MaterialTheme.colorScheme.surface, tonalElevation = 2.dp) {
        Row(
            Modifier.fillMaxWidth().navigationBarsPadding().padding(horizontal = 16.dp, vertical = 6.dp),
            horizontalArrangement = Arrangement.Center
        ) {
            SingleChoiceSegmentedButtonRow(Modifier.widthIn(min = 280.dp).fillMaxWidth()) {
                SegmentedButton(
                    selected = presentation == ListingPresentation.Map,
                    onClick = { onSelect(ListingPresentation.Map) },
                    modifier = Modifier.weight(1f),
                    shape = SegmentedButtonDefaults.itemShape(index = 0, count = 2)
                ) { Text("Map") }
                SegmentedButton(
                    selected = presentation == ListingPresentation.List,
                    onClick = { onSelect(ListingPresentation.List) },
                    modifier = Modifier.weight(1f),
                    shape = SegmentedButtonDefaults.itemShape(index = 1, count = 2)
                ) { Text("List · $listingCount") }
            }
        }
    }
}

@Composable
private fun MapListingRow(property: MapListing, onClick: () -> Unit) {
    Surface(
        Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(17.dp),
        color = MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
            Text(
                "${formatKes(property.rentAmount)} / ${property.rentFrequency}",
                color = MaterialTheme.colorScheme.primary,
                style = MaterialTheme.typography.titleMedium,
                fontWeight = FontWeight.Bold
            )
            Text(property.title, style = MaterialTheme.typography.titleSmall)
            Text(
                "${property.bedrooms} bedrooms · ${property.locationLabel}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun ListingPreviewSheet(property: MapListing, onDismiss: () -> Unit, onOpenDetails: () -> Unit) {
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 28.dp),
            verticalArrangement = Arrangement.spacedBy(10.dp)
        ) {
            Text(property.title, style = MaterialTheme.typography.titleLarge)
            Text(property.locationLabel, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                "${formatKes(property.rentAmount)} / ${property.rentFrequency}",
                style = MaterialTheme.typography.headlineSmall,
                color = MaterialTheme.colorScheme.primary,
                fontWeight = FontWeight.Bold
            )
            HorizontalDivider()
            Text(
                "${property.bedrooms} bedrooms · ${property.bathrooms} bathrooms · ${property.furnishing.replace('_', ' ')}",
                style = MaterialTheme.typography.bodyMedium
            )
            if (property.verified) {
                Text("Verified listing", style = MaterialTheme.typography.labelMedium, color = homeScoutSuccessTextColor())
            }
            Text(
                "Published listing with coordinates supplied by its publisher. Confirm the home’s details and location with the listing contact.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Button(onClick = onOpenDetails, modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp)) {
                Text("View home details")
            }
        }
    }
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun MapFilterSheet(current: MapFilters, onDismiss: () -> Unit, onApply: (MapFilters) -> Unit) {
    var minRent by remember(current) { mutableStateOf(current.minRent) }
    var maxRent by remember(current) { mutableStateOf(current.maxRent) }
    var propertyType by remember(current) { mutableStateOf(current.propertyType) }
    var bedrooms by remember(current) { mutableStateOf(current.bedrooms) }
    var bedroomsAtLeast by remember(current) { mutableStateOf(current.bedroomsAtLeast) }
    var furnishing by remember(current) { mutableStateOf(current.furnishing) }
    var verifiedOnly by remember(current) { mutableStateOf(current.verifiedOnly) }
    var validationError by remember { mutableStateOf<String?>(null) }
    ModalBottomSheet(onDismissRequest = onDismiss) {
        Column(
            Modifier.fillMaxWidth().padding(horizontal = 20.dp).padding(bottom = 30.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Map filters", style = MaterialTheme.typography.titleLarge)
                    Text("Published and available homes only.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = {
                    minRent = ""; maxRent = ""; propertyType = null; bedrooms = null
                    bedroomsAtLeast = false; furnishing = null; verifiedOnly = false
                }) { Text("Clear") }
            }
            Text("Rent amount (KES)", style = MaterialTheme.typography.titleSmall)
            Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                OutlinedTextField(minRent, { minRent = it.filter(Char::isDigit) }, Modifier.weight(1f), label = { Text("Minimum") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
                OutlinedTextField(maxRent, { maxRent = it.filter(Char::isDigit) }, Modifier.weight(1f), label = { Text("Maximum") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), singleLine = true)
            }
            FilterChoiceRow(
                "Property type", listOf("Apartment", "House", "Maisonette", "Villa", "Townhouse"),
                propertyType?.replaceFirstChar(Char::uppercase)
            ) { propertyType = if (propertyType == it.lowercase()) null else it.lowercase() }
            FilterChoiceRow(
                "Bedrooms", listOf("Studio / bedsitter", "1", "2", "3", "4+"),
                bedrooms?.let { when { it == 0 -> "Studio / bedsitter"; it >= 4 -> "4+"; else -> it.toString() } }
            ) {
                bedrooms = when (it) { "Studio / bedsitter" -> 0; "4+" -> 4; else -> it.toIntOrNull() }
                bedroomsAtLeast = it == "4+"
            }
            FilterChoiceRow(
                "Furnishing", listOf("Furnished", "Unfurnished", "Semi furnished"),
                furnishing?.replace('_', ' ')?.replaceFirstChar(Char::uppercase)
            ) { furnishing = if (furnishing == it.lowercase().replace(' ', '_')) null else it.lowercase().replace(' ', '_') }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("Verified only", style = MaterialTheme.typography.titleSmall)
                    Text("Uses the listing’s actual verification record.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Switch(checked = verifiedOnly, onCheckedChange = { verifiedOnly = it })
            }
            validationError?.let { Text(it, color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }
            Button(
                onClick = {
                    runCatching {
                        MapFilters(minRent, maxRent, propertyType, bedrooms, bedroomsAtLeast, furnishing, verifiedOnly).validated()
                    }.onSuccess(onApply).onFailure { validationError = it.message }
                },
                modifier = Modifier.fillMaxWidth().heightIn(min = 50.dp)
            ) { Text("Apply filters") }
        }
    }
}

@Composable
private fun FilterChoiceRow(title: String, options: List<String>, selected: String?, onSelect: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
        Text(title, style = MaterialTheme.typography.titleSmall)
        Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(6.dp)) {
            options.forEach { option ->
                FilterChip(selected = selected.equals(option, ignoreCase = true), onClick = { onSelect(option) }, label = { Text(option) })
            }
        }
    }
}

private enum class MapStyleOption(val label: String, private val styleName: String) {
    Liberty("Standard", "liberty"),
    Bright("Bright", "bright"),
    Positron("Light", "positron"),
    Dark("Dark", "dark");

    val url: String get() = openFreeMapStyleUrl(styleName)
}
