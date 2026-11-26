package ke.co.homescout.features.home

import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.CircleShape
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Bed
import androidx.compose.material.icons.filled.Campaign
import androidx.compose.material.icons.filled.ChatBubbleOutline
import androidx.compose.material.icons.filled.CheckCircle
import androidx.compose.material.icons.filled.ChevronRight
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Explore
import androidx.compose.material.icons.filled.FavoriteBorder
import androidx.compose.material.icons.filled.HomeWork
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Search
import androidx.compose.material.icons.filled.Security
import androidx.compose.material.icons.filled.SquareFoot
import androidx.compose.material.icons.automirrored.filled.TrendingUp
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.alpha
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import android.net.Uri
import androidx.compose.ui.text.style.TextOverflow
import ke.co.homescout.BuildConfig
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.MarketplaceApi
import ke.co.homescout.data.remote.MarketplaceFilters
import ke.co.homescout.data.remote.MarketplaceProperty
import ke.co.homescout.features.discover.MarketplacePropertyCard
import ke.co.homescout.navigation.Destination
import ke.co.homescout.ui.components.*
import ke.co.homescout.ui.theme.HomeScoutColors
import ke.co.homescout.ui.theme.HomeScoutSpacing
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext

@Composable
fun HomeScreen(onNavigate: (String) -> Unit, accessToken: String? = null) {
    var query by remember { mutableStateOf("") }
    var location by remember { mutableStateOf("") }
    var selectedFaq by remember { mutableIntStateOf(-1) }
    var searchMessage by remember { mutableStateOf<String?>(null) }
    var homes by remember { mutableStateOf<List<MarketplaceProperty>>(emptyList()) }
    var savedHomes by remember { mutableStateOf<List<MarketplaceProperty>>(emptyList()) }
    var loadingHomes by remember { mutableStateOf(false) }
    var homesError by remember { mutableStateOf<String?>(null) }
    val configured = ApiConfiguration.isConfigured
    val scope = rememberCoroutineScope()
    val snackbar = remember { SnackbarHostState() }
    LaunchedEffect(searchMessage) {
        searchMessage?.let { snackbar.showSnackbar(it); searchMessage = null }
    }
    fun loadHomes() {
        if (!configured) return
        scope.launch {
            loadingHomes = true
            homesError = null
            try {
                val result = withContext(Dispatchers.IO) {
                    val api = MarketplaceApi()
                    val featured = api.search(MarketplaceFilters(includeDemo = BuildConfig.DEBUG))
                    val saved = accessToken?.let { api.savedProperties(it) }.orEmpty()
                    featured to saved
                }
                homes = result.first
                savedHomes = result.second
            } catch (failure: Exception) {
                homesError = failure.message ?: "Homes could not be loaded."
            } finally {
                loadingHomes = false
            }
        }
    }
    LaunchedEffect(configured, accessToken) { loadHomes() }

    Scaffold(snackbarHost = { HomeScoutSnackbarHost(snackbar) }) { insets ->
        BoxWithConstraints(Modifier.fillMaxSize().padding(insets)) {
        val columnModifier = if (maxWidth > 720.dp) Modifier.widthIn(max = 720.dp).fillMaxHeight().align(Alignment.TopCenter) else Modifier.fillMaxSize()
        LazyColumn(
            modifier = columnModifier,
            contentPadding = PaddingValues(start = 20.dp, end = 20.dp, top = 10.dp, bottom = 32.dp),
            verticalArrangement = Arrangement.spacedBy(28.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                        Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                            Text("KARIBU, WELCOME HOME", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.primary, letterSpacing = 1.2.sp)
                            Text("Find a place that feels like yours.", style = MaterialTheme.typography.headlineMedium, color = MaterialTheme.colorScheme.onBackground)
                            Text("Thoughtful homes, clearer choices, right here in Kenya.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                    HomeScoutCard(Modifier.fillMaxWidth()) {
                        Row(Modifier.fillMaxWidth().clickable { onNavigate("collaboration?tab=Messages") }.padding(14.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(11.dp)) {
                            Icon(Icons.Filled.ChatBubbleOutline, contentDescription = null, tint = HomeScoutColors.blue)
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                Text("Your home conversations", style = MaterialTheme.typography.titleSmall)
                                Text("Message listing contacts and keep replies in one place.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Open messages", tint = MaterialTheme.colorScheme.primary)
                        }
                    }
                }
            }
            item { HeroBanner(onExplore = { onNavigate(Destination.Discover.route) }) }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    Text("Find your next home", style = MaterialTheme.typography.titleLarge)
                    HomeScoutSearchField(query, { query = it }, "Area, estate or property", Modifier.fillMaxWidth(), leading = { Icon(Icons.Filled.Search, null) })
                    HomeScoutSearchField(location, { location = it }, "Add a location", Modifier.fillMaxWidth(), leading = { Icon(Icons.Filled.LocationOn, null) })
                    HomeScoutPrimaryButton("Search homes", Modifier.fillMaxWidth()) {
                        if (query.isBlank() && location.isBlank()) searchMessage = "Add an area or property type to start your search."
                        else onNavigate("${Destination.Discover.route}?query=${Uri.encode(query.ifBlank { location })}")
                    }
                }
            }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Popular around you", "Explore") { onNavigate(Destination.Neighbourhoods.route) }
                    Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                        popularAreas.forEachIndexed { index, area ->
                            PopularAreaCard(area, index, onClick = {
                                location = area
                                query = area
                                onNavigate("${Destination.Discover.route}?query=${Uri.encode(area)}")
                            })
                        }
                    }
                }
            }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                    SectionHeading("Featured homes", "See all") { onNavigate(Destination.Discover.route) }
                    Text(
                        if (BuildConfig.DEBUG) "Clearly marked synthetic examples for development." else "Homes shown here come from the HomeScout listing service.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
            }
            when {
                !configured -> item { EmptyState("Connect HomeScout to browse homes", "Add the development API address to load listings, details and saved homes.") }
                loadingHomes -> item {
                    Row(Modifier.fillMaxWidth().padding(vertical = 18.dp), horizontalArrangement = Arrangement.Center, verticalAlignment = Alignment.CenterVertically) {
                        CircularProgressIndicator(Modifier.size(22.dp), strokeWidth = 2.dp)
                        Spacer(Modifier.width(10.dp)); Text("Loading homes…", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                homesError != null -> item {
                    ErrorState("Homes could not be loaded", homesError.orEmpty(), onRetry = ::loadHomes)
                }
                homes.isEmpty() -> item { EmptyState("No homes to show yet", "Published listings and development examples appear here when available.") }
                else -> items(homes.take(6), key = MarketplaceProperty::id) { property ->
                    MarketplacePropertyCard(
                        property = property,
                        saved = savedHomes.any { it.id == property.id },
                        compared = false,
                        canSave = accessToken != null,
                        onClick = { onNavigate("property/${property.id}") },
                        onSave = {
                            val token = accessToken
                            if (token == null) onNavigate(Destination.Profile.route)
                            else scope.launch {
                                try {
                                    val newSaved = savedHomes.none { it.id == property.id }
                                    withContext(Dispatchers.IO) { MarketplaceApi().save(property.id, token, newSaved) }
                                    savedHomes = if (newSaved) savedHomes + property else savedHomes.filterNot { it.id == property.id }
                                    searchMessage = if (newSaved) "Home saved to your favourites." else "Home removed from your favourites."
                                } catch (failure: Exception) { searchMessage = failure.message ?: "Home could not be saved." }
                            }
                        },
                        onCompare = { onNavigate("collaboration?propertyId=${Uri.encode(property.id)}&tab=Compare") }
                    )
                }
            }
            if (accessToken != null && savedHomes.isNotEmpty()) {
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
                        SectionHeading("Saved by you", "View all") { onNavigate("hub/saved") }
                        Text("Your saved homes stay attached to your account.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
                items(savedHomes.take(3), key = { "saved-${it.id}" }) { property ->
                    MarketplacePropertyCard(
                        property = property, saved = true, compared = false, canSave = true,
                        onClick = { onNavigate("property/${property.id}") },
                        onSave = {
                            scope.launch {
                                try {
                                    withContext(Dispatchers.IO) { MarketplaceApi().save(property.id, checkNotNull(accessToken), false) }
                                    savedHomes = savedHomes.filterNot { it.id == property.id }
                                    searchMessage = "Home removed from your favourites."
                                } catch (failure: Exception) { searchMessage = failure.message ?: "Home could not be removed." }
                            }
                        },
                        onCompare = { onNavigate("collaboration?propertyId=${Uri.encode(property.id)}&tab=Compare") }
                    )
                }
            }
            if (configured && homes.size > 6) {
                item {
                    SectionHeading("More homes to explore", "Browse all") { onNavigate(Destination.Discover.route) }
                }
                items(homes.drop(6).take(4), key = { "more-${it.id}" }) { property ->
                    MarketplacePropertyCard(
                        property = property,
                        saved = savedHomes.any { it.id == property.id },
                        compared = false,
                        canSave = accessToken != null,
                        onClick = { onNavigate("property/${property.id}") },
                        onSave = {
                            val token = accessToken
                            if (token == null) onNavigate(Destination.Profile.route)
                            else scope.launch {
                                try {
                                    val newSaved = savedHomes.none { it.id == property.id }
                                    withContext(Dispatchers.IO) { MarketplaceApi().save(property.id, token, newSaved) }
                                    savedHomes = if (newSaved) savedHomes + property else savedHomes.filterNot { it.id == property.id }
                                    searchMessage = if (newSaved) "Home saved to your favourites." else "Home removed from your favourites."
                                } catch (failure: Exception) { searchMessage = failure.message ?: "Home could not be saved." }
                            }
                        },
                        onCompare = { onNavigate("collaboration?propertyId=${Uri.encode(property.id)}&tab=Compare") }
                    )
                }
            }
            item { FeatureRow(Icons.Filled.Payments, "Make renting work for you", "Get a feel for SmartRent and practical money tips.", HomeScoutColors.paleGreen, onClick = { onNavigate(Destination.Finance.route) }, action = "Explore finance") }
            item { FeatureRow(Icons.Filled.Security, "Feel more confident at every step", "Learn what to look for and how to stay alert while renting.", HomeScoutColors.paleBlue, onClick = { onNavigate("trust-safety") }, action = "Safety guide") }
            item { AssistantCard(onClick = { onNavigate(Destination.Assistant.route) }) }
            item { NeighbourhoodPanel(onClick = { onNavigate(Destination.Neighbourhoods.route) }) }
            item { FeatureRow(Icons.Filled.DirectionsCar, "Moving day, made simpler", "Find the right moving support when you are ready.", HomeScoutColors.paleAmber, onClick = { onNavigate(Destination.Services.route) }, action = "Moving services") }
            item { LearningCard(onClick = { onNavigate(Destination.Finance.route) }) }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                    SectionHeading("A few things you might wonder")
                    listOf(
                        "Are these demo listings real homes?" to "No. Development examples are synthetic, clearly labelled, and are not real or available homes.",
                        "Can I message a listing contact?" to "Open a home and send an enquiry to start a private conversation with its authorized listing contact.",
                        "Does HomeScout collect rent?" to "No. HomeScout does not collect rent or hold tenant rent payments."
                    ).forEachIndexed { index, item ->
                        HomeScoutCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(16.dp)) {
                                TextButton(onClick = { selectedFaq = if (selectedFaq == index) -1 else index }, contentPadding = PaddingValues(0.dp)) {
                                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                        Text(item.first, color = MaterialTheme.colorScheme.onSurface, style = MaterialTheme.typography.titleMedium)
                                        Icon(Icons.Filled.ChevronRight, null)
                                    }
                                }
                                if (selectedFaq == index) Text(item.second, color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodyMedium)
                            }
                        }
                    }
                }
            }
            item { Footer(onNavigate = onNavigate) }
        }
        }
    }
}

