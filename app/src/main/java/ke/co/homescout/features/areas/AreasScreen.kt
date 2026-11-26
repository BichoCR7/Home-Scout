package ke.co.homescout.features.areas

import android.util.Base64
import androidx.compose.foundation.BorderStroke
import androidx.compose.foundation.clickable
import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.LazyRow
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Search
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.MarketplaceApi
import ke.co.homescout.data.remote.MarketplaceCounty
import ke.co.homescout.data.remote.MarketplaceLocation
import ke.co.homescout.data.remote.MarketplaceNeighbourhood
import ke.co.homescout.data.remote.MarketplaceTown
import ke.co.homescout.features.home.popularAreas
import ke.co.homescout.ui.components.HomeScoutBadge
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.components.HomeScoutPrimaryButton
import ke.co.homescout.ui.components.HomeScoutSearchField
import ke.co.homescout.ui.theme.HomeScoutColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject

private data class CountyOption(val id: String?, val code: String, val name: String)
private data class TownOption(val id: String?, val countyId: String?, val name: String, val localAreas: List<String> = emptyList())
private data class NeighbourhoodOption(val id: String?, val townId: String?, val name: String)
private data class LocationChoice(
    val name: String,
    val countyName: String,
    val townName: String? = null,
    val neighbourhoodName: String? = null,
    val countyId: String? = null,
    val townId: String? = null,
    val neighbourhoodId: String? = null
) {
    val path: String
        get() = listOfNotNull(neighbourhoodName, townName, countyName).distinct().joinToString(" · ")
}

