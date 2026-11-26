package ke.co.homescout.features.profile

import androidx.compose.foundation.background
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.layout.widthIn
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.verticalScroll
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Email
import androidx.compose.material3.AlertDialog
import androidx.compose.material3.Button
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.draw.shadow
import androidx.compose.ui.graphics.Path
import androidx.compose.ui.graphics.Brush
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.drawscope.Fill
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ke.co.homescout.ui.components.HomeScoutLogo
import ke.co.homescout.ui.components.RemotePhoto
import ke.co.homescout.ui.theme.HomeScoutColors

@Composable
fun AuthEntryScreen(onSignIn: () -> Unit, onCreateAccount: () -> Unit, onBrowseAsGuest: () -> Unit) {
    var providerNotice by remember { mutableStateOf<String?>(null) }
    Column(
        Modifier.fillMaxSize().verticalScroll(rememberScrollState()).background(MaterialTheme.colorScheme.background),
        horizontalAlignment = Alignment.CenterHorizontally
    ) {
        Box(
            Modifier.fillMaxWidth().height(390.dp)
                .background(HomeScoutColors.navy)
        ) {
            RemotePhoto(
                url = "https://images.unsplash.com/photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1400&q=85",
                contentDescription = "Modern home exterior at golden hour",
                modifier = Modifier.fillMaxSize()
            ) {
                Box(Modifier.fillMaxSize().background(HomeScoutColors.navy))
            }
            Box(Modifier.fillMaxSize().background(Brush.verticalGradient(listOf(
                HomeScoutColors.navy.copy(alpha = .66f), Color.Transparent, HomeScoutColors.navy.copy(alpha = .92f)
            ))))
            Column(
                Modifier.align(Alignment.TopStart).padding(start = 24.dp, top = 28.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                HomeScoutLogo(markSize = 54.dp, wordmarkColor = Color.White)
                Text("KENYA, FIND YOUR PLACE", style = MaterialTheme.typography.labelMedium,
                    color = Color.White.copy(alpha = .88f), fontWeight = FontWeight.SemiBold, letterSpacing = 1.5.sp)
            }
            Column(
                Modifier.align(Alignment.BottomStart).padding(horizontal = 24.dp, vertical = 28.dp),
                verticalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                Text("A home that feels like yours.", style = MaterialTheme.typography.headlineMedium,
                    color = Color.White, fontWeight = FontWeight.Bold)
                Text("Explore places across Kenya with clearer choices at every step.",
                    style = MaterialTheme.typography.bodyLarge, color = Color.White.copy(alpha = .88f))
            }
        }

        Column(
            Modifier.fillMaxWidth().padding(horizontal = 22.dp, vertical = 22.dp)
                .widthIn(max = 520.dp).shadow(4.dp, RoundedCornerShape(24.dp))
                .clip(RoundedCornerShape(24.dp)).background(MaterialTheme.colorScheme.surface)
                .padding(20.dp),
            horizontalAlignment = Alignment.CenterHorizontally,
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Text("Welcome to HomeScout", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text("Sign in to save homes and continue your conversations with listing contacts.",
                style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Button(onClick = onSignIn, modifier = Modifier.fillMaxWidth().height(52.dp)) {
                androidx.compose.material3.Icon(Icons.Filled.Email, contentDescription = null)
                Spacer(Modifier.width(8.dp)); Text("Continue with email")
            }
            Row(Modifier.fillMaxWidth(), verticalAlignment = Alignment.CenterVertically) {
                androidx.compose.material3.HorizontalDivider(Modifier.weight(1f))
                Text("  or continue with  ", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.labelMedium)
                androidx.compose.material3.HorizontalDivider(Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                listOf("Google", "Facebook", "Apple").forEach { provider ->
                    OutlinedButton(
                        onClick = { providerNotice = provider },
                        modifier = Modifier.weight(1f).height(48.dp)
                            .semantics { contentDescription = "Continue with $provider; provider setup required" },
                        contentPadding = androidx.compose.foundation.layout.PaddingValues(horizontal = 4.dp)
                    ) {
                        Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            ProviderMark(provider)
                            Text(provider, maxLines = 1, style = MaterialTheme.typography.labelMedium)
                        }
                    }
                }
            }
            Row(verticalAlignment = Alignment.CenterVertically) {
                Text("Don't have an account?", color = MaterialTheme.colorScheme.onSurfaceVariant)
                TextButton(onClick = onCreateAccount) { Text("Sign up") }
            }
            TextButton(onClick = onBrowseAsGuest) { Text("Browse homes first") }
        }
    }
    providerNotice?.let { provider ->
        AlertDialog(
            onDismissRequest = { providerNotice = null },
            title = { Text("$provider sign-in isn’t configured") },
            text = { Text("This build has no $provider OAuth credentials, so HomeScout can’t safely sign you in with it yet. Use email sign-in for now. Apple sign-in also needs a configured Apple web authorization flow for Android.") },
            confirmButton = { TextButton(onClick = { providerNotice = null }) { Text("Got it") } }
        )
    }
}

@Composable
private fun ProviderMark(provider: String) {
    when (provider) {
        "Google" -> Text("G", color = Color(0xFF4285F4), fontWeight = FontWeight.Bold, fontSize = 20.sp)
        "Facebook" -> Text("f", color = Color(0xFF1877F2), fontWeight = FontWeight.Bold, fontSize = 21.sp)
        else -> Canvas(Modifier.size(18.dp)) {
            val scaleX = size.width / 24f
            val scaleY = size.height / 24f
            val apple = Path().apply {
                moveTo(12.1f * scaleX, 6.2f * scaleY)
                cubicTo(9.8f * scaleX, 4.9f * scaleY, 6.8f * scaleX, 5.4f * scaleY, 5.2f * scaleX, 8.1f * scaleY)
                cubicTo(2.9f * scaleX, 11.9f * scaleY, 4.8f * scaleX, 18.7f * scaleY, 8.0f * scaleX, 21.2f * scaleY)
                cubicTo(9.6f * scaleX, 22.5f * scaleY, 10.6f * scaleX, 21.2f * scaleY, 12.0f * scaleX, 21.2f * scaleY)
                cubicTo(13.5f * scaleX, 21.2f * scaleY, 14.2f * scaleX, 22.3f * scaleY, 16.0f * scaleX, 21.1f * scaleY)
                cubicTo(18.6f * scaleX, 19.3f * scaleY, 20.8f * scaleX, 13.5f * scaleY, 18.7f * scaleX, 11.8f * scaleY)
                cubicTo(17.1f * scaleX, 10.5f * scaleY, 15.4f * scaleX, 10.3f * scaleY, 13.8f * scaleX, 11.2f * scaleY)
                cubicTo(13.0f * scaleX, 11.6f * scaleY, 12.5f * scaleX, 11.7f * scaleY, 11.7f * scaleX, 11.2f * scaleY)
                cubicTo(10.7f * scaleX, 10.6f * scaleY, 9.4f * scaleX, 10.6f * scaleY, 8.3f * scaleX, 11.1f * scaleY)
                cubicTo(9.1f * scaleX, 8.0f * scaleY, 11.8f * scaleX, 8.2f * scaleY, 12.1f * scaleX, 6.2f * scaleY)
                close()
            }
            val leaf = Path().apply {
                moveTo(13.0f * scaleX, 5.7f * scaleY)
                cubicTo(13.1f * scaleX, 3.0f * scaleY, 15.7f * scaleX, 1.4f * scaleY, 18.5f * scaleX, 1.2f * scaleY)
                cubicTo(18.4f * scaleX, 4.1f * scaleY, 16.3f * scaleX, 6.0f * scaleY, 13.0f * scaleX, 6.3f * scaleY)
                close()
            }
            drawPath(apple, color = Color(0xFF171717), style = Fill)
            drawPath(leaf, color = Color(0xFF171717), style = Fill)
        }
    }
}