@Composable
private fun PopularAreaCard(area: String, index: Int, onClick: () -> Unit) {
    val photos = listOf(
        "photo-1600607687939-ce8a6c25118c", "photo-1600566753086-00f18fb6b3ea",
        "photo-1600585154340-be6161a56a0c", "photo-1639663742190-1b3dba2eebcf",
        "photo-1701092868263-2ed67ac8dfa0", "photo-1609766857326-18a204c2cf31",
        "photo-1630699144865-d3230bf37016", "photo-1704428381339-3b3087053b3a",
        "photo-1484154218962-a197022b5858", "photo-1646615811071-f4f0735e2355",
        "photo-1630699144886-d6d025f5d0f1", "photo-1646592491770-c113dd6f8827",
        "photo-1721824318446-8ad0857decdd", "photo-1577579242425-b323e6d61bd4",
        "photo-1737737149038-e6532662659e", "photo-1615749250437-8f3fd29f9118",
        "photo-1721396185451-ff45e7440c30", "photo-1612419299101-6c294dc2901d"
    )
    val imageUrl = "https://images.unsplash.com/${photos[index % photos.size]}?auto=format&fit=crop&w=720&q=80"
    HomeScoutCard(Modifier.width(202.dp)) {
        Column(Modifier.clickable(onClick = onClick)) {
            Box(Modifier.fillMaxWidth().height(118.dp).background(HomeScoutColors.paleBlue)) {
                RemotePhoto(imageUrl, "Illustrative stock image for $area", Modifier.fillMaxSize()) {
                    Icon(Icons.Filled.LocationOn, null, Modifier.align(Alignment.Center).size(32.dp), tint = HomeScoutColors.navy)
                }
                Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(Color.Transparent, Color.Black.copy(alpha = .42f)))))
                Text("KENYA", Modifier.align(Alignment.BottomStart).padding(10.dp), style = MaterialTheme.typography.labelSmall, color = Color.White)
            }
            Row(Modifier.fillMaxWidth().padding(horizontal = 12.dp, vertical = 11.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text(area, style = MaterialTheme.typography.titleSmall, maxLines = 1, overflow = TextOverflow.Ellipsis)
                    Text("Explore homes", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Explore $area", tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(18.dp))
            }
        }
    }
}

