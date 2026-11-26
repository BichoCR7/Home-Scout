package ke.co.homescout.features.finance

import org.json.JSONArray
import org.json.JSONObject
import org.junit.Assert.assertEquals
import org.junit.Assert.assertFalse
import org.junit.Assert.assertTrue
import org.junit.Test

class SmartRentLoadTest {
    @Test
    fun financeSectionsRouteToTheirOwnContent() {
        assertEquals("Budget", smartRentContentSection("Budget", "Housing budget", "Compare"))
        assertEquals("Plan", smartRentContentSection("Budget", "Move-in costs", "Compare"))
        assertEquals("Discover", smartRentContentSection("Tools", "Housing budget", "Discover"))
        assertEquals("Savings", smartRentContentSection("Savings", "Housing budget", "Compare"))
        assertEquals("Overview", smartRentErrorSection("Budget"))
        assertEquals("Savings", smartRentErrorSection("Savings"))
        assertEquals("Learn", smartRentErrorSection("Learn"))
    }

    @Test
    fun overviewFailureDoesNotDiscardOtherFinanceSections() {
        val batch = assembleSmartRentLoadBatch(
            dashboard = FinanceLoadResult(JSONObject()),
            profile = FinanceLoadResult(JSONObject(), IllegalStateException("encryption key is configured")),
            assessment = FinanceLoadResult(JSONObject()),
            plans = FinanceLoadResult(JSONArray().put("move-in plan")),
            goals = FinanceLoadResult(JSONArray().put("savings goal")),
            records = FinanceLoadResult(JSONArray()),
            documents = FinanceLoadResult(JSONArray()),
            lessons = FinanceLoadResult(JSONObject()),
            comparisons = FinanceLoadResult(JSONArray().put("comparison")),
            leases = FinanceLoadResult(JSONArray()),
            alerts = FinanceLoadResult(JSONArray())
        )

        assertEquals(setOf("Overview"), batch.sectionErrors.keys)
        assertTrue(batch.sectionErrors.getValue("Overview").contains("HOMESCOUT_FINANCE_ENCRYPTION_KEY"))
        assertEquals("move-in plan", batch.snapshot.plans.getString(0))
        assertEquals("savings goal", batch.snapshot.goals.getString(0))
        assertEquals("comparison", batch.snapshot.comparisons.getString(0))
        assertFalse(batch.profileLoaded)
    }

    @Test
    fun recordsFailureIsScopedAndSuccessfulProfileRemainsLoaded() {
        val batch = assembleSmartRentLoadBatch(
            dashboard = FinanceLoadResult(JSONObject()),
            profile = FinanceLoadResult(JSONObject().put("is_configured", true)),
            assessment = FinanceLoadResult(JSONObject()),
            plans = FinanceLoadResult(JSONArray()),
            goals = FinanceLoadResult(JSONArray()),
            records = FinanceLoadResult(JSONArray(), IllegalStateException("request failed")),
            documents = FinanceLoadResult(JSONArray()),
            lessons = FinanceLoadResult(JSONObject()),
            comparisons = FinanceLoadResult(JSONArray()),
            leases = FinanceLoadResult(JSONArray()),
            alerts = FinanceLoadResult(JSONArray())
        )

        assertEquals(setOf("Records"), batch.sectionErrors.keys)
        assertTrue(batch.sectionErrors.getValue("Records").contains("Records could not reach HomeScout"))
        assertTrue(batch.profileLoaded)
    }
}
