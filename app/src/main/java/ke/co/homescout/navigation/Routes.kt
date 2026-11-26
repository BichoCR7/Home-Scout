package ke.co.homescout.navigation

import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountCircle
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.Build
import androidx.compose.material.icons.filled.DirectionsCar
import androidx.compose.material.icons.filled.Explore
import androidx.compose.material.icons.filled.Home
import androidx.compose.material.icons.filled.LocationOn
import androidx.compose.material.icons.filled.Map
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Search
import androidx.compose.ui.graphics.vector.ImageVector

sealed class Destination(val route: String, val label: String, val icon: ImageVector, val primary: Boolean) {
    data object Home : Destination("home", "Home", Icons.Filled.Home, true)
    data object Discover : Destination("discover", "Discover", Icons.Filled.Search, true)
    data object Map : Destination("map", "Map", Icons.Filled.Map, false)
    data object Finance : Destination("finance", "Finance", Icons.Filled.Payments, true)
    data object Neighbourhoods : Destination("neighbourhoods", "Areas", Icons.Filled.LocationOn, true)
    data object Services : Destination("services", "Services", Icons.Filled.DirectionsCar, false)
    data object Assistant : Destination("assistant", "AI Assistant", Icons.Filled.AutoAwesome, false)
    data object Profile : Destination("profile", "Profile", Icons.Filled.AccountCircle, true)

    companion object {
        val primaryItems = listOf(Home, Discover, Neighbourhoods, Finance, Profile)
        val all = listOf(Home, Discover, Map, Finance, Neighbourhoods, Services, Assistant, Profile)
    }
}