@Composable
private fun HeroBanner(onExplore: () -> Unit) {
    Box(Modifier.fillMaxWidth().height(226.dp).clip(RoundedCornerShape(24.dp)).background(HomeScoutColors.navy)) {
        RemotePhoto(
            url = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1400&q=82",
            contentDescription = "Contemporary home exterior, illustrative stock photography",
            modifier = Modifier.fillMaxSize().alpha(.43f),
            fallback = { Box(Modifier.fillMaxSize().background(Brush.linearGradient(listOf(HomeScoutColors.navy, Color(0xFF183D5B))))) }
        )
        Box(Modifier.fillMaxSize().background(Brush.horizontalGradient(listOf(HomeScoutColors.navy.copy(alpha = .96f), HomeScoutColors.navy.copy(alpha = .55f), Color.Transparent))))
        Box(Modifier.size(188.dp).align(Alignment.CenterEnd).offset(x = 24.dp).clip(CircleShape).background(Color.White.copy(alpha = .05f)))
        Box(Modifier.size(136.dp).align(Alignment.CenterEnd).offset(x = (-28).dp, y = 32.dp).clip(CircleShape).background(Color.White.copy(alpha = .05f)))
        Column(Modifier.align(Alignment.CenterStart).padding(horizontal = 22.dp).fillMaxWidth(.72f), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            HomeScoutBadge("MADE FOR THE WAY YOU LIVE", color = HomeScoutColors.white, background = Color.White.copy(alpha = .14f))
            Text("A better way to find home.", color = HomeScoutColors.white, style = MaterialTheme.typography.headlineMedium)
            Text("Explore places across Nairobi and beyond.", color = Color.White.copy(alpha = .78f), style = MaterialTheme.typography.bodyMedium)
            FilledTonalButton(onClick = onExplore, colors = ButtonDefaults.filledTonalButtonColors(containerColor = Color.White, contentColor = HomeScoutColors.navy)) {
                Text("Explore homes"); Spacer(Modifier.width(8.dp)); Icon(Icons.AutoMirrored.Filled.ArrowForward, null, Modifier.size(17.dp))
            }
        }
        Icon(Icons.Filled.HomeWork, null, Modifier.align(Alignment.CenterEnd).padding(end = 18.dp).size(50.dp), tint = Color.White.copy(alpha = .88f))
    }
}

