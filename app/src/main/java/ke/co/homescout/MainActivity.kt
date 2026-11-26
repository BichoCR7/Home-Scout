package ke.co.homescout

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.core.splashscreen.SplashScreen.Companion.installSplashScreen
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.material3.Surface
import androidx.compose.material3.MaterialTheme
import androidx.compose.ui.Modifier
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.runtime.setValue
import ke.co.homescout.navigation.HomeScoutApp
import ke.co.homescout.ui.components.HomeScoutSplash
import ke.co.homescout.ui.theme.HomeScoutTheme

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        installSplashScreen()
        super.onCreate(savedInstanceState)
        setContent {
            val preferences = getSharedPreferences("homescout-appearance", MODE_PRIVATE)
            var appearance by rememberSaveable { mutableStateOf(preferences.getString("appearance", "system") ?: "system") }
            var largerText by rememberSaveable { mutableStateOf(preferences.getBoolean("larger-text", false)) }
            HomeScoutTheme(
                darkTheme = when (appearance) {
                    "dark" -> true
                    "light" -> false
                    else -> androidx.compose.foundation.isSystemInDarkTheme()
                },
                textScale = if (largerText) 1.15f else 1f
            ) {
                Surface(Modifier.fillMaxSize(), color = MaterialTheme.colorScheme.background) {
                    var showSplash by rememberSaveable { mutableStateOf(true) }
                    if (showSplash) HomeScoutSplash(onFinished = { showSplash = false }) else HomeScoutApp(
                        onAppearanceChange = { value ->
                            appearance = value
                            preferences.edit().putString("appearance", value).apply()
                        },
                        onLargerTextChange = { value ->
                            largerText = value
                            preferences.edit().putBoolean("larger-text", value).apply()
                        }
                    )
                }
            }
        }
    }
}
