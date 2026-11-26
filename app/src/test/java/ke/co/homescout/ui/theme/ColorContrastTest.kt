package ke.co.homescout.ui.theme

import org.junit.Assert.assertTrue
import org.junit.Test

class ColorContrastTest {
    @Test
    fun interactiveAndStatusTextColorsMeetWcagAaForTheirSurfaces() {
        assertTrue(contrastRatio(0xFF2563EB.toInt(), 0xFFF6F8FB.toInt()) >= 4.5)
        assertTrue(contrastRatio(0xFF15803D.toInt(), 0xFFFFFFFF.toInt()) >= 4.5)
        assertTrue(contrastRatio(0xFF15803D.toInt(), 0xFFECFDF3.toInt()) >= 4.5)
        assertTrue(contrastRatio(0xFF65D991.toInt(), 0xFF142235.toInt()) >= 4.5)
    }

    @Test
    fun darkThemeFinanceTextAndActionsMeetWcagAaOnDarkSurfaces() {
        val darkBackground = 0xFF0B1421.toInt()
        val darkSurface = 0xFF142235.toInt()
        assertTrue(contrastRatio(0xFFE6EDF7.toInt(), darkBackground) >= 4.5)
        assertTrue(contrastRatio(0xFFE6EDF7.toInt(), darkSurface) >= 4.5)
        assertTrue(contrastRatio(0xFFA7B4C6.toInt(), darkSurface) >= 4.5)
        assertTrue(contrastRatio(0xFF7DA8FF.toInt(), darkSurface) >= 4.5)
        assertTrue(contrastRatio(0xFFFF8A80.toInt(), darkSurface) >= 4.5)
    }

    private fun contrastRatio(foreground: Int, background: Int): Double {
        val first = luminance(foreground)
        val second = luminance(background)
        val lighter = maxOf(first, second)
        val darker = minOf(first, second)
        return (lighter + 0.05) / (darker + 0.05)
    }

    private fun luminance(color: Int): Double {
        fun channel(shift: Int): Double {
            val value = ((color shr shift) and 0xFF) / 255.0
            return if (value <= 0.04045) value / 12.92 else Math.pow((value + 0.055) / 1.055, 2.4)
        }

        return 0.2126 * channel(16) + 0.7152 * channel(8) + 0.0722 * channel(0)
    }
}