@Composable
private fun FeatureRow(icon: androidx.compose.ui.graphics.vector.ImageVector, title: String, text: String, tint: Color, action: String, onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
            Box(Modifier.size(44.dp).clip(RoundedCornerShape(14.dp)).background(tint), contentAlignment = Alignment.Center) {
                Icon(icon, null, tint = when (tint) { HomeScoutColors.paleGreen -> HomeScoutColors.green; HomeScoutColors.paleAmber -> Color(0xFF9A6200); else -> HomeScoutColors.blue })
            }
            Text(title, style = MaterialTheme.typography.titleLarge)
            Text(text, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            TextButton(onClick = onClick, contentPadding = PaddingValues(horizontal = 0.dp)) { Text(action); Spacer(Modifier.width(4.dp)); Icon(Icons.AutoMirrored.Filled.ArrowForward, null, Modifier.size(16.dp)) }
        }
    }
}

@Composable
private fun AssistantCard(onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().background(Brush.linearGradient(listOf(HomeScoutColors.paleBlue, MaterialTheme.colorScheme.surface))).padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Icon(Icons.Filled.AutoAwesome, null, tint = HomeScoutColors.blue, modifier = Modifier.size(28.dp))
            Text("A little help finding your way?", style = MaterialTheme.typography.titleLarge)
            Text("Get help with home searches, rental costs, viewings and moving. Replies require an active provider and your consent.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            HomeScoutOutlinedButton("Open HomeScout Assistant", onClick = onClick)
        }
    }
}

