package ke.co.homescout.ui.theme

import androidx.compose.foundation.isSystemInDarkTheme
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.darkColorScheme
import androidx.compose.material3.lightColorScheme
import androidx.compose.runtime.Composable
import androidx.compose.runtime.CompositionLocalProvider
import androidx.compose.ui.platform.LocalDensity
import androidx.compose.ui.unit.Density

private val LightScheme = lightColorScheme(
    primary = HomeScoutColors.blue,
    onPrimary = HomeScoutColors.white,
    primaryContainer = HomeScoutColors.paleBlue,
    onPrimaryContainer = HomeScoutColors.navy,
    secondary = HomeScoutColors.green,
    onSecondary = HomeScoutColors.white,
    tertiary = HomeScoutColors.amber,
    error = HomeScoutColors.red,
    background = HomeScoutColors.background,
    onBackground = HomeScoutColors.dark,
    surface = HomeScoutColors.white,
    onSurface = HomeScoutColors.dark,
    surfaceVariant = HomeScoutColors.paleBlue,
    onSurfaceVariant = HomeScoutColors.muted,
    outline = HomeScoutColors.border
)

private val DarkScheme = darkColorScheme(
    primary = ColorTokens.blueDark,
    onPrimary = HomeScoutColors.white,
    primaryContainer = HomeScoutColors.darkSurface,
    onPrimaryContainer = HomeScoutColors.darkText,
    secondary = ColorTokens.greenDark,
    onSecondary = HomeScoutColors.white,
    tertiary = HomeScoutColors.amber,
    error = ColorTokens.redDark,
    background = HomeScoutColors.darkBackground,
    onBackground = HomeScoutColors.darkText,
    surface = HomeScoutColors.darkSurface,
    onSurface = HomeScoutColors.darkText,
    surfaceVariant = HomeScoutColors.darkSurface,
    onSurfaceVariant = HomeScoutColors.darkMuted,
    outline = HomeScoutColors.darkBorder
)

private object ColorTokens {
    val blueDark = androidx.compose.ui.graphics.Color(0xFF7DA8FF)
    val greenDark = androidx.compose.ui.graphics.Color(0xFF65D991)
    val redDark = androidx.compose.ui.graphics.Color(0xFFFF8A80)
}

@Composable
fun HomeScoutTheme(
    darkTheme: Boolean = isSystemInDarkTheme(),
    textScale: Float = 1f,
    content: @Composable () -> Unit
) {
    val density = LocalDensity.current
    CompositionLocalProvider(LocalDensity provides Density(density.density, density.fontScale * textScale)) {
        MaterialTheme(
            colorScheme = if (darkTheme) DarkScheme else LightScheme,
            typography = HomeScoutTypography,
            shapes = HomeScoutShapes,
            content = content
        )
    }
}
