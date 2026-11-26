package ke.co.homescout.ui.components

import androidx.compose.animation.core.Animatable
import androidx.compose.animation.core.tween
import androidx.compose.foundation.background
import androidx.compose.foundation.layout.*
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.graphicsLayer
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import ke.co.homescout.ui.theme.HomeScoutColors

@Composable
fun HomeScoutSplash(onFinished: () -> Unit) {
    val entrance = remember { Animatable(.82f) }
    val progress = remember { Animatable(0f) }
    LaunchedEffect(Unit) {
        launch { entrance.animateTo(1f, tween(520)) }
        launch { progress.animateTo(1f, tween(1_500)) }
        delay(1_850)
        onFinished()
    }

    Box(Modifier.fillMaxSize().background(MaterialTheme.colorScheme.surface), contentAlignment = Alignment.Center) {
        Column(horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(12.dp)) {
            HomeScoutLogo(Modifier.graphicsLayer { scaleX = entrance.value; scaleY = entrance.value; alpha = entrance.value }, markSize = 76.dp, showWordmark = false)
            Text("HomeScout", style = MaterialTheme.typography.headlineLarge, color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.Bold, letterSpacing = (-.6).sp)
            Text("FIND YOUR NEXT PLACE", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant, letterSpacing = 2.sp)
            Spacer(Modifier.height(18.dp))
            LinearProgressIndicator(
                progress = { progress.value },
                modifier = Modifier.width(120.dp).height(3.dp).semantics { contentDescription = "Launching HomeScout" },
                color = HomeScoutColors.green,
                trackColor = HomeScoutColors.border
            )
        }
    }
}