@Composable
private fun NeighbourhoodPanel(onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                Icon(Icons.Filled.Map, null, tint = HomeScoutColors.blue)
                Text("Get to know the neighbourhood", style = MaterialTheme.typography.titleMedium)
            }
            Text("Compare the feel of different areas, from the city buzz to a quieter pace.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Row(Modifier.horizontalScroll(rememberScrollState()), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("Westlands", "Kilimani", "Ruaka").forEach { SuggestionChip(onClick = onClick, label = { Text(it) }) }
            }
            TextButton(onClick = onClick, contentPadding = PaddingValues(0.dp)) { Text("Explore neighbourhoods") }
        }
    }
}

@Composable
private fun LearningCard(onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(18.dp), horizontalArrangement = Arrangement.spacedBy(14.dp), verticalAlignment = Alignment.Top) {
            Icon(Icons.AutoMirrored.Filled.TrendingUp, null, Modifier.size(28.dp), tint = HomeScoutColors.green)
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                Text("Small steps. Smarter renting.", style = MaterialTheme.typography.titleMedium)
                Text("Explore friendly guides to budgeting for a move and understanding rental costs.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                TextButton(onClick = onClick, contentPadding = PaddingValues(0.dp)) { Text("Financial learning preview") }
            }
        }
    }
}

@Composable
private fun Footer(onNavigate: (String) -> Unit) {
    Column(Modifier.fillMaxWidth().padding(top = 8.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        HorizontalDivider(color = MaterialTheme.colorScheme.outline)
        Text("HomeScout", style = MaterialTheme.typography.titleLarge, color = MaterialTheme.colorScheme.primary)
        Text("A more considered way to find home in Kenya.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            TextButton(onClick = { onNavigate(Destination.Services.route) }) { Text("Services") }
            TextButton(onClick = { onNavigate(Destination.Profile.route) }) { Text("Profile preview") }
        }
        Text("Design preview · Sample property information", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}
