package ke.co.homescout.features.map

import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class MapModelsTest {
    @Test
    fun mapUsesOpenFreeMapStylesWithoutApiKeys() {
        assertEquals("https://tiles.openfreemap.org/styles/liberty", openFreeMapStyleUrl("liberty"))
        assertEquals("https://tiles.openfreemap.org/styles/bright", openFreeMapStyleUrl("bright"))
        assertEquals("https://tiles.openfreemap.org/styles/positron", openFreeMapStyleUrl("positron"))
        assertEquals("https://tiles.openfreemap.org/styles/dark", openFreeMapStyleUrl("dark"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun unknownMapStyleIsRejected() {
        openFreeMapStyleUrl("unknown-provider")
    }

    @Test
    fun filterQueryCarriesViewportAndOnlySelectedFilters() {
        val query = MapFilters(
            minRent = "12000",
            maxRent = "85000",
            propertyType = "apartment",
            bedrooms = 2,
            furnishing = "semi_furnished",
            verifiedOnly = true
        ).queryParameters(MapViewport(-90.0, -180.0, 90.0, 180.0))

        assertTrue(query.contains("south=-90.0"))
        assertTrue(query.contains("rent_min=12000"))
        assertTrue(query.contains("property_type=apartment"))
        assertTrue(query.contains("verified_only=true"))
        assertFalse(query.contains("include_demo=true"))
        assertTrue(query.contains("furnishing=semi_furnished"))
    }

    @Test(expected = IllegalArgumentException::class)
    fun invalidRentRangeIsRejected() {
        MapFilters(minRent = "50000", maxRent = "20000").validated()
    }

    @Test
    fun listingParserExcludesDemoAndListingsWithoutSourcedCoordinates() {
        val demo = listingJson().put("is_demo", true)
        assertEquals(null, MapListing.fromJson(demo))

        val unsourced = listingJson().put("coordinate_source", JSONObject.NULL)
        assertEquals(null, MapListing.fromJson(unsourced))

        assertEquals("KSh 68,000", formatKes(68_000))
    }

    private fun listingJson() = JSONObject()
        .put("id", "listing-1")
        .put("title", "Two-bedroom apartment")
        .put("rent_amount", "68000.00")
        .put("rent_frequency", "monthly")
        .put("bedrooms", 2)
        .put("bathrooms", "1.5")
        .put("furnishing", "unfurnished")
        .put("property_type", "apartment")
        .put("latitude", JSONObject.NULL)
        .put("longitude", JSONObject.NULL)
        .put("coordinate_source", JSONObject.NULL)
        .put("listing_status", "published")
        .put("availability_status", "available")
        .put("verification_status", "verified")
        .put("is_demo", false)
        .put("location", JSONObject().put("town_name", "Nairobi").put("neighbourhood_name", "Kilimani"))
}
