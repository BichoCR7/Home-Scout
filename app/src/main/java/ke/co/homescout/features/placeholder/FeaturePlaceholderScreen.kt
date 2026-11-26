package ke.co.homescout.features.placeholder

import androidx.compose.foundation.layout.*
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Construction
import androidx.compose.material3.*
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import ke.co.homescout.navigation.Destination
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.theme.HomeScoutColors

@Composable
fun FeaturePlaceholderScreen(destination: Destination, onBack: () -> Unit) {
    Box(Modifier.fillMaxSize().padding(24.dp), contentAlignment = Alignment.Center) {
        HomeScoutCard(Modifier.fillMaxWidth().widthIn(max = 480.dp)) {
            Column(Modifier.fillMaxWidth().padding(24.dp), verticalArrangement = Arrangement.spacedBy(14.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                Icon(destination.icon, null, Modifier.size(46.dp), tint = HomeScoutColors.blue)
                Text(destination.label, style = MaterialTheme.typography.headlineMedium)
                Surface(color = HomeScoutColors.paleAmber, shape = MaterialTheme.shapes.small) {
                    Text("DEVELOPMENT PREVIEW", Modifier.padding(horizontal = 12.dp, vertical = 7.dp), color = HomeScoutColors.navy, style = MaterialTheme.typography.labelMedium)
                }
                Text(
                    when (destination) {
                        Destination.Map -> "Map-based discovery is planned for a later phase. No map is connected in this preview."
                        Destination.Finance -> "SmartRent and financial learning are planned. No financial product, account, or payment is available here."
                        Destination.Neighbourhoods -> "Neighbourhood guides are planned. Area names shown elsewhere are sample content only."
                        Destination.Services -> "Moving and property service discovery is planned. No providers can be booked here."
                        Destination.Assistant -> "The HomeScout AI experience is planned. No AI model or assistant is connected."
                        Destination.Profile -> "Accounts, saved homes, and notifications are planned. Sign-in is not available in this phase."
                        else -> "This destination is a preview for a later phase."
                    },
                    style = MaterialTheme.typography.bodyLarge,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                OutlinedButton(onClick = onBack, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, null); Spacer(Modifier.width(8.dp)); Text("Go back")
                }
            }
        }
    }
}