@Composable
fun AreasScreen(onNavigate: (String) -> Unit) {
    val scope = rememberCoroutineScope()
    val apiConfigured = ApiConfiguration.isConfigured
    val api = remember { if (apiConfigured) runCatching { MarketplaceApi() }.getOrNull() else null }
    var counties by remember { mutableStateOf(AreaDirectory.counties.map { CountyOption(null, it.code, it.name) }) }
    var selectedCounty by remember { mutableStateOf<CountyOption?>(null) }
    var towns by remember { mutableStateOf<List<TownOption>>(emptyList()) }
    var selectedTown by remember { mutableStateOf<TownOption?>(null) }
    var neighbourhoods by remember { mutableStateOf<List<NeighbourhoodOption>>(emptyList()) }
    var searchText by remember { mutableStateOf("") }
    var searchResults by remember { mutableStateOf<List<LocationChoice>>(emptyList()) }
    var loadingCounties by remember { mutableStateOf(apiConfigured) }
    var loadingTowns by remember { mutableStateOf(false) }
    var loadingNeighbourhoods by remember { mutableStateOf(false) }
    var searching by remember { mutableStateOf(false) }
    var apiDirectoryAvailable by remember { mutableStateOf(false) }
    var notice by remember { mutableStateOf<String?>(null) }
    var searchError by remember { mutableStateOf<String?>(null) }

    fun browse(choice: LocationChoice) {
        val filters = JSONObject().put("query", choice.name)
        choice.countyId?.takeIf(String::isNotBlank)?.let { filters.put("county_id", it) }
        choice.townId?.takeIf(String::isNotBlank)?.let { filters.put("town_id", it) }
        choice.neighbourhoodId?.takeIf(String::isNotBlank)?.let { filters.put("neighbourhood_id", it) }
        val encoded = Base64.encodeToString(
            filters.toString().toByteArray(Charsets.UTF_8),
            Base64.URL_SAFE or Base64.NO_WRAP or Base64.NO_PADDING
        )
        onNavigate("discover?savedFilters=$encoded")
    }

    fun fallbackCounty(code: String): AreaDirectory.County? = AreaDirectory.counties.firstOrNull { it.code == code }

    fun localTowns(county: CountyOption): List<TownOption> = fallbackCounty(county.code)?.let { source ->
        AreaDirectory.towns(source).map { TownOption(null, county.id, it.name, it.neighbourhoods) }
    }.orEmpty()

    fun chooseCounty(county: CountyOption) {
        selectedCounty = county
        selectedTown = null
        neighbourhoods = emptyList()
        towns = localTowns(county)
        loadingTowns = api != null && !county.id.isNullOrBlank()
        notice = if (apiDirectoryAvailable) null else "Showing the built-in Kenyan area directory."
        if (api != null && !county.id.isNullOrBlank()) scope.launch {
            val response = runCatching { withContext(Dispatchers.IO) { api.towns(county.id) } }.getOrNull()
            if (response != null && response.isNotEmpty()) {
                towns = response.map { TownOption(it.id, it.countyId, it.name, localTowns(county).firstOrNull { local -> local.name.equals(it.name, true) }?.localAreas.orEmpty()) }
            } else if (response == null) {
                notice = "The location service is unavailable. Showing local reference places."
            }
            loadingTowns = false
        }
    }

    fun chooseTown(town: TownOption) {
        selectedTown = town
        neighbourhoods = town.localAreas.map { NeighbourhoodOption(null, town.id, it) }
        loadingNeighbourhoods = api != null && !town.id.isNullOrBlank()
        if (api != null && !town.id.isNullOrBlank()) scope.launch {
            val response = runCatching { withContext(Dispatchers.IO) { api.neighbourhoods(town.id) } }.getOrNull()
            if (response != null && response.isNotEmpty()) {
                neighbourhoods = response.map { NeighbourhoodOption(it.id, it.townId, it.name) }
            } else if (response == null) {
                notice = "The location service is unavailable. Showing available local reference areas."
            }
            loadingNeighbourhoods = false
        }
    }

    fun countyChoice(county: CountyOption) = LocationChoice(
        name = county.name,
        countyName = county.name,
        countyId = county.id
    )

    fun townChoice(county: CountyOption, town: TownOption) = LocationChoice(
        name = town.name,
        countyName = county.name,
        townName = town.name,
        countyId = town.countyId ?: county.id,
        townId = town.id
    )

    fun neighbourhoodChoice(county: CountyOption, town: TownOption, area: NeighbourhoodOption) = LocationChoice(
        name = area.name,
        countyName = county.name,
        townName = town.name,
        neighbourhoodName = area.name,
        countyId = town.countyId ?: county.id,
        townId = area.townId ?: town.id,
        neighbourhoodId = area.id
    )

    fun searchLocations() {
        val query = searchText.trim()
        searchError = null
        if (query.length < 2) {
            searchError = "Enter at least two letters to search."
            searchResults = emptyList()
            return
        }
        searching = true
        scope.launch {
            val remote = if (api != null) runCatching {
                withContext(Dispatchers.IO) { api.searchLocations(query) }
            }.getOrNull() else null
            searchResults = if (!remote.isNullOrEmpty()) remote.map { it.toChoice() }
            else AreaDirectory.search(query).map { path ->
                LocationChoice(path.name, path.county.name, path.town, path.neighbourhood)
            }
            if (remote == null && api != null) notice = "Could not reach the location service. Search is using local reference places."
            if (searchResults.isEmpty()) searchError = "No matching county, town, or neighbourhood was found."
            searching = false
        }
    }

    fun openPopularArea(name: String) {
        searchText = name
        scope.launch {
            val remote = if (api != null) runCatching {
                withContext(Dispatchers.IO) { api.searchLocations(name) }
            }.getOrNull() else null
            val match = remote?.firstOrNull { it.name.equals(name, true) }?.toChoice()
                ?: AreaDirectory.search(name).firstOrNull { it.name.equals(name, true) }?.let {
                    LocationChoice(it.name, it.county.name, it.town, it.neighbourhood)
                }
            if (match != null) browse(match) else {
                searchLocations()
            }
        }
    }

    LaunchedEffect(api) {
        if (api == null) {
            loadingCounties = false
            notice = "Offline reference directory · connect to HomeScout to load live property results."
            return@LaunchedEffect
        }
        val remote = runCatching { withContext(Dispatchers.IO) { api.counties() } }.getOrNull()
        if (!remote.isNullOrEmpty()) {
            counties = remote.map { CountyOption(it.id, it.code, it.name) }
            apiDirectoryAvailable = true
        } else {
            notice = "The location service is unavailable. Showing the built-in Kenyan area directory."
        }
        loadingCounties = false
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize().padding(horizontal = 18.dp),
        contentPadding = PaddingValues(top = 20.dp, bottom = 28.dp),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                Text("Explore Areas", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                Text(
                    "Choose a Kenyan county, town, or neighbourhood to find matching homes.",
                    style = MaterialTheme.typography.bodyMedium,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        if (notice != null) {
            item {
                HomeScoutBadge(
                    notice.orEmpty(),
                    color = HomeScoutColors.navy,
                    background = HomeScoutColors.paleBlue
                )
            }
        }

        item {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                HomeScoutSearchField(
                    value = searchText,
                    onValueChange = { searchText = it },
                    placeholder = "Search a county, town, or area",
                    modifier = Modifier.weight(1f),
                    leading = { Icon(Icons.Filled.Search, contentDescription = null) }
                )
                Button(onClick = ::searchLocations, enabled = !searching, modifier = Modifier.heightIn(min = 52.dp)) {
                    if (searching) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    else Text("Search")
                }
            }
        }

        if (searchError != null) item { Text(searchError.orEmpty(), color = MaterialTheme.colorScheme.error, style = MaterialTheme.typography.bodySmall) }

        item {
            Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Text("Popular around you", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                LazyRow(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    items(popularAreas.take(12), key = { it }) { area ->
                        SuggestionChip(onClick = { openPopularArea(area) }, label = { Text(area) }, icon = {
                            Icon(Icons.Filled.LocationOn, contentDescription = null, modifier = Modifier.size(16.dp))
                        })
                    }
                }
            }
        }

        if (searchResults.isNotEmpty()) {
            item { Text("Matching places", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
            items(searchResults, key = { "${it.countyName}:${it.townName}:${it.neighbourhoodName}:${it.name}" }) { result ->
                LocationResultCard(result, onClick = { browse(result) })
            }
        }

        val activeCounty = selectedCounty
        val activeTown = selectedTown
        if (activeCounty == null) {
            item {
                Text(
                    if (loadingCounties) "Loading counties…" else "Browse all ${counties.size} counties",
                    style = MaterialTheme.typography.titleMedium,
                    fontWeight = FontWeight.SemiBold
                )
            }
            items(counties, key = CountyOption::code) { county ->
                CountyCard(county, onClick = { chooseCounty(county) })
            }
        } else {
            item {
                TextButton(onClick = {
                    selectedCounty = null
                    selectedTown = null
                    towns = emptyList()
                    neighbourhoods = emptyList()
                }, contentPadding = PaddingValues(horizontal = 0.dp)) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = null)
                    Spacer(Modifier.width(6.dp))
                    Text("All counties")
                }
            }
            item {
                Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text(activeCounty.name, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text("County · Kenya", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    HomeScoutPrimaryButton(
                        "Browse homes in ${activeCounty.name}",
                        Modifier.fillMaxWidth(),
                        onClick = { browse(countyChoice(activeCounty)) }
                    )
                }
            }
            item { Text("Towns and cities", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
            if (loadingTowns) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            if (!loadingTowns && towns.isEmpty()) {
                item { Text("No town records are listed yet. You can still browse this county.", color = MaterialTheme.colorScheme.onSurfaceVariant) }
            }
            items(towns, key = { "${it.id ?: "local"}:${it.name}" }) { town ->
                TownCard(town, selected = activeTown?.name == town.name, onClick = { chooseTown(town) })
            }
            if (activeTown != null) {
                item {
                    Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(activeTown.name, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                        Text("${activeTown.name} · ${activeCounty.name}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        HomeScoutPrimaryButton(
                            "Browse homes in ${activeTown.name}",
                            Modifier.fillMaxWidth(),
                            onClick = { browse(townChoice(activeCounty, activeTown)) }
                        )
                    }
                }
                item { Text("Neighbourhoods and areas", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold) }
                if (loadingNeighbourhoods) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                if (!loadingNeighbourhoods && neighbourhoods.isEmpty()) {
                    item {
                        HomeScoutCard(Modifier.fillMaxWidth()) {
                            Text(
                                "No neighbourhoods are listed for this town yet. Browse town-wide homes above.",
                                Modifier.padding(16.dp),
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
                items(neighbourhoods, key = { "${it.id ?: "local"}:${it.name}" }) { area ->
                    LocationResultCard(
                        LocationChoice(area.name, activeCounty.name, activeTown.name, area.name, activeCounty.id, activeTown.id, area.id),
                        onClick = { browse(neighbourhoodChoice(activeCounty, activeTown, area)) }
                    )
                }
            }
        }

        item {
            Text(
                "Area names are reference data. The map does not infer town or neighbourhood coordinates.",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
    }
}

@Composable
private fun CountyCard(county: CountyOption, onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(Modifier.fillMaxWidth().padding(horizontal = 16.dp, vertical = 14.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Filled.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(12.dp))
            Column(Modifier.weight(1f)) {
                Text(county.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text("County ${county.code}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Open ${county.name}", tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun TownCard(town: TownOption, selected: Boolean, onClick: () -> Unit) {
    Surface(
        modifier = Modifier.fillMaxWidth().clickable(onClick = onClick),
        shape = RoundedCornerShape(14.dp),
        color = if (selected) MaterialTheme.colorScheme.secondaryContainer else MaterialTheme.colorScheme.surface,
        border = BorderStroke(1.dp, MaterialTheme.colorScheme.outlineVariant)
    ) {
        Row(Modifier.padding(horizontal = 15.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Filled.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(town.name, fontWeight = FontWeight.Medium)
                Text("Town or city", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Open ${town.name}", tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

@Composable
private fun LocationResultCard(choice: LocationChoice, onClick: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth().clickable(onClick = onClick)) {
        Row(Modifier.padding(horizontal = 15.dp, vertical = 13.dp), verticalAlignment = Alignment.CenterVertically) {
            Icon(Icons.Filled.LocationOn, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            Spacer(Modifier.width(10.dp))
            Column(Modifier.weight(1f)) {
                Text(choice.name, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(choice.path, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 2, overflow = TextOverflow.Ellipsis)
            }
            Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = "Browse ${choice.name}", tint = MaterialTheme.colorScheme.onSurfaceVariant)
        }
    }
}

private fun MarketplaceLocation.toChoice(): LocationChoice = LocationChoice(
    name = name,
    countyName = countyName,
    townName = townName,
    neighbourhoodName = if (kind == "neighbourhood") name else null,
    countyId = countyId,
    townId = townId,
    neighbourhoodId = neighbourhoodId
)
