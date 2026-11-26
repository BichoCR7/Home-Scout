package ke.co.homescout.ui.components

import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.Dp
import androidx.compose.ui.unit.dp
import androidx.compose.ui.res.painterResource
import ke.co.homescout.R

@Composable
fun HomeScoutLogo(
    modifier: Modifier = Modifier,
    markSize: Dp = 40.dp,
    showWordmark: Boolean = true,
    wordmarkColor: androidx.compose.ui.graphics.Color = MaterialTheme.colorScheme.onBackground
) {
    Row(modifier, verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
        Image(painterResource(R.drawable.ic_homescout), contentDescription = "HomeScout house and location mark", modifier = Modifier.size(markSize))
        if (showWordmark) Text("HomeScout", style = MaterialTheme.typography.titleLarge, color = wordmarkColor, fontWeight = FontWeight.Bold)
    }
}
