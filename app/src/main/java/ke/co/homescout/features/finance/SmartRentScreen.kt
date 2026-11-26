package ke.co.homescout.features.finance

import android.content.Intent
import android.net.Uri
import androidx.compose.foundation.background
import androidx.compose.foundation.clickable
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.ArrowForward
import androidx.compose.material.icons.filled.AutoAwesome
import androidx.compose.material.icons.filled.DeleteOutline
import androidx.compose.material.icons.filled.Edit
import androidx.compose.material.icons.filled.Info
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Savings
import androidx.compose.material.icons.filled.Shield
import androidx.compose.material.icons.filled.Tune
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.platform.LocalContext
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import androidx.lifecycle.Lifecycle
import androidx.lifecycle.LifecycleEventObserver
import androidx.lifecycle.compose.LocalLifecycleOwner
import ke.co.homescout.data.remote.AuthApiException
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.MarketplaceApi
import ke.co.homescout.data.remote.MarketplaceFilters
import ke.co.homescout.data.remote.MarketplaceProperty
import ke.co.homescout.data.remote.PersonalHubApi
import ke.co.homescout.features.discover.DiscoverScreen
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.components.HomeScoutDateField
import ke.co.homescout.ui.components.HomeScoutTabs
import ke.co.homescout.ui.components.homeScoutSuccessTextColor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.async
import kotlinx.coroutines.coroutineScope
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.io.IOException
import java.time.ZoneId
import java.time.OffsetDateTime

internal data class SmartRentSnapshot(
    val dashboard: JSONObject,
    val profile: JSONObject,
    val assessment: JSONObject,
    val plans: JSONArray,
    val goals: JSONArray,
    val records: JSONArray,
    val receiptDocuments: JSONArray,
    val lessons: JSONObject,
    val comparisons: JSONArray,
    val leases: JSONArray,
    val alerts: JSONArray
)

internal data class FinanceLoadResult<T>(val value: T, val error: Exception? = null)

internal data class SmartRentLoadBatch(
    val snapshot: SmartRentSnapshot,
    val sectionErrors: Map<String, String>,
    val profileLoaded: Boolean
)

private data class IncomeSourceDraft(
    val label: String = "",
    val amount: String = "",
    val frequency: String = "monthly",
    val workDaysPerWeek: String = "5"
)

internal fun smartRentContentSection(activeSection: String, budgetSection: String, toolSection: String): String = when (activeSection) {
    "Budget" -> if (budgetSection == "Move-in costs") "Plan" else "Budget"
    "Tools" -> toolSection
    else -> activeSection
}

internal fun smartRentErrorSection(contentSection: String): String = if (contentSection == "Budget") "Overview" else contentSection

private const val FINANCE_LOAD_ATTEMPTS = 3

private fun isRetryableFinanceFailure(failure: Exception): Boolean = when (failure) {
    is IOException -> true
    is AuthApiException -> failure.statusCode in setOf(408, 429, 500, 502, 503, 504)
    else -> false
}

private suspend fun <T> financeLoad(
    fallback: T,
    loader: suspend () -> T
): FinanceLoadResult<T> {
    var attempt = 0
    while (attempt < FINANCE_LOAD_ATTEMPTS) {
        try {
            return FinanceLoadResult(loader())
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (failure: Exception) {
            attempt += 1
            if (attempt >= FINANCE_LOAD_ATTEMPTS || !isRetryableFinanceFailure(failure)) {
                return FinanceLoadResult(fallback, failure)
            }
            delay(350L * attempt)
        }
    }
    return FinanceLoadResult(fallback, IOException("HomeScout finance data could not be loaded."))
}

private fun financeLoadMessage(section: String, failure: Exception): String {
    val message = failure.message.orEmpty()
    return when {
        message.contains("encryption key", ignoreCase = true) ||
            message.contains("key is configured", ignoreCase = true) ->
            "$section needs the backend finance encryption key. Configure HOMESCOUT_FINANCE_ENCRYPTION_KEY and restart the API."
        failure is AuthApiException && failure.statusCode == 401 ->
            "Your HomeScout session expired and could not be renewed. Sign in again to load $section."
        failure is AuthApiException && failure.statusCode == 403 ->
            "This account does not have permission to load $section. Contact support if you think this is a mistake."
        failure is AuthApiException && failure.statusCode == 404 ->
            "The HomeScout server does not support this Finance request yet. Start the current backend version, then retry $section."
        failure is AuthApiException && failure.statusCode >= 500 ->
            "The HomeScout Finance service had a server error while loading $section. Retry after the API is ready."
        else ->
            "$section could not reach HomeScout. Check that the API is running at the configured address, then retry."
    }
}

internal fun assembleSmartRentLoadBatch(
    dashboard: FinanceLoadResult<JSONObject>,
    profile: FinanceLoadResult<JSONObject>,
    assessment: FinanceLoadResult<JSONObject>,
    plans: FinanceLoadResult<JSONArray>,
    goals: FinanceLoadResult<JSONArray>,
    records: FinanceLoadResult<JSONArray>,
    documents: FinanceLoadResult<JSONArray>,
    lessons: FinanceLoadResult<JSONObject>,
    comparisons: FinanceLoadResult<JSONArray>,
    leases: FinanceLoadResult<JSONArray>,
    alerts: FinanceLoadResult<JSONArray>
): SmartRentLoadBatch {
    fun sectionFailure(section: String, vararg results: FinanceLoadResult<*>): Pair<String, String>? {
        val failures = results.mapNotNull { it.error }.distinctBy { it.message }
        if (failures.isEmpty()) return null
        return section to failures.joinToString(" ") { financeLoadMessage(section, it) }
    }

    return SmartRentLoadBatch(
        snapshot = SmartRentSnapshot(
            dashboard = dashboard.value,
            profile = profile.value,
            assessment = assessment.value,
            plans = plans.value,
            goals = goals.value,
            records = records.value,
            receiptDocuments = documents.value,
            lessons = lessons.value,
            comparisons = comparisons.value,
            leases = leases.value,
            alerts = alerts.value
        ),
        sectionErrors = listOfNotNull(
            sectionFailure("Overview", dashboard, profile, assessment),
            sectionFailure("Plan", plans),
            sectionFailure("Savings", goals),
            sectionFailure("Compare", comparisons),
            sectionFailure("Learn", lessons),
            sectionFailure("Records", records, documents),
            sectionFailure("Lease", leases),
            sectionFailure("Alerts", alerts)
        ).toMap(),
        profileLoaded = profile.error == null
    )
}

private fun JSONObject.stringOrBlank(key: String): String = optString(key).takeUnless { it == "null" }.orEmpty()

private data class FinanceProfileDraft(val body: JSONObject?, val error: String? = null)

private fun financeProfileDraft(
    income: String,
    frequency: String,
    workDaysPerWeek: String,
    additionalIncomeSources: List<IncomeSourceDraft>,
    pattern: String,
    expenses: String,
    obligations: String,
    savings: String,
    rent: String,
    moveIn: String,
    utilities: String,
    transport: String,
    otherHousingCosts: String,
    householdSize: String,
    recentIncome: String,
    budgetLimits: Map<String, String>
): FinanceProfileDraft {
    fun amount(value: String, default: String? = null): Double? {
        if (value.isBlank() && default != null) return default.toDouble()
        return value.toDoubleOrNull()?.takeIf { it.isFinite() && it in 0.0..999_999_999_999.99 }
    }

    val monthlyIncome = amount(income, "0")
    val monthlyExpenses = amount(expenses, "0")
    val monthlyObligations = amount(obligations, "0")
    val currentSavings = amount(savings, "0")
    val targetRent = amount(rent, "0")
    val moveInCosts = amount(moveIn, "0")
    val monthlyUtilities = amount(utilities)
    val monthlyTransport = amount(transport, "0")
    val monthlyOtherHousingCosts = amount(otherHousingCosts, "0")
    val household = householdSize.toIntOrNull()
    val paidDays = workDaysPerWeek.toIntOrNull()
    if (monthlyIncome == null || monthlyExpenses == null || monthlyObligations == null ||
        currentSavings == null || targetRent == null || moveInCosts == null ||
        (utilities.isNotBlank() && monthlyUtilities == null) || monthlyTransport == null ||
        monthlyOtherHousingCosts == null || household == null || household !in 1..30 ||
        paidDays == null || paidDays !in 1..7 || additionalIncomeSources.size > 10
    ) {
        return FinanceProfileDraft(null, "Enter valid non-negative KES amounts and a household size from 1 to 30.")
    }

    val recentTokens = recentIncome.split(',', ' ', ';').filter(String::isNotBlank)
    val recentValues = recentTokens.map { it.trim().toDoubleOrNull() }
    if (recentValues.any { it == null || !it.isFinite() || it !in 0.0..999_999_999_999.99 }) {
        return FinanceProfileDraft(null, "Check each recent monthly income amount and separate entries with commas.")
    }
    val recent = recentValues.filterNotNull()
    if (recent.isNotEmpty() && recent.size < 3) {
        return FinanceProfileDraft(null, "Enter three or more recent monthly income values, or leave this field blank.")
    }

    val normalizedBudgets = JSONArray()
    for ((category, _) in financeBudgetCategories) {
        val rawLimit = budgetLimits[category].orEmpty()
        if (rawLimit.isBlank()) continue
        val monthlyLimit = amount(rawLimit)
            ?: return FinanceProfileDraft(null, "Enter valid non-negative KES limits for each filled category.")
        normalizedBudgets.put(JSONObject().put("category", category).put("monthly_limit", monthlyLimit))
    }

    val normalizedSources = JSONArray()
    for (source in additionalIncomeSources) {
        val sourceAmount = amount(source.amount)
        val sourceDays = source.workDaysPerWeek.toIntOrNull()
        if (source.label.isBlank() || sourceAmount == null ||
            source.frequency !in listOf("daily", "weekly", "biweekly", "twice_monthly", "monthly", "annual") ||
            sourceDays == null || sourceDays !in 1..7
        ) {
            return FinanceProfileDraft(null, "Complete or remove each added income source. Amounts must be non-negative KES values.")
        }
        normalizedSources.put(JSONObject().apply {
            put("label", source.label.trim())
            put("amount", sourceAmount)
            put("frequency", source.frequency)
            put("work_days_per_week", sourceDays)
        })
    }

    return FinanceProfileDraft(JSONObject().apply {
        put("income_amount", monthlyIncome)
        put("income_frequency", frequency)
        put("income_work_days_per_week", paidDays)
        put("additional_income_sources", normalizedSources)
        put("income_pattern", pattern)
        put("recent_monthly_income", JSONArray(recent))
        put("monthly_expenses", monthlyExpenses)
        put("monthly_obligations", monthlyObligations)
        put("current_savings", currentSavings)
        put("target_monthly_rent", targetRent)
        put("expected_move_in_total", moveInCosts)
        put("monthly_utility_budget", monthlyUtilities ?: JSONObject.NULL)
        put("monthly_transport_cost", monthlyTransport)
        put("monthly_housing_other_costs", monthlyOtherHousingCosts)
        put("budget_categories", normalizedBudgets)
        put("household_size", household)
        put("has_payslip", false)
    })
}

private fun exampleFinanceProfile(): JSONObject = JSONObject().apply {
    put("income_amount", 95_000)
    put("income_frequency", "monthly")
    put("income_work_days_per_week", 5)
    put("additional_income_sources", JSONArray())
    put("income_pattern", "variable")
    put("recent_monthly_income", JSONArray().put(82_000).put(90_000).put(95_000))
    put("monthly_expenses", 29_000)
    put("monthly_obligations", 9_000)
    put("current_savings", 26_000)
    put("target_monthly_rent", 24_000)
    put("expected_move_in_total", 82_000)
    put("monthly_utility_budget", 4_500)
    put("monthly_transport_cost", 7_500)
    put("monthly_housing_other_costs", 3_000)
    put("budget_categories", JSONArray())
    put("household_size", 2)
    put("has_payslip", false)
}

@Composable
fun SmartRentScreen(
    accessToken: String?,
    onSignIn: () -> Unit,
    onNavigate: (String) -> Unit,
    onPayments: () -> Unit
) {
    val api = remember { SmartRentApi() }
    val scope = rememberCoroutineScope()
    val lifecycleOwner = LocalLifecycleOwner.current
    val snackbar = remember { SnackbarHostState() }
    var activeSection by remember { mutableStateOf("Overview") }
    var budgetSection by remember { mutableStateOf("Housing budget") }
    var toolSection by remember { mutableStateOf("Compare") }
    val financeSections = listOf("Overview", "Budget", "Payments", "Savings", "Tools", "Records")
    val financeToolSections = listOf("Compare", "Discover", "Learn", "Lease", "Alerts", "AI")
    val contentSection = smartRentContentSection(activeSection, budgetSection, toolSection)
    val sectionErrorKey = smartRentErrorSection(contentSection)
    var snapshot by remember { mutableStateOf<SmartRentSnapshot?>(null) }
    var sectionErrors by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var loading by remember { mutableStateOf(false) }
    var working by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var previewAssessment by remember { mutableStateOf<JSONObject?>(null) }
    var previewIsExample by remember { mutableStateOf(false) }
    var exampleValuesLoaded by remember { mutableStateOf(false) }
    var coach by remember { mutableStateOf<JSONObject?>(null) }
    var discovery by remember { mutableStateOf<JSONObject?>(null) }
    var marketHomes by remember { mutableStateOf<List<MarketplaceProperty>>(emptyList()) }
    var compareIds by remember { mutableStateOf<Set<String>>(emptySet()) }
    var compareUtilities by remember { mutableStateOf("") }
    var compareWater by remember { mutableStateOf("") }
    var compareElectricity by remember { mutableStateOf("") }
    var compareGas by remember { mutableStateOf("") }
    var compareWaste by remember { mutableStateOf("") }
    var compareTransport by remember { mutableStateOf("") }
    var compareInternet by remember { mutableStateOf("") }
    var compareParking by remember { mutableStateOf("") }
    var compareOtherMonthly by remember { mutableStateOf("") }
    var compareMovingCost by remember { mutableStateOf("") }
    var utilityResult by remember { mutableStateOf<JSONObject?>(null) }
    var simulationResult by remember { mutableStateOf<JSONObject?>(null) }
    var rentChoiceResult by remember { mutableStateOf<JSONObject?>(null) }
    var editingPlan by remember { mutableStateOf<String?>(null) }
    var showShareDialog by remember { mutableStateOf<String?>(null) }
    var editingGoalId by remember { mutableStateOf<String?>(null) }
    var editGoalTitle by remember { mutableStateOf("") }
    var editGoalTarget by remember { mutableStateOf("") }
    var editGoalDate by remember { mutableStateOf("") }
    var profileIncome by remember { mutableStateOf("") }
    var profileFrequency by remember { mutableStateOf("monthly") }
    var profileWorkDays by remember { mutableStateOf("5") }
    var profileIncomeSources by remember { mutableStateOf(emptyList<IncomeSourceDraft>()) }
    var profilePattern by remember { mutableStateOf("steady") }
    var profileExpenses by remember { mutableStateOf("") }
    var profileObligations by remember { mutableStateOf("") }
    var profileSavings by remember { mutableStateOf("") }
    var profileRent by remember { mutableStateOf("") }
    var profileMoveIn by remember { mutableStateOf("") }
    var profileUtilities by remember { mutableStateOf("") }
    var profileTransport by remember { mutableStateOf("") }
    var profileHousingOther by remember { mutableStateOf("") }
    var profileRecent by remember { mutableStateOf("") }
    var budgetLimitValues by remember { mutableStateOf(financeBudgetCategories.associate { it.first to "" }) }
    var profileHouseholdSize by remember { mutableStateOf("1") }
    var planTitle by remember { mutableStateOf("") }
    var planRent by remember { mutableStateOf("") }
    var planDeposit by remember { mutableStateOf("") }
    var planRentEvidence by remember { mutableStateOf("user_entered") }
    var planDepositEvidence by remember { mutableStateOf("user_entered") }
    val planCosts = remember { mutableStateMapOf<String, String>() }
    val planCostEvidence = remember { mutableStateMapOf<String, String>() }
    var goalTitle by remember { mutableStateOf("") }
    var goalTarget by remember { mutableStateOf("") }
    var goalTargetDate by remember { mutableStateOf("") }
    var goalInitialSaved by remember { mutableStateOf("") }
    var goalPlannedMonthly by remember { mutableStateOf("") }
    var contributionAmounts by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var contributionRequestIds by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var shareMemberId by remember { mutableStateOf("") }
    var shareCanContribute by remember { mutableStateOf(true) }
    var recordTitle by remember { mutableStateOf("") }
    var recordAmount by remember { mutableStateOf("") }
    var recordCategory by remember { mutableStateOf("rent") }
    var recordReference by remember { mutableStateOf("") }
    var recordReceiptId by remember { mutableStateOf("") }
    var recordMethod by remember { mutableStateOf("not_recorded") }
    var recordDate by remember { mutableStateOf(java.time.LocalDate.now(ZoneId.of("Africa/Nairobi")).toString()) }
    var recordDueDate by remember { mutableStateOf("") }
    var recordNotes by remember { mutableStateOf("") }
    var recordPendingDeletion by remember { mutableStateOf<String?>(null) }
    var leaseTitle by remember { mutableStateOf("") }
    var leaseRent by remember { mutableStateOf("") }
    var leaseDeposit by remember { mutableStateOf("") }
    var leaseNote by remember { mutableStateOf("") }
    var editingLeaseId by remember { mutableStateOf<String?>(null) }
    var leaseStart by remember { mutableStateOf("") }
    var leaseEnd by remember { mutableStateOf("") }
    var leaseClauseTitle by remember { mutableStateOf("") }
    var leaseClauseSummary by remember { mutableStateOf("") }
    var leaseClauseQuestion by remember { mutableStateOf("") }
    var utilityEntries by remember { mutableStateOf("") }
    var utilityBreakdown by remember { mutableStateOf<Map<String, String>>(emptyMap()) }
    var simulatorTarget by remember { mutableStateOf("") }
    var simulatorSaved by remember { mutableStateOf("") }
    var simulatorMonthly by remember { mutableStateOf("") }
    var simulatorMonths by remember { mutableStateOf("6") }
    var customSimulatorMonths by remember { mutableStateOf("") }
    var rentChoiceCurrent by remember { mutableStateOf("") }
    var rentChoiceAlternative by remember { mutableStateOf("") }
    var rentChoiceMoving by remember { mutableStateOf("") }
    var rentChoiceMonths by remember { mutableStateOf("12") }

    suspend fun refresh() {
        val token = accessToken ?: return
        if (loading) return
        loading = true
        error = null
        sectionErrors = emptyMap()
        try {
            val loaded = withContext(Dispatchers.IO) {
                coroutineScope {
                    val dashboard = async { financeLoad(JSONObject()) { api.get("dashboard", token) } }
                    val profile = async { financeLoad(JSONObject()) { api.get("profile", token) } }
                    val assessment = async { financeLoad(JSONObject()) { api.get("assessment", token) } }
                    val plans = async { financeLoad(JSONArray()) { api.getList("move-in/plans", token) } }
                    val goals = async { financeLoad(JSONArray()) { api.getList("savings/goals", token) } }
                    val records = async { financeLoad(JSONArray()) { api.getList("records", token) } }
                    val documents = async { financeLoad(JSONArray()) { PersonalHubApi().getArray("hub/documents", token) } }
                    val lessons = async { financeLoad(JSONObject().put("lessons", JSONArray())) { api.get("lessons", token) } }
                    val comparisons = async { financeLoad(JSONArray()) { api.getList("comparisons", token) } }
                    val leases = async { financeLoad(JSONArray()) { api.getList("lease-guardian", token) } }
                    val alerts = async { financeLoad(JSONArray()) { api.getList("alerts", token) } }

                    val dashboardResult = dashboard.await()
                    val profileResult = profile.await()
                    val assessmentResult = assessment.await()
                    val plansResult = plans.await()
                    val goalsResult = goals.await()
                    val recordsResult = records.await()
                    val documentsResult = documents.await()
                    val lessonsResult = lessons.await()
                    val comparisonsResult = comparisons.await()
                    val leasesResult = leases.await()
                    val alertsResult = alerts.await()

                    assembleSmartRentLoadBatch(
                        dashboard = dashboardResult,
                        profile = profileResult,
                        assessment = assessmentResult,
                        plans = plansResult,
                        goals = goalsResult,
                        records = recordsResult,
                        documents = documentsResult,
                        lessons = lessonsResult,
                        comparisons = comparisonsResult,
                        leases = leasesResult,
                        alerts = alertsResult
                    )
                }
            }

            snapshot = loaded.snapshot
            sectionErrors = loaded.sectionErrors
            if (loaded.profileLoaded) {
                val profile = loaded.snapshot.profile
                val configured = profile.optBoolean("is_configured")
                profileIncome = if (configured) profile.optString("income_amount").takeUnless { it == "null" }.orEmpty() else ""
                profileFrequency = profile.optString("income_frequency", profileFrequency)
                profileWorkDays = profile.optString("income_work_days_per_week", "5")
                val incomeSources = profile.optJSONArray("additional_income_sources")
                profileIncomeSources = if (configured && incomeSources != null) {
                    (0 until incomeSources.length()).mapNotNull { index ->
                        incomeSources.optJSONObject(index)?.let { source ->
                            IncomeSourceDraft(
                                label = source.optString("label"),
                                amount = source.optString("amount"),
                                frequency = source.optString("frequency", "monthly"),
                                workDaysPerWeek = source.optString("work_days_per_week", "5")
                            )
                        }
                    }
                } else emptyList()
                profilePattern = profile.optString("income_pattern", profilePattern)
                profileExpenses = if (configured) profile.optString("monthly_expenses").takeUnless { it == "null" }.orEmpty() else ""
                profileObligations = if (configured) profile.optString("monthly_obligations").takeUnless { it == "null" }.orEmpty() else ""
                profileSavings = if (configured) profile.optString("current_savings").takeUnless { it == "null" }.orEmpty() else ""
                profileRent = if (configured) profile.optString("target_monthly_rent").takeUnless { it == "null" }.orEmpty() else ""
                profileMoveIn = if (configured) profile.optString("expected_move_in_total").takeUnless { it == "null" }.orEmpty() else ""
                profileUtilities = if (configured) profile.stringOrBlank("monthly_utility_budget") else ""
                profileTransport = if (configured) profile.optString("monthly_transport_cost", "0") else ""
                profileHousingOther = if (configured) profile.optString("monthly_housing_other_costs", "0") else ""
                profileHouseholdSize = if (configured) profile.optString("household_size", "1") else "1"
                profileRecent = if (configured) profile.optJSONArray("recent_monthly_income")?.join(",")?.replace("\"", "").orEmpty() else ""
                val savedBudgets = profile.optJSONArray("budget_categories") ?: JSONArray()
                budgetLimitValues = buildMap {
                    financeBudgetCategories.forEach { (category, _) -> put(category, "") }
                    for (index in 0 until savedBudgets.length()) {
                        val item = savedBudgets.optJSONObject(index) ?: continue
                        val category = item.optString("category")
                        if (category in financeBudgetCategories.map { it.first }) {
                            put(category, item.optString("monthly_limit"))
                        }
                    }
                }
            }
        } catch (cancelled: CancellationException) {
            throw cancelled
        } catch (failure: Exception) {
            error = failure.message ?: "HomeScout could not refresh SmartRent."
        } finally {
            loading = false
        }
    }

    fun runRequest(
        request: () -> Unit,
        success: String,
        refreshAfter: Boolean = true,
        onSuccess: (() -> Unit)? = null
    ) {
        scope.launch {
            working = true
            error = null
            val result = withContext(Dispatchers.IO) { runCatching(request) }
            result.onFailure { error = it.message ?: "That change could not be saved. Try again." }
            if (result.isSuccess) {
                snackbar.showSnackbar(success)
                onSuccess?.invoke()
                if (refreshAfter) refresh()
            }
            working = false
        }
    }

    val apiConfigured = ApiConfiguration.isConfigured
    DisposableEffect(lifecycleOwner, accessToken, apiConfigured) {
        val observer = if (accessToken != null && apiConfigured) {
            LifecycleEventObserver { _, event ->
                if (event == Lifecycle.Event.ON_RESUME) scope.launch { refresh() }
            }
        } else null
        observer?.let(lifecycleOwner.lifecycle::addObserver)
        if (
            accessToken != null && apiConfigured &&
            lifecycleOwner.lifecycle.currentState.isAtLeast(Lifecycle.State.RESUMED)
        ) {
            scope.launch { refresh() }
        }
        onDispose { observer?.let(lifecycleOwner.lifecycle::removeObserver) }
    }

    Scaffold(snackbarHost = { SnackbarHost(snackbar) }) { contentPadding ->
        LazyColumn(
            modifier = Modifier.fillMaxSize().padding(contentPadding),
            contentPadding = PaddingValues(start = 18.dp, end = 18.dp, top = 12.dp, bottom = 30.dp),
            verticalArrangement = Arrangement.spacedBy(16.dp)
        ) {
            item {
                Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                    Text("SmartRent", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.onSurface)
                    Text("Plan your next move with confidence.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(7.dp)) {
                        Icon(Icons.Filled.Lock, null, Modifier.size(15.dp), tint = MaterialTheme.colorScheme.secondary)
                        Text("Private to your account · KES planning estimates", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                }
            }
            item {
                HomeScoutTabs(
                    labels = financeSections,
                    selectedIndex = financeSections.indexOf(activeSection).coerceAtLeast(0),
                    onSelect = { index -> activeSection = financeSections[index]; error = null }
                )
            }
            if (activeSection == "Budget") item {
                HomeScoutTabs(
                    labels = listOf("Housing budget", "Move-in costs"),
                    selectedIndex = if (budgetSection == "Housing budget") 0 else 1,
                    onSelect = { index -> budgetSection = if (index == 0) "Housing budget" else "Move-in costs" }
                )
            }
            if (activeSection == "Tools") item {
                HomeScoutTabs(
                    labels = financeToolSections,
                    selectedIndex = financeToolSections.indexOf(toolSection).coerceAtLeast(0),
                    onSelect = { index -> toolSection = financeToolSections[index]; error = null }
                )
            }
            if (accessToken == null) {
                item {
                    EmptyStateCard("Sign in to use SmartRent", "Your personal budgets, savings goals, and records are account-scoped. Sign in to continue.", "Sign in", onSignIn)
                }
            } else if (!ApiConfiguration.isConfigured) {
                item {
                    EmptyStateCard("Connect the HomeScout API", "Configure HOMESCOUT_API_BASE_URL to load or save SmartRent data.", null, null)
                }
            } else {
                error?.let { message ->
                    item { ErrorCard(message, onRetry = { scope.launch { refresh() } }) }
                }
                if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
                sectionErrors[sectionErrorKey]?.let { message ->
                    item {
                        ErrorCard(title = "Could not load $sectionErrorKey data", message = message, onRetry = { scope.launch { refresh() } })
                    }
                }
                snapshot?.let { data ->
                    item {
                    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
                    when (contentSection) {
                        "Overview" -> FinanceOverviewContent(
                            data = data,
                            preview = previewAssessment,
                            previewIsExample = previewIsExample,
                            assessmentUnavailable = sectionErrors.containsKey("Overview"),
                            savingsUnavailable = sectionErrors.containsKey("Savings"),
                            onBudget = { activeSection = "Budget"; budgetSection = "Housing budget" },
                            onPayments = { activeSection = "Payments" },
                            onSavings = { activeSection = "Savings" },
                            onCompare = { activeSection = "Tools"; toolSection = "Compare" },
                            onRecords = { activeSection = "Records" }
                        )
                        "Payments" -> FinancePaymentsContent(onOpenPaymentHistory = onPayments)
                        "Budget" -> {
                            fun currentDraft() = financeProfileDraft(
                                profileIncome, profileFrequency, profileWorkDays, profileIncomeSources, profilePattern, profileExpenses,
                                profileObligations, profileSavings, profileRent, profileMoveIn,
                                profileUtilities, profileTransport, profileHousingOther,
                                profileHouseholdSize, profileRecent, budgetLimitValues
                            )
                            fun clearPreview() {
                                previewAssessment = null
                                previewIsExample = false
                                error = null
                            }
                            overviewContent(
                                data = data,
                                income = profileIncome,
                                frequency = profileFrequency,
                                workDaysPerWeek = profileWorkDays,
                                incomeSources = profileIncomeSources,
                                pattern = profilePattern,
                                expenses = profileExpenses,
                                obligations = profileObligations,
                                savings = profileSavings,
                                rent = profileRent,
                                moveIn = profileMoveIn,
                                utilities = profileUtilities,
                                transport = profileTransport,
                                otherHousingCosts = profileHousingOther,
                                householdSize = profileHouseholdSize,
                                recent = profileRecent,
                                preview = previewAssessment,
                                previewIsExample = previewIsExample,
                                exampleValuesLoaded = exampleValuesLoaded,
                                working = working,
                                onIncome = { profileIncome = it; clearPreview() },
                                onFrequency = { profileFrequency = it; clearPreview() },
                                onWorkDaysPerWeek = { profileWorkDays = it; clearPreview() },
                                onIncomeSources = { profileIncomeSources = it; clearPreview() },
                                onPattern = { profilePattern = it; clearPreview() },
                                onExpenses = { profileExpenses = it; clearPreview() },
                                onObligations = { profileObligations = it; clearPreview() },
                                onSavings = { profileSavings = it; clearPreview() },
                                onRent = { profileRent = it; clearPreview() },
                                onMoveIn = { profileMoveIn = it; clearPreview() },
                                onUtilities = { profileUtilities = it; clearPreview() },
                                onTransport = { profileTransport = it; clearPreview() },
                                onOtherHousingCosts = { profileHousingOther = it; clearPreview() },
                                onHouseholdSize = { profileHouseholdSize = it; clearPreview() },
                                onRecent = { profileRecent = it; clearPreview() },
                                onPreview = {
                                    val draft = currentDraft()
                                    val body = draft.body
                                    if (body == null) error = draft.error
                                    else {
                                        var result: JSONObject? = null
                                        runRequest(
                                            request = { result = api.send("assessment/preview", accessToken, "POST", body) },
                                            success = "Your figures were calculated. Nothing was saved.",
                                            onSuccess = { previewAssessment = result; previewIsExample = false },
                                            refreshAfter = false
                                        )
                                    }
                                },
                                onLoadExample = {
                                    val example = exampleFinanceProfile()
                                    profileIncome = example.optString("income_amount")
                                    profileFrequency = example.optString("income_frequency")
                                    profileWorkDays = example.optString("income_work_days_per_week", "5")
                                    profileIncomeSources = emptyList()
                                    profilePattern = example.optString("income_pattern")
                                    profileExpenses = example.optString("monthly_expenses")
                                    profileObligations = example.optString("monthly_obligations")
                                    profileSavings = example.optString("current_savings")
                                    profileRent = example.optString("target_monthly_rent")
                                    profileMoveIn = example.optString("expected_move_in_total")
                                    profileUtilities = example.optString("monthly_utility_budget")
                                    profileTransport = example.optString("monthly_transport_cost")
                                    profileHousingOther = example.optString("monthly_housing_other_costs")
                                    profileHouseholdSize = example.optString("household_size")
                                    profileRecent = example.optJSONArray("recent_monthly_income")?.join(",")?.replace("\"", "").orEmpty()
                                    exampleValuesLoaded = true
                                    var result: JSONObject? = null
                                    runRequest(
                                        request = { result = api.send("assessment/preview", accessToken, "POST", example) },
                                        success = "Example calculated for preview only; no data was saved.",
                                        onSuccess = { previewAssessment = result; previewIsExample = true },
                                        refreshAfter = false
                                    )
                                },
                                onClearExample = {
                                    exampleValuesLoaded = false
                                    clearPreview()
                                    scope.launch { refresh() }
                                },
                                onSave = {
                                    val draft = currentDraft()
                                    val body = draft.body
                                    if (body == null) error = draft.error
                                    else runRequest(
                                        request = { api.send("profile", accessToken, "PUT", body) },
                                        success = "Private planning inputs saved.",
                                        onSuccess = {
                                            exampleValuesLoaded = false
                                            previewAssessment = null
                                            previewIsExample = false
                                        }
                                    )
                                },
                                onCoach = { runRequest({ coach = api.send("coach", accessToken) }, "Budget coach preview updated.") },
                                onDiscovery = { activeSection = "Tools"; toolSection = "Discover" },
                                coach = coach
                            )
                            FinanceBudgetEditor(
                                values = budgetLimitValues,
                                dashboardBudget = data.dashboard.optJSONObject("monthly_budget"),
                                working = working,
                                onValueChange = { category, value -> budgetLimitValues = budgetLimitValues + (category to value) },
                                onFillExample = {
                                    fun sample(min: Int, max: Int) = (kotlin.random.Random.nextInt(min / 1_000, max / 1_000 + 1) * 1_000).toString()
                                    budgetLimitValues = mapOf(
                                        "rent" to sample(20_000, 50_000), "utilities" to sample(2_000, 8_000),
                                        "internet" to sample(1_000, 5_000), "transport" to sample(3_000, 12_000),
                                        "household" to sample(2_000, 10_000), "debt" to sample(0, 15_000),
                                        "expense" to sample(1_000, 8_000), "other" to sample(0, 5_000)
                                    )
                                },
                                onSave = {
                                    val draft = currentDraft()
                                    val body = draft.body
                                    if (body == null) error = draft.error
                                    else runRequest({ api.send("profile", accessToken, "PUT", body) }, "Monthly category limits saved.") {
                                        previewAssessment = null
                                        previewIsExample = false
                                        exampleValuesLoaded = false
                                    }
                                }
                            )
                        }
                        "Plan" -> planContent(data, editingPlan, planTitle, planRent, planDeposit, planRentEvidence, planDepositEvidence, planCosts, planCostEvidence, utilityEntries, utilityBreakdown, utilityResult, simulatorTarget, simulatorSaved, simulatorMonthly, simulatorMonths, customSimulatorMonths, simulationResult,
                            rentChoiceCurrent, rentChoiceAlternative, rentChoiceMoving, rentChoiceMonths, rentChoiceResult,
                            onCurrentHousingCost = { rentChoiceCurrent = it }, onAlternativeHousingCost = { rentChoiceAlternative = it }, onMovingCost = { rentChoiceMoving = it }, onChoiceMonths = { rentChoiceMonths = it },
                            onFillExample = {
                                val area = listOf("Kilimani", "Ruaka", "Ruiru", "Syokimau").random()
                                val sampleRent = kotlin.random.Random.nextInt(24, 46) * 1_000
                                editingPlan = null
                                planTitle = "DEMO · $area move-in estimate"
                                planRent = sampleRent.toString()
                                planDeposit = (sampleRent * listOf(1, 1, 2).random()).toString()
                                planRentEvidence = "estimated"
                                planDepositEvidence = "estimated"
                                planCosts.clear(); planCostEvidence.clear()
                                val sampleCosts = mapOf(
                                    "moving" to (kotlin.random.Random.nextInt(6, 19) * 1_000).toString(),
                                    "agent_fee" to (if (kotlin.random.Random.nextBoolean()) sampleRent / 2 else 0).toString(),
                                    "utilities" to (kotlin.random.Random.nextInt(2, 8) * 1_000).toString(),
                                    "internet" to (kotlin.random.Random.nextInt(2, 5) * 1_000).toString(),
                                    "furniture" to (kotlin.random.Random.nextInt(4, 16) * 1_000).toString(),
                                    "essentials" to (kotlin.random.Random.nextInt(2, 9) * 1_000).toString(),
                                    "cleaning" to (kotlin.random.Random.nextInt(1, 5) * 1_000).toString(),
                                    "transport" to (kotlin.random.Random.nextInt(2, 7) * 1_000).toString(),
                                    "other" to (kotlin.random.Random.nextInt(0, 4) * 1_000).toString()
                                )
                                sampleCosts.forEach { (key, value) ->
                                    planCosts[key] = value
                                    planCostEvidence[key] = "estimated"
                                }
                            },
                            onTitle = { planTitle = it }, onRent = { planRent = it }, onDeposit = { planDeposit = it }, onRentEvidence = { planRentEvidence = it }, onDepositEvidence = { planDepositEvidence = it }, onCost = { category, value -> planCosts[category] = value }, onCostEvidence = { category, value -> planCostEvidence[category] = value }, onUtilityEntries = { utilityEntries = it }, onUtilityCategory = { category, value -> utilityBreakdown = utilityBreakdown + (category to value) }, onUseUtilitiesInBudget = { total -> profileUtilities = total; previewAssessment = null; previewIsExample = false; activeSection = "Budget"; budgetSection = "Housing budget" }, onSimulatorTarget = { simulatorTarget = it }, onSimulatorSaved = { simulatorSaved = it }, onSimulatorMonthly = { simulatorMonthly = it }, onSimulatorMonths = { simulatorMonths = it }, onCustomMonths = { customSimulatorMonths = it },
                            onEditPlan = { plan ->
                                editingPlan = plan.optString("id")
                                planTitle = plan.optString("title")
                                planRent = plan.optString("monthly_rent")
                                planDeposit = plan.optString("deposit_amount")
                                planRentEvidence = plan.optString("rent_evidence", "user_entered")
                                planDepositEvidence = plan.optString("deposit_evidence", "user_entered")
                                planCosts.clear(); planCostEvidence.clear()
                                val lines = plan.optJSONArray("costs") ?: JSONArray()
                                for (index in 0 until lines.length()) {
                                    val line = lines.optJSONObject(index) ?: continue
                                    val category = line.optString("category")
                                    planCosts[category] = line.optString("amount")
                                    planCostEvidence[category] = line.optString("evidence", "user_entered")
                                }
                            },
                            onCancelPlanEdit = { editingPlan = null; planTitle = ""; planRent = ""; planDeposit = ""; planCosts.clear(); planCostEvidence.clear(); planRentEvidence = "user_entered"; planDepositEvidence = "user_entered" },
                            onSavePlan = {
                                val rent = planRent.toDoubleOrNull(); val deposit = planDeposit.ifBlank { "0" }.toDoubleOrNull()
                                val costLines = planCosts.mapNotNull { (category, value) -> value.toDoubleOrNull()?.takeIf { it > 0 }?.let { Triple(category, it, planCostEvidence[category] ?: "user_entered") } }
                                val invalidCost = planCosts.values.any { it.isNotBlank() && (it.toDoubleOrNull() == null || it.toDouble() < 0) }
                                if (planTitle.isBlank() || rent == null || rent < 0 || deposit == null || deposit < 0 || invalidCost) error = "Add a title and valid non-negative KES values for your plan."
                                else {
                                    val planId = editingPlan
                                    val method = if (planId == null) "POST" else "PATCH"
                                    val path = if (planId == null) "move-in/plans" else "move-in/plans/$planId"
                                    val body = JSONObject().apply {
                                        put("title", planTitle.trim()); put("rent_amount", rent); put("deposit_amount", deposit); put("rent_evidence", planRentEvidence); put("deposit_evidence", planDepositEvidence)
                                        put("costs", JSONArray().apply { costLines.forEach { (category, amount, evidence) -> put(JSONObject().put("category", category).put("amount", amount).put("evidence", evidence)) } })
                                    }
                                    runRequest({ api.send(path, accessToken, method, body) }, if (planId == null) "Move-in plan saved." else "Move-in plan updated.") {
                                        editingPlan = null; planTitle = ""; planRent = ""; planDeposit = ""; planCosts.clear(); planCostEvidence.clear(); planRentEvidence = "user_entered"; planDepositEvidence = "user_entered"
                                    }
                                }
                            },
                            onDeletePlan = { id -> runRequest({ api.send("move-in/plans/$id", accessToken, "DELETE") }, "Move-in plan removed.") },
                            onCreateGoalFromPlan = { title, total -> goalTitle = "Move-in: $title"; goalTarget = total; goalInitialSaved = ""; activeSection = "Savings" },
                            onEstimateUtilities = {
                                val rawValues = utilityEntries.split(",", ";", " ", "\n").map(String::trim).filter(String::isNotBlank)
                                val values = rawValues.mapNotNull(String::toDoubleOrNull)
                                val categoryValues = utilityBreakdown.filterValues(String::isNotBlank).mapValues { (_, value) -> value.toDoubleOrNull() }
                                val invalid = values.size != rawValues.size || categoryValues.values.any { it == null || it < 0 } || values.any { it < 0 }
                                if (invalid) error = "Use valid non-negative KES amounts. Separate past totals with commas."
                                else if (values.isEmpty() && categoryValues.isEmpty()) error = "Add a past utility total or one or more itemized monthly costs."
                                else runRequest({ utilityResult = api.send("utilities/estimate", accessToken, body = JSONObject().apply {
                                    if (values.isNotEmpty()) put("monthly_user_entries", JSONArray(values))
                                    put("monthly_by_category", JSONObject().apply { categoryValues.forEach { (name, amount) -> if (amount != null) put(name, amount) } })
                                }) }, "Your monthly utility estimate is ready.")
                            },
                            onSimulate = {
                                val target = simulatorTarget.toDoubleOrNull(); val saved = simulatorSaved.ifBlank { "0" }.toDoubleOrNull(); val monthly = simulatorMonthly.toDoubleOrNull(); val months = (if (simulatorMonths == "custom") customSimulatorMonths else simulatorMonths).toIntOrNull()
                                if (target == null || saved == null || monthly == null || months == null) error = "Enter valid savings amounts and a month count."
                                else runRequest({ simulationResult = api.send("savings/simulate", accessToken, body = JSONObject().put("target_amount", target).put("current_savings", saved).put("monthly_contribution", monthly).put("months", months)) }, "Savings projection calculated.")
                            },
                            onRentChoiceSimulate = {
                                val current = rentChoiceCurrent.toDoubleOrNull()
                                val alternative = rentChoiceAlternative.toDoubleOrNull()
                                val moving = rentChoiceMoving.ifBlank { "0" }.toDoubleOrNull()
                                val months = rentChoiceMonths.toIntOrNull()
                                if (current == null || current <= 0 || alternative == null || alternative < 0 || moving == null || moving < 0 || months == null || months !in 1..120) {
                                    error = "Enter a current housing cost above KSh 0, non-negative alternative and moving costs, and 1–120 months."
                                } else {
                                    runRequest(
                                        request = { rentChoiceResult = api.send("rent-choice/simulate", accessToken, body = JSONObject().put("current_monthly_housing_cost", current).put("alternative_monthly_housing_cost", alternative).put("one_time_moving_cost", moving).put("months", months)) },
                                        success = "Rent choice projection calculated.",
                                        refreshAfter = false
                                    )
                                }
                            },
                            working = working
                        )
                        "Savings" -> savingsContent(data, goalTitle, goalTarget, goalTargetDate, goalInitialSaved, goalPlannedMonthly, contributionAmounts,
                            onFillExample = {
                                val target = kotlin.random.Random.nextInt(65, 151) * 1_000
                                val saved = kotlin.random.Random.nextInt(5, (target / 1_000).coerceAtLeast(6)) * 1_000
                                goalTitle = "DEMO · ${listOf("Move-in", "Deposit", "Furniture", "Emergency") .random()} fund"
                                goalTarget = target.toString()
                                goalTargetDate = java.time.LocalDate.now(ZoneId.of("Africa/Nairobi")).plusMonths(kotlin.random.Random.nextLong(3, 10)).toString()
                                goalInitialSaved = saved.toString()
                                goalPlannedMonthly = (kotlin.random.Random.nextInt(5, 16) * 1_000).toString()
                            },
                            onGoalTitle = { goalTitle = it }, onGoalTarget = { goalTarget = it }, onGoalTargetDate = { goalTargetDate = it }, onGoalInitialSaved = { goalInitialSaved = it }, onGoalPlannedMonthly = { goalPlannedMonthly = it },
                            onCreateGoal = {
                                val target = goalTarget.toDoubleOrNull()
                                val initial = goalInitialSaved.ifBlank { "0" }.toDoubleOrNull()
                                val planned = goalPlannedMonthly.ifBlank { "0" }.toDoubleOrNull()
                                val validDate = goalTargetDate.isBlank() || runCatching { java.time.LocalDate.parse(goalTargetDate) }.isSuccess
                                if (goalTitle.isBlank() || target == null || target <= 0 || initial == null || initial < 0 || planned == null || planned < 0 || !validDate) error = "Add a goal title, target above KSh 0, non-negative savings and monthly plan, and choose a valid optional date."
                                else runRequest({ api.send("savings/goals", accessToken, body = JSONObject().apply { put("title", goalTitle.trim()); put("target_amount", target); put("initial_saved_amount", initial); put("planned_monthly_contribution", planned); if (goalTargetDate.isNotBlank()) put("target_date", goalTargetDate) }) }, "Virtual savings goal saved.") {
                                    goalTitle = ""; goalTarget = ""; goalTargetDate = ""; goalInitialSaved = ""; goalPlannedMonthly = ""
                                }
                            },
                            onContributionAmount = { id, value -> if (contributionAmounts[id] != value) contributionRequestIds = contributionRequestIds - id; contributionAmounts = contributionAmounts + (id to value) },
                            onContribute = { id ->
                                val amount = contributionAmounts[id]?.toDoubleOrNull()
                                if (amount == null || amount <= 0) error = "Enter a contribution amount above KSh 0."
                                else {
                                    val requestId = contributionRequestIds[id] ?: java.util.UUID.randomUUID().toString().also { contributionRequestIds = contributionRequestIds + (id to it) }
                                    runRequest(
                                        request = { api.send("savings/goals/$id/contributions", accessToken, body = JSONObject().put("amount", amount).put("request_id", requestId)) },
                                        success = "Manual contribution recorded.",
                                        onSuccess = { contributionRequestIds = contributionRequestIds - id; contributionAmounts = contributionAmounts + (id to "") }
                                    )
                                }
                            },
                            onArchive = { id -> runRequest({ api.send("savings/goals/$id", accessToken, "PATCH", JSONObject().put("status", "archived")) }, "Goal archived.") },
                            onComplete = { id -> runRequest({ api.send("savings/goals/$id", accessToken, "PATCH", JSONObject().put("status", "completed")) }, "Moving goal completed.") },
                            onShare = { showShareDialog = it },
                            onEdit = { id, name, amount, date -> editingGoalId = id; editGoalTitle = name; editGoalTarget = amount; editGoalDate = date.takeUnless { it == "null" }.orEmpty() },
                            working = working
                        )
                        "Compare" -> compareContent(data, marketHomes, compareIds, compareUtilities, compareWater, compareElectricity, compareGas, compareWaste, compareTransport, compareInternet, compareParking, compareOtherMonthly, compareMovingCost,
                            onUtilities = { compareUtilities = it }, onWater = { compareWater = it }, onElectricity = { compareElectricity = it }, onGas = { compareGas = it }, onWaste = { compareWaste = it }, onTransport = { compareTransport = it }, onInternet = { compareInternet = it }, onParking = { compareParking = it }, onOtherMonthly = { compareOtherMonthly = it }, onMovingCost = { compareMovingCost = it }, onSelected = { compareIds = it }, onLoadHomes = {
                            scope.launch { val result = withContext(Dispatchers.IO) { runCatching { MarketplaceApi().search(MarketplaceFilters(sortBy = "rent_low")) } }; result.onSuccess { marketHomes = it.filterNot(MarketplaceProperty::demo) }.onFailure { error = it.message } }
                        }, onCompare = {
                            val ids = compareIds.toList()
                            val extraValues = listOf(compareUtilities, compareWater, compareElectricity, compareGas, compareWaste, compareTransport, compareInternet, compareParking, compareOtherMonthly, compareMovingCost).filter(String::isNotBlank)
                            val validExtras = extraValues.all { it.toDoubleOrNull() != null && it.toDouble() >= 0 }
                            if (ids.size !in 2..4) error = "Choose between two and four available homes to compare."
                            else if (!validExtras) error = "Enter valid non-negative KES amounts for comparison costs."
                            else {
                                val monthlyByProperty = JSONObject().apply {
                                    ids.forEach { id ->
                                        val costs = JSONObject()
                                        compareUtilities.toDoubleOrNull()?.let { costs.put("utilities", it) }
                                        compareWater.toDoubleOrNull()?.let { costs.put("water", it) }
                                        compareElectricity.toDoubleOrNull()?.let { costs.put("electricity", it) }
                                        compareGas.toDoubleOrNull()?.let { costs.put("gas", it) }
                                        compareWaste.toDoubleOrNull()?.let { costs.put("waste_collection", it) }
                                        compareTransport.toDoubleOrNull()?.let { costs.put("transport", it) }
                                        compareInternet.toDoubleOrNull()?.let { costs.put("internet", it) }
                                        compareParking.toDoubleOrNull()?.let { costs.put("parking", it) }
                                        compareOtherMonthly.toDoubleOrNull()?.let { costs.put("other", it) }
                                        if (costs.length() > 0) put(id, costs)
                                    }
                                }
                                val oneTimeByProperty = JSONObject().apply {
                                    val amount = compareMovingCost.toDoubleOrNull()
                                    if (amount != null) ids.forEach { id -> put(id, JSONObject().put("moving", amount)) }
                                }
                                runRequest({ api.send("comparisons", accessToken, body = JSONObject().put("title", "Home comparison").put("property_ids", JSONArray(ids)).put("additional_monthly_costs", monthlyByProperty).put("one_time_costs", oneTimeByProperty)) }, "True-cost comparison saved.")
                            }
                        }, onOpenListing = { id -> onNavigate("property/$id") })
                        "Discover" -> discoveryContent(discovery, onLoad = { runRequest({ discovery = api.get("discovery?limit=30", accessToken) }, "Budget-based homes refreshed.") }, onOpen = { id -> onNavigate("property/$id") })
                        "Learn" -> learnContent(data, accessToken, api, ::runRequest)
                        "Records" -> recordsContent(data, recordTitle, recordAmount, recordCategory, recordReference, recordReceiptId, recordMethod, recordDate, recordDueDate, recordNotes, onTitle = { recordTitle = it }, onAmount = { recordAmount = it }, onCategory = { recordCategory = it }, onReference = { recordReference = it }, onReceipt = { recordReceiptId = it }, onMethod = { recordMethod = it }, onDate = { recordDate = it }, onDueDate = { recordDueDate = it }, onNotes = { recordNotes = it }, onFillExample = {
                            recordTitle = "DEMO · ${listOf("Monthly rent", "Utility bill", "Moving expense", "Internet setup").random()}"
                            recordCategory = listOf("rent", "utilities", "moving", "internet").random()
                            recordAmount = (kotlin.random.Random.nextInt(2, 51) * 1_000).toString()
                            recordReference = "DEMO-${kotlin.random.Random.nextInt(100000, 999999)}"
                            recordMethod = listOf("mpesa", "bank_transfer", "cash").random()
                            recordDate = java.time.LocalDate.now(ZoneId.of("Africa/Nairobi")).minusDays(kotlin.random.Random.nextLong(0, 28)).toString()
                            recordDueDate = ""
                            recordNotes = "DEMO · Example only. This is a private manual note, not a payment processed or verified by HomeScout."
                            recordReceiptId = ""
                        }, onUpload = { onNavigate("hub/documents") }, onDelete = { recordPendingDeletion = it }, onSave = {
                            val amount = recordAmount.toDoubleOrNull()
                            val parsedDate = runCatching { java.time.LocalDate.parse(recordDate) }.getOrNull()
                            val parsedDueDate = recordDueDate.takeIf(String::isNotBlank)?.let { runCatching { java.time.LocalDate.parse(it) }.getOrNull() }
                            val dueDateInvalid = (recordDueDate.isNotBlank() && (parsedDueDate == null || parsedDueDate.isBefore(java.time.LocalDate.now(ZoneId.of("Africa/Nairobi"))))) || (recordCategory == "receipt" && recordDueDate.isNotBlank())
                            if (recordTitle.isBlank() || amount == null || amount < 0 || parsedDate == null || dueDateInvalid) error = "Add a title, a non-negative KES amount, and valid dates. Upcoming due dates must be today or later."
                            else runRequest({ api.send("records", accessToken, body = JSONObject().put("category", recordCategory).put("title", recordTitle.trim()).put("amount", amount).put("record_date", parsedDate.atStartOfDay(ZoneId.of("Africa/Nairobi")).toOffsetDateTime().toString()).put("due_date", parsedDueDate?.toString() ?: JSONObject.NULL).put("payment_method", recordMethod).put("notes", recordNotes.takeIf(String::isNotBlank) ?: JSONObject.NULL).put("reference", recordReference).apply { if (recordReceiptId.isNotBlank()) put("private_document_id", recordReceiptId) }) }, if (parsedDueDate == null) "Manual housing record saved." else "Upcoming expense reminder saved.") {
                                recordTitle = ""; recordAmount = ""; recordReference = ""; recordReceiptId = ""; recordDueDate = ""; recordNotes = ""
                            }
                        })
                        "Lease" -> leaseContent(data, leaseTitle, leaseRent, leaseDeposit, leaseNote, leaseStart, leaseEnd, leaseClauseTitle, leaseClauseSummary, leaseClauseQuestion, editingLeaseId,
                            onTitle = { leaseTitle = it }, onRent = { leaseRent = it }, onDeposit = { leaseDeposit = it }, onNote = { leaseNote = it },
                            onStart = { leaseStart = it }, onEnd = { leaseEnd = it }, onClauseTitle = { leaseClauseTitle = it }, onClauseSummary = { leaseClauseSummary = it }, onClauseQuestion = { leaseClauseQuestion = it },
                            onFillExample = {
                                val start = java.time.LocalDate.now(ZoneId.of("Africa/Nairobi")).plusDays(kotlin.random.Random.nextLong(3, 31))
                                leaseTitle = "DEMO · Rental terms to review"
                                leaseRent = (kotlin.random.Random.nextInt(18, 51) * 1_000).toString()
                                leaseDeposit = leaseRent
                                leaseNote = "DEMO · Sample figures and notes for practice. Confirm all terms against your actual agreement."
                                leaseStart = start.toString()
                                leaseEnd = start.plusMonths(kotlin.random.Random.nextLong(6, 25)).toString()
                                leaseClauseTitle = listOf("Water charges", "Repairs", "Notice period", "Service charge").random()
                                leaseClauseSummary = "DEMO · Ask who is responsible and how the amount is calculated."
                                leaseClauseQuestion = "Can you confirm this term in writing before I sign?"
                            },
                            onSave = {
                                val rent = leaseRent.ifBlank { "0" }.toDoubleOrNull(); val deposit = leaseDeposit.ifBlank { "0" }.toDoubleOrNull()
                                val validDates = listOf(leaseStart, leaseEnd).all { it.isBlank() || runCatching { java.time.LocalDate.parse(it) }.isSuccess }
                                val hasClause = listOf(leaseClauseTitle, leaseClauseSummary, leaseClauseQuestion).any(String::isNotBlank)
                                val validClause = !hasClause || leaseClauseTitle.isNotBlank()
                                val parsedStart = runCatching { java.time.LocalDate.parse(leaseStart) }.getOrNull()
                                val parsedEnd = runCatching { java.time.LocalDate.parse(leaseEnd) }.getOrNull()
                                if (leaseTitle.isBlank() || rent == null || deposit == null || !validDates || !validClause || (parsedStart != null && parsedEnd != null && parsedEnd < parsedStart)) error = "Check the title, amounts, lease dates, and clause title."
                                else {
                                    val obligations = JSONArray()
                                    if (hasClause) obligations.put(JSONObject().put("title", leaseClauseTitle.trim()).put("plain_language_note", leaseClauseSummary.takeIf(String::isNotBlank) ?: JSONObject.NULL).put("user_question", leaseClauseQuestion.takeIf(String::isNotBlank) ?: JSONObject.NULL))
                                    val leaseId = editingLeaseId
                                    val method = if (leaseId == null) "POST" else "PATCH"
                                    val path = if (leaseId == null) "lease-guardian" else "lease-guardian/$leaseId"
                                    val body = JSONObject().put("title", leaseTitle.trim()).put("monthly_rent", rent).put("deposit_amount", deposit).put("private_notes", leaseNote).put("obligations", obligations)
                                    body.put("lease_start", leaseStart.takeIf(String::isNotBlank) ?: JSONObject.NULL)
                                    body.put("lease_end", leaseEnd.takeIf(String::isNotBlank) ?: JSONObject.NULL)
                                    runRequest({ api.send(path, accessToken, method, body) }, if (leaseId == null) "Private lease notes saved." else "Lease notes updated.") {
                                        editingLeaseId = null; leaseTitle = ""; leaseRent = ""; leaseDeposit = ""; leaseNote = ""; leaseStart = ""; leaseEnd = ""; leaseClauseTitle = ""; leaseClauseSummary = ""; leaseClauseQuestion = ""
                                    }
                                }
                            },
                            onEdit = { id, item ->
                                editingLeaseId = id; leaseTitle = item.optString("title"); leaseRent = item.optString("monthly_rent"); leaseDeposit = item.optString("deposit_amount"); leaseNote = item.stringOrBlank("private_notes"); leaseStart = item.stringOrBlank("lease_start"); leaseEnd = item.stringOrBlank("lease_end")
                                val obligation = item.optJSONArray("obligations")?.optJSONObject(0)
                                leaseClauseTitle = obligation?.optString("title").orEmpty(); leaseClauseSummary = obligation?.optString("plain_language_note").orEmpty().takeUnless { it == "null" }.orEmpty(); leaseClauseQuestion = obligation?.optString("user_question").orEmpty().takeUnless { it == "null" }.orEmpty()
                            },
                            onCancel = { editingLeaseId = null; leaseTitle = ""; leaseRent = ""; leaseDeposit = ""; leaseNote = ""; leaseStart = ""; leaseEnd = ""; leaseClauseTitle = ""; leaseClauseSummary = ""; leaseClauseQuestion = "" },
                            onDelete = { id -> runRequest({ api.send("lease-guardian/$id", accessToken, "DELETE") }, "Lease notes removed.") })
                        "Alerts" -> alertsContent(data, accessToken, api, ::runRequest)
                        "AI" -> aiContent(coach, onAsk = { onNavigate("assistant?intent=budget_planning") })
                    }
                    }
                    }
                }
            }
        }
        if (showShareDialog != null && accessToken != null) {
            AlertDialog(
                onDismissRequest = { showShareDialog = null },
                title = { Text("Share this moving goal") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("Only the goal is shared. The member will not see your RentScore, budget, or other records.")
                        OutlinedTextField(shareMemberId, { shareMemberId = it }, label = { Text("Member HomeScout user ID") }, singleLine = true, modifier = Modifier.fillMaxWidth())
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Checkbox(shareCanContribute, { shareCanContribute = it })
                            Text("Allow manual contributions")
                        }
                    }
                },
                confirmButton = {
                    TextButton(onClick = {
                        val goalId = showShareDialog.orEmpty()
                        if (shareMemberId.isBlank()) error = "Enter the HomeScout account ID to share with."
                        else runRequest({ api.send("savings/goals/$goalId/shares", accessToken, body = JSONObject().put("user_id", shareMemberId.trim()).put("can_contribute", shareCanContribute)) }, "Goal shared with the selected account.")
                        showShareDialog = null
                    }) { Text("Share goal") }
                },
                dismissButton = { TextButton(onClick = { showShareDialog = null }) { Text("Cancel") } }
            )
        }
        if (editingGoalId != null && accessToken != null) {
            AlertDialog(
                onDismissRequest = { editingGoalId = null },
                title = { Text("Edit moving goal") },
                text = {
                    Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        OutlinedTextField(editGoalTitle, { editGoalTitle = it }, label = { Text("Goal name") }, modifier = Modifier.fillMaxWidth())
                        AmountField("Target amount (KES)", editGoalTarget) { editGoalTarget = it }
                        HomeScoutDateField(editGoalDate, { editGoalDate = it }, "Target date · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                    }
                },
                confirmButton = {
                    TextButton(onClick = {
                        val amount = editGoalTarget.toDoubleOrNull()
                        val id = editingGoalId.orEmpty()
                        val validDate = editGoalDate.isBlank() || runCatching { java.time.LocalDate.parse(editGoalDate) }.isSuccess
                        if (editGoalTitle.isBlank() || amount == null || amount <= 0 || !validDate) error = "Enter a goal title, positive target, and a valid optional date."
                        else runRequest({ api.send("savings/goals/$id", accessToken, "PATCH", JSONObject().apply { put("title", editGoalTitle.trim()); put("target_amount", amount); put("target_date", if (editGoalDate.isBlank()) JSONObject.NULL else editGoalDate) }) }, "Moving goal updated.") { editingGoalId = null }
                    }) { Text("Save changes") }
                },
                dismissButton = { TextButton(onClick = { editingGoalId = null }) { Text("Cancel") } }
            )
        }
        recordPendingDeletion?.let { recordId ->
            val token = accessToken
            if (token != null) AlertDialog(
                onDismissRequest = { recordPendingDeletion = null },
                title = { Text("Remove this finance record?") },
                text = { Text("The private note will be deleted from your account. This does not reverse or change any payment.") },
                confirmButton = {
                    TextButton(onClick = {
                        recordPendingDeletion = null
                        runRequest({ api.send("records/$recordId", token, "DELETE") }, "Finance record removed.")
                    }) { Text("Remove") }
                },
                dismissButton = { TextButton(onClick = { recordPendingDeletion = null }) { Text("Cancel") } }
            )
        }
    }
}

@Composable
private fun overviewContent(
    data: SmartRentSnapshot, income: String, frequency: String, workDaysPerWeek: String,
    incomeSources: List<IncomeSourceDraft>, pattern: String,
    expenses: String, obligations: String, savings: String, rent: String, moveIn: String, utilities: String,
    transport: String, otherHousingCosts: String, householdSize: String, recent: String,
    preview: JSONObject?, previewIsExample: Boolean, exampleValuesLoaded: Boolean, working: Boolean,
    onIncome: (String) -> Unit, onFrequency: (String) -> Unit,
    onWorkDaysPerWeek: (String) -> Unit, onIncomeSources: (List<IncomeSourceDraft>) -> Unit,
    onPattern: (String) -> Unit,
    onExpenses: (String) -> Unit, onObligations: (String) -> Unit, onSavings: (String) -> Unit,
    onRent: (String) -> Unit, onMoveIn: (String) -> Unit, onUtilities: (String) -> Unit,
    onTransport: (String) -> Unit, onOtherHousingCosts: (String) -> Unit,
    onHouseholdSize: (String) -> Unit, onRecent: (String) -> Unit,
    onPreview: () -> Unit, onLoadExample: () -> Unit, onClearExample: () -> Unit,
    onSave: () -> Unit, onCoach: () -> Unit, onDiscovery: () -> Unit, coach: JSONObject?
) {
    val configured = data.profile.optBoolean("is_configured")
    val assessment = preview ?: data.assessment
    val hasAssessment = configured || preview != null
    var showAdditionalInputs by remember { mutableStateOf(false) }
    var showBudgetCoach by remember { mutableStateOf(false) }
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        Text("Housing budget", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Enter your own figures. A payslip is not required.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                if (exampleValuesLoaded) {
                    Text("Example figures are illustrative. Review or edit them; they are saved only if you choose the save button below.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                    TextButton(onClick = onClearExample, enabled = !working, modifier = Modifier.align(Alignment.End)) { Text("Clear example") }
                }
                AmountField("Income amount (KES)", income, onIncome)
                ChoiceField("Income frequency", frequency, listOf("daily", "weekly", "biweekly", "twice_monthly", "monthly", "annual"), onFrequency)
                if (frequency == "daily") {
                    OutlinedTextField(workDaysPerWeek, onWorkDaysPerWeek, label = { Text("Paid workdays per week (1–7)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(), singleLine = true)
                    Text("Daily income uses the work schedule you choose, multiplied across 52 weeks and divided by 12.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                ChoiceField("Income pattern", pattern, listOf("steady", "variable", "seasonal"), onPattern)
                AmountField("Other monthly expenses (exclude the items below)", expenses, onExpenses)
                AmountField("Monthly obligations", obligations, onObligations)
                AmountField("Current savings", savings, onSavings)
                AmountField("Target monthly rent", rent, onRent)
                AmountField("Expected move-in costs", moveIn, onMoveIn)
                TextButton(onClick = { showAdditionalInputs = !showAdditionalInputs }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text(if (showAdditionalInputs) "Hide additional details" else "Add income sources and monthly details")
                }
                if (showAdditionalInputs) {
                    Text("Additional income sources", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    Text("Add recurring income such as freelance work or a second job. Recent monthly history below should include your total income from all sources.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    incomeSources.forEachIndexed { index, source ->
                        HomeScoutCard(Modifier.fillMaxWidth()) {
                            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text("Income source ${index + 1}", modifier = Modifier.weight(1f), fontWeight = FontWeight.Medium)
                                    TextButton(onClick = { onIncomeSources(incomeSources.filterIndexed { itemIndex, _ -> itemIndex != index }) }) { Text("Remove") }
                                }
                                OutlinedTextField(source.label, { value -> onIncomeSources(incomeSources.mapIndexed { itemIndex, item -> if (itemIndex == index) item.copy(label = value) else item }) }, label = { Text("Source name") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                                AmountField("Income amount (KES)", source.amount) { value -> onIncomeSources(incomeSources.mapIndexed { itemIndex, item -> if (itemIndex == index) item.copy(amount = value) else item }) }
                                ChoiceField("Income frequency", source.frequency, listOf("daily", "weekly", "biweekly", "twice_monthly", "monthly", "annual")) { value -> onIncomeSources(incomeSources.mapIndexed { itemIndex, item -> if (itemIndex == index) item.copy(frequency = value) else item }) }
                                if (source.frequency == "daily") {
                                    OutlinedTextField(source.workDaysPerWeek, { value -> onIncomeSources(incomeSources.mapIndexed { itemIndex, item -> if (itemIndex == index) item.copy(workDaysPerWeek = value) else item }) }, label = { Text("Paid workdays per week (1–7)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(), singleLine = true)
                                }
                            }
                        }
                    }
                    if (incomeSources.size < 10) {
                        OutlinedButton(onClick = { onIncomeSources(incomeSources + IncomeSourceDraft()) }, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text("Add income source") }
                    }
                    AmountField("Monthly utilities (water, power, internet, etc.)", utilities, onUtilities)
                    AmountField("Monthly transport costs", transport, onTransport)
                    AmountField("Other monthly housing costs (e.g. parking)", otherHousingCosts, onOtherHousingCosts)
                    OutlinedTextField(householdSize, onHouseholdSize, label = { Text("Household size") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(), singleLine = true)
                    OutlinedTextField(recent, onRecent, label = { Text("Recent total monthly income (optional; comma separated)") }, supportingText = { Text("Enter at least 3 months including all income sources for variable or seasonal income.") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                }
                if (assessment.optJSONArray("suggestions")?.length() ?: 0 > 0) {
                    assessment.optJSONArray("suggestions")?.let { items ->
                        for (i in 0 until items.length()) Text("• ${items.optString(i)}", style = MaterialTheme.typography.bodyMedium)
                    }
                }
                if (hasAssessment) {
                    HomeScoutCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                            Text("Monthly calculation", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                            FinanceMetricRow("Conservative monthly income", assessment.optString("conservative_monthly_income"))
                            FinanceMetricRow("Non-housing commitments", assessment.optString("non_housing_committed_costs"))
                            FinanceMetricRow("Housing before rent", assessment.optString("housing_costs_excluding_rent"))
                            FinanceMetricRow("Total monthly housing cost", assessment.optString("total_monthly_housing_cost"))
                            FinanceMetricRow("Surplus / deficit", assessment.optString("monthly_surplus_or_deficit", assessment.optString("remaining_after_target_rent")))
                            if (!assessment.isNull("rent_to_income_percent")) FinanceMetricRow("Rent share of income", "${assessment.optString("rent_to_income_percent")}%")
                        }
                    }
                    Text(assessment.optString("method"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text(assessment.optString("disclaimer", "Planning estimate only; not a credit score or listing eligibility rule."), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                }
                OutlinedButton(onClick = onPreview, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(if (working) "Calculating…" else "Calculate preview without saving") }
                OutlinedButton(onClick = onLoadExample, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Try example KES budget") }
                Button(onClick = onSave, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(if (working) "Saving…" else if (exampleValuesLoaded) "Save these figures to my account" else "Save & calculate") }
            }
        }
        Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
            TextButton(onClick = { showBudgetCoach = !showBudgetCoach }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                Text(if (showBudgetCoach) "Hide budget coach" else "Budget coach · rule-based tips")
            }
            if (showBudgetCoach) {
                Text("Uses your saved figures and fixed planning rules. No AI service is connected.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = onCoach, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Icon(Icons.Filled.AutoAwesome, null); Spacer(Modifier.width(8.dp)); Text("Refresh planning tips") }
                coach?.let { value -> value.optJSONArray("messages")?.let { messages -> for (i in 0 until messages.length()) Text("• ${messages.optString(i)}", style = MaterialTheme.typography.bodyMedium) } }
            }
        }
        OutlinedButton(onClick = onDiscovery, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Icon(Icons.Filled.ArrowForward, null); Spacer(Modifier.width(8.dp)); Text("Find homes within your budget") }
        Text("Based on your entries • private to this account", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun FinanceMetricRow(label: String, amount: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(label, modifier = Modifier.weight(1f), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text(if (amount.isBlank() || amount == "null") "Not available" else if (amount.endsWith("%")) amount else ksh(amount), style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
    }
}

@Composable
private fun planContent(
    data: SmartRentSnapshot, editingPlanId: String?, title: String, rent: String, deposit: String,
    rentEvidence: String, depositEvidence: String, costs: Map<String, String>, costEvidence: Map<String, String>,
    utilityEntries: String, utilityBreakdown: Map<String, String>, utilityResult: JSONObject?, target: String, saved: String,
    monthly: String, months: String, customMonths: String, simulation: JSONObject?,
    currentHousingCost: String, alternativeHousingCost: String, movingCost: String, choiceMonths: String,
    rentChoiceResult: JSONObject?,
    onCurrentHousingCost: (String) -> Unit, onAlternativeHousingCost: (String) -> Unit,
    onMovingCost: (String) -> Unit, onChoiceMonths: (String) -> Unit,
    onFillExample: () -> Unit,
    onTitle: (String) -> Unit, onRent: (String) -> Unit, onDeposit: (String) -> Unit,
    onRentEvidence: (String) -> Unit, onDepositEvidence: (String) -> Unit,
    onCost: (String, String) -> Unit, onCostEvidence: (String, String) -> Unit,
    onUtilityEntries: (String) -> Unit, onUtilityCategory: (String, String) -> Unit, onUseUtilitiesInBudget: (String) -> Unit, onSimulatorTarget: (String) -> Unit,
    onSimulatorSaved: (String) -> Unit, onSimulatorMonthly: (String) -> Unit, onSimulatorMonths: (String) -> Unit, onCustomMonths: (String) -> Unit,
    onEditPlan: (JSONObject) -> Unit, onCancelPlanEdit: () -> Unit,
    onSavePlan: () -> Unit, onDeletePlan: (String) -> Unit, onCreateGoalFromPlan: (String, String) -> Unit,
    onEstimateUtilities: () -> Unit, onSimulate: () -> Unit,
    onRentChoiceSimulate: () -> Unit, working: Boolean
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        SectionHeading("Plan your move", "Label each figure as user-entered or estimated; listing figures should be confirmed with the provider.")
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Move-in cost planner", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                OutlinedButton(onClick = onFillExample, enabled = !working, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                Text("DEMO figures change each time. Review them, then tap Save move-in plan if you want this sample stored.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedTextField(title, onTitle, label = { Text("Plan name") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                AmountField("Monthly rent (KES)", rent, onRent)
                ChoiceField("Rent figure source", rentEvidence, listOf("user_entered", "listing", "estimated"), onRentEvidence)
                AmountField("Deposit (KES)", deposit, onDeposit)
                ChoiceField("Deposit figure source", depositEvidence, listOf("user_entered", "listing", "estimated"), onDepositEvidence)
                listOf("moving", "agent_fee", "utilities", "internet", "furniture", "essentials", "cleaning", "transport", "other").forEach { category ->
                    AmountField("${category.replace('_', ' ').replaceFirstChar(Char::uppercase)} (KES)", costs[category].orEmpty()) { onCost(category, it) }
                    ChoiceField("${category.replace('_', ' ').replaceFirstChar(Char::uppercase)} source", costEvidence[category] ?: "user_entered", listOf("user_entered", "listing", "estimated")) { onCostEvidence(category, it) }
                }
                Text("Each figure keeps its source label. Confirm agent fees and listing figures with the provider.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = onSavePlan, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(if (editingPlanId == null) "Save move-in plan" else "Update move-in plan") }
                if (editingPlanId != null) TextButton(onClick = onCancelPlanEdit, modifier = Modifier.align(Alignment.End)) { Text("Cancel editing") }
            }
        }
        Text("Saved move-in plans", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
        if (data.plans.length() == 0) Text("No move-in plans yet.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        for (i in 0 until data.plans.length()) {
            val plan = data.plans.optJSONObject(i) ?: continue
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.fillMaxWidth().padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(plan.optString("title"), fontWeight = FontWeight.SemiBold)
                            Text("${ksh(plan.optString("total_move_in_cost"))} estimated to move in", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("First month ${ksh(plan.optString("monthly_rent"))} · deposit ${ksh(plan.optString("deposit_amount"))}", style = MaterialTheme.typography.bodySmall)
                        }
                        IconButton(onClick = { onEditPlan(plan) }, modifier = Modifier.semantics { contentDescription = "Edit ${plan.optString("title")} move-in plan" }) { Icon(Icons.Filled.Edit, "Edit move-in plan") }
                        IconButton(onClick = { onDeletePlan(plan.optString("id")) }) { Icon(Icons.Filled.DeleteOutline, "Delete move-in plan") }
                    }
                    val costLines = plan.optJSONArray("costs") ?: JSONArray()
                    for (costIndex in 0 until costLines.length()) {
                        val line = costLines.optJSONObject(costIndex) ?: continue
                        Text("${line.optString("category").replace('_', ' ').replaceFirstChar(Char::uppercase)} · ${ksh(line.optString("amount"))} · ${line.optString("evidence").replace('_', ' ')}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    val total = plan.optString("total_move_in_cost").toDoubleOrNull() ?: 0.0
                    val trackedSavings = data.profile.optString("current_savings").toDoubleOrNull() ?: 0.0
                    Text("If you allocate all your reported savings (${ksh(trackedSavings.toString())}), the estimated gap is ${ksh((total - trackedSavings).coerceAtLeast(0.0).toString())}. This does not reserve money.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                    OutlinedButton(onClick = { onCreateGoalFromPlan(plan.optString("title"), total.toString()) }, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text("Create a savings goal from this plan") }
                }
            }
        }
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Utility expense predictor", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                Text("Summarizes the monthly figures you enter. It is not a provider quote or future bill.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                listOf("water" to "Water", "electricity" to "Electricity", "internet" to "Internet", "cooking_gas" to "Cooking gas", "waste_collection" to "Waste collection", "other" to "Other").forEach { (key, label) ->
                    AmountField("$label per month (KES)", utilityBreakdown[key].orEmpty()) { onUtilityCategory(key, it) }
                }
                OutlinedTextField(utilityEntries, onUtilityEntries, label = { Text("Past total bills (optional, comma separated)") }, supportingText = { Text("Enter bills like 2,400, 3,100, 2,850 to summarize history.") }, modifier = Modifier.fillMaxWidth())
                OutlinedButton(onClick = onEstimateUtilities, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Calculate my monthly estimate") }
                utilityResult?.let { result ->
                    Text("Itemized monthly estimate: ${ksh(result.optString("monthly_total", "0"))}", color = MaterialTheme.colorScheme.onSurface, fontWeight = FontWeight.SemiBold)
                    if (result.optInt("sample_count") > 0) Text("Past bills: median ${ksh(result.optString("median"))} · range ${ksh(result.optString("minimum"))}–${ksh(result.optString("maximum"))} from ${result.optInt("sample_count")} entries", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    TextButton(onClick = { onUseUtilitiesInBudget(result.optString("monthly_total", "0")) }) { Text("Use this estimate in my affordability budget") }
                }
            }
        }
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Rent-to-savings simulator", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                AmountField("Savings target (KES)", target, onSimulatorTarget)
                AmountField("Already saved (KES)", saved, onSimulatorSaved)
                AmountField("Monthly contribution (KES)", monthly, onSimulatorMonthly)
                ChoiceField("Period", months, listOf("3", "6", "12", "24", "custom"), onSimulatorMonths)
                if (months == "custom") OutlinedTextField(customMonths, onCustomMonths, label = { Text("Custom months (1–120)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(), singleLine = true)
                Button(onClick = onSimulate, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Simulate savings") }
                simulation?.let { Text("Projected ${ksh(it.optString("projected_total"))} after ${it.optInt("months")} months · ${if (it.optBoolean("will_reach_target")) "target reached" else "target not reached"}", fontWeight = FontWeight.SemiBold) }
                Text("Virtual planning only. HomeScout does not hold or transfer funds.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Compare a rent change", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                Text("Compare your current and alternative monthly housing costs after a move. Enter rent plus recurring utilities and other housing costs in each amount.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                AmountField("Current total housing cost per month (KES)", currentHousingCost, onCurrentHousingCost)
                AmountField("Alternative total housing cost per month (KES)", alternativeHousingCost, onAlternativeHousingCost)
                AmountField("One-time moving cost (KES)", movingCost, onMovingCost)
                OutlinedTextField(choiceMonths, onChoiceMonths, label = { Text("Projection period (months, 1–120)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number), modifier = Modifier.fillMaxWidth(), singleLine = true)
                Button(onClick = onRentChoiceSimulate, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Compare housing costs") }
                rentChoiceResult?.let { result ->
                    Text("${ksh(result.optString("net_savings_after_move_cost"))} net difference after ${result.optInt("months")} months, including the move cost.", fontWeight = FontWeight.SemiBold)
                    Text("Current cost over period: ${ksh(result.optString("current_housing_cost_over_period"))} · alternative with move: ${ksh(result.optString("alternative_cost_over_period_including_move"))}", style = MaterialTheme.typography.bodySmall)
                    val breakEven = result.opt("break_even_month")
                    Text(if (breakEven == null || breakEven == JSONObject.NULL) "No break-even point from the entered figures." else "Moving cost is recovered after approximately ${result.optInt("break_even_month")} months.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("Assumes the entered costs stay unchanged; excludes costs you did not enter and any investment return.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                Text("Planning projection only. It does not guarantee savings or affordability.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun savingsContent(
    data: SmartRentSnapshot, title: String, target: String, targetDate: String, initialSaved: String,
    plannedMonthly: String, contributions: Map<String, String>,
    onFillExample: () -> Unit,
    onGoalTitle: (String) -> Unit, onGoalTarget: (String) -> Unit, onGoalTargetDate: (String) -> Unit,
    onGoalInitialSaved: (String) -> Unit, onGoalPlannedMonthly: (String) -> Unit,
    onCreateGoal: () -> Unit, onContributionAmount: (String, String) -> Unit,
    onContribute: (String) -> Unit, onArchive: (String) -> Unit, onComplete: (String) -> Unit,
    onShare: (String) -> Unit, onEdit: (String, String, String, String) -> Unit, working: Boolean
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        SectionHeading("Virtual moving goals", "Track progress manually. HomeScout never holds, receives, or transfers the money.")
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Create a goal", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                OutlinedButton(onClick = onFillExample, enabled = !working, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                Text("DEMO amounts change each time. Review them, then tap Create virtual goal to save the example to your account. No money moves.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedTextField(title, onGoalTitle, label = { Text("Goal name") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                AmountField("Target amount (KES)", target, onGoalTarget)
                AmountField("Already saved for this goal (KES)", initialSaved, onGoalInitialSaved)
                AmountField("Planned monthly contribution (KES, optional)", plannedMonthly, onGoalPlannedMonthly)
                val targetValue = target.toDoubleOrNull()
                val savedValue = initialSaved.ifBlank { "0" }.toDoubleOrNull()
                if (targetValue != null && targetValue > 0 && savedValue != null && savedValue >= 0) {
                    Text("Preview · ${ksh(savedValue.toString())} saved · ${ksh((targetValue - savedValue).coerceAtLeast(0.0).toString())} left", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                }
                Text("Use only money you have actually set aside. This tracker does not move or hold funds.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                HomeScoutDateField(targetDate, onGoalTargetDate, "Target date · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                Button(onClick = onCreateGoal, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Icon(Icons.Filled.Savings, null); Spacer(Modifier.width(8.dp)); Text("Create virtual goal") }
            }
        }
        for (i in 0 until data.goals.length()) {
            val goal = data.goals.optJSONObject(i) ?: continue
            val id = goal.optString("id")
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(goal.optString("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                            Text("${ksh(goal.optString("current_amount"))} of ${ksh(goal.optString("target_amount"))} · ${goal.optString("status")}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                            Text("${ksh(goal.optString("remaining_amount", "0"))} left to target", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                        }
                        if (goal.optBoolean("is_owner")) {
                            Row {
                                IconButton(onClick = { onEdit(id, goal.optString("title"), goal.optString("target_amount"), goal.optString("target_date")) }) { Icon(Icons.Filled.Edit, "Edit moving goal") }
                                IconButton(onClick = { onShare(id) }) { Icon(Icons.Filled.ArrowForward, "Share this goal") }
                            }
                        }
                    }
                    LinearProgressIndicator(progress = { (goal.optInt("progress_percent") / 100f).coerceIn(0f, 1f) }, modifier = Modifier.fillMaxWidth())
                    Text("${goal.optInt("progress_percent")}% tracked · ${goal.optString("disclaimer")}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (goal.optString("target_date").isNotBlank()) Text("Target date ${goal.optString("target_date")}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    goal.optString("required_monthly_contribution").takeUnless { it.isBlank() || it == "null" }?.let { Text("To meet your date: ${ksh(it)} per month · ${ksh(goal.optString("required_weekly_contribution"))} per week based on current tracked progress.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface) }
                    goal.optString("estimated_completion_date").takeUnless { it.isBlank() || it == "null" }?.let { Text("At your planned ${ksh(goal.optString("planned_monthly_contribution"))}/month pace, estimated completion is $it (${goal.optInt("estimated_months_to_completion")} months).", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    val members = goal.optJSONArray("members")
                    if (members != null && members.length() > 0) Text("Shared with ${members.length()} HomeScout account${if (members.length() == 1) "" else "s"}", style = MaterialTheme.typography.labelMedium)
                    if (goal.optString("status") == "open" && (goal.optBoolean("is_owner") || goal.optBoolean("can_contribute"))) {
                        OutlinedTextField(contributions[id].orEmpty(), { onContributionAmount(id, it) }, label = { Text("Record a manual contribution (KES)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth(), singleLine = true)
                        Button(onClick = { onContribute(id) }, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Record contribution") }
                    }
                    if (goal.optBoolean("is_owner") && goal.optString("status") == "open") {
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            TextButton(onClick = { onComplete(id) }) { Text("Mark complete") }
                            TextButton(onClick = { onArchive(id) }) { Text("Archive goal") }
                        }
                    }
                }
            }
        }
        if (data.goals.length() == 0) EmptyStateCard("Your goals appear here", "Create a private tracker or share a single goal with people you choose.", null, null)
        Text("Members only see the goal you share; your profile, RentScore, and finance records remain private.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun compareContent(
    data: SmartRentSnapshot,
    homes: List<MarketplaceProperty>,
    selected: Set<String>,
    utilities: String,
    water: String,
    electricity: String,
    gas: String,
    waste: String,
    transport: String,
    internet: String,
    parking: String,
    otherMonthly: String,
    moving: String,
    onUtilities: (String) -> Unit,
    onWater: (String) -> Unit,
    onElectricity: (String) -> Unit,
    onGas: (String) -> Unit,
    onWaste: (String) -> Unit,
    onTransport: (String) -> Unit,
    onInternet: (String) -> Unit,
    onParking: (String) -> Unit,
    onOtherMonthly: (String) -> Unit,
    onMovingCost: (String) -> Unit,
    onSelected: (Set<String>) -> Unit,
    onLoadHomes: () -> Unit,
    onCompare: () -> Unit,
    onOpenListing: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        SectionHeading("True-cost comparison", "Select 2–4 currently available, non-demo homes. Compare rent with your own extra-cost estimates.")
        OutlinedButton(onClick = onLoadHomes, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Icon(Icons.Filled.Tune, null); Spacer(Modifier.width(8.dp)); Text("Load homes to compare") }
        if (homes.isEmpty()) Text("No live HomeScout listings are loaded. Connect the property API to compare current listings.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        homes.take(30).forEach { home ->
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Row(Modifier.fillMaxWidth().clickable { onOpenListing(home.id) }.padding(12.dp), verticalAlignment = Alignment.CenterVertically) {
                    Checkbox(checked = home.id in selected, onCheckedChange = { checked -> onSelected(if (checked) selected + home.id else selected - home.id) })
                    Column(Modifier.weight(1f)) {
                        Text(home.title, fontWeight = FontWeight.SemiBold)
                        Text("${ksh(home.rentAmount)} / ${home.rentFrequency} · ${home.location}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("Tap to view details", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary)
                    }
                }
            }
        }
        Text("Extra costs below apply to each selected home and are user-entered.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        AmountField("General utilities per month (KES)", utilities, onUtilities)
        AmountField("Water per month (KES)", water, onWater)
        AmountField("Electricity per month (KES)", electricity, onElectricity)
        AmountField("Cooking gas per month (KES)", gas, onGas)
        AmountField("Waste collection per month (KES)", waste, onWaste)
        AmountField("Transport per month (KES)", transport, onTransport)
        AmountField("Internet per month (KES)", internet, onInternet)
        AmountField("Parking per month (KES)", parking, onParking)
        AmountField("Other costs per month (KES)", otherMonthly, onOtherMonthly)
        AmountField("Moving cost (one-time)", moving, onMovingCost)
        Button(onClick = onCompare, enabled = selected.size in 2..4, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Save comparison (${selected.size}/4)") }
        Text("Saved comparisons: ${data.comparisons.length()}. Rent and deposit reflect current listing data. Confirm totals with the property contact.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        for (i in 0 until data.comparisons.length()) {
            val item = data.comparisons.optJSONObject(i) ?: continue
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(item.optString("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    val properties = item.optJSONArray("properties") ?: JSONArray()
                    for (j in 0 until properties.length()) {
                        val prop = properties.optJSONObject(j) ?: continue
                        Text("${prop.optString("title")} · known monthly subtotal ${ksh(prop.optString("known_monthly_cost_subtotal", prop.optString("total_monthly_cost")))} · deposit ${prop.optString("deposit").takeUnless { it == "null" }?.let(::ksh) ?: "not listed"}")
                        Text("Known move-in subtotal: ${ksh(prop.optString("known_move_in_cost_subtotal", prop.optString("user_entered_move_in_costs")))}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        val missingMonthly = prop.optJSONArray("missing_monthly_cost_categories")
                        val missingOneTime = prop.optJSONArray("missing_move_in_cost_categories")
                        if ((missingMonthly?.length() ?: 0) > 0 || (missingOneTime?.length() ?: 0) > 0) {
                            Text("Incomplete estimate · not entered: ${buildList { for (index in 0 until (missingMonthly?.length() ?: 0)) add(missingMonthly!!.optString(index).replace('_', ' ')); for (index in 0 until (missingOneTime?.length() ?: 0)) add(missingOneTime!!.optString(index).replace('_', ' ')) }.distinct().joinToString()}. Missing figures are not counted as zero.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.tertiary)
                        }
                    }
                }
            }
        }
    }
}

@Composable
private fun discoveryContent(result: JSONObject?, onLoad: () -> Unit, onOpen: (String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(14.dp)) {
        SectionHeading("Homes within your budget", "This private filter does not share your budget with landlords or agents.")
        Button(onClick = onLoad, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Find available homes within budget") }
        if (result == null) Text("Results include only currently published, available, non-demo listings.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        result?.let { data ->
            Text("Suggested monthly budget: ${ksh(data.optString("suggested_monthly_budget"))} · ${data.optInt("result_count")} homes", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            val items = data.optJSONArray("items") ?: JSONArray()
            if (items.length() == 0) EmptyStateCard("No available homes under this budget", "Try adjusting your private inputs or search the full Discover tab.", null, null)
            for (i in 0 until items.length()) {
                val prop = items.optJSONObject(i) ?: continue
                HomeScoutCard(Modifier.fillMaxWidth().clickable { onOpen(prop.optString("id")) }) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Text(prop.optString("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text("${ksh(prop.optString("rent_amount"))} / month · ${prop.optString("location")}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("${prop.optInt("bedrooms")} bedrooms · ${prop.optString("verification_status").replace('_', ' ')}", style = MaterialTheme.typography.bodySmall)
                        Text(prop.optString("why_recommended"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                    }
                }
            }
        }
    }
}

@Composable
private fun learnContent(data: SmartRentSnapshot, token: String, api: SmartRentApi, runRequest: (() -> Unit, String) -> Unit) {
    val context = LocalContext.current
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeading("Housing literacy academy", "Short lessons with a knowledge check. Learning records are private to you.")
        val lessons = data.lessons.optJSONArray("items") ?: JSONArray()
        Text("${data.lessons.optInt("completed_count")} lessons completed", fontWeight = FontWeight.SemiBold, color = homeScoutSuccessTextColor())
        for (i in 0 until lessons.length()) {
            val lesson = lessons.optJSONObject(i) ?: continue
            val quiz = lesson.optJSONObject("quiz") ?: JSONObject()
            val options = quiz.optJSONArray("options") ?: JSONArray()
            var selected by remember(lesson.optString("slug")) { mutableIntStateOf(-1) }
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(lesson.optString("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(lesson.optString("body"), style = MaterialTheme.typography.bodyMedium)
                    val sources = lesson.optJSONArray("source_urls") ?: JSONArray()
                    for (sourceIndex in 0 until sources.length()) {
                        val source = sources.optString(sourceIndex)
                        TextButton(onClick = {
                            runCatching { context.startActivity(Intent(Intent.ACTION_VIEW, Uri.parse(source))) }
                        }) { Text("Open official safety source ${sourceIndex + 1}") }
                    }
                    Text(quiz.optString("question"), fontWeight = FontWeight.SemiBold)
                    for (j in 0 until options.length()) Row(Modifier.fillMaxWidth().clickable { selected = j }, verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected == j, onClick = { selected = j })
                        Text(options.optString(j), style = MaterialTheme.typography.bodySmall)
                    }
                    OutlinedButton(onClick = {
                        if (selected < 0) return@OutlinedButton
                        runRequest({ api.send("lessons/${lesson.optString("slug")}/quiz", token, body = JSONObject().put("answers", JSONArray().put(selected))) }, "Lesson check saved.")
                    }, enabled = selected >= 0, modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp)) { Text(lesson.optJSONObject("progress")?.let { "Review answer" } ?: "Check answer") }
                }
            }
        }
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(10.dp), verticalAlignment = Alignment.CenterVertically) {
                Icon(Icons.Filled.Shield, null, tint = MaterialTheme.colorScheme.secondary)
                Text("Fraud safety: pause when pressured, verify independently, and never share account PINs or passwords.", style = MaterialTheme.typography.bodyMedium)
            }
        }
    }
}

@Composable
private fun recordsContent(
    data: SmartRentSnapshot,
    title: String,
    amount: String,
    category: String,
    reference: String,
    receiptId: String,
    paymentMethod: String,
    recordDate: String,
    dueDate: String,
    notes: String,
    onTitle: (String) -> Unit,
    onAmount: (String) -> Unit,
    onCategory: (String) -> Unit,
    onReference: (String) -> Unit,
    onReceipt: (String) -> Unit,
    onMethod: (String) -> Unit,
    onDate: (String) -> Unit,
    onDueDate: (String) -> Unit,
    onNotes: (String) -> Unit,
    onFillExample: () -> Unit,
    onUpload: () -> Unit,
    onDelete: (String) -> Unit,
    onSave: () -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeading("Housing expense organizer", "Record your actual notes or add a future due date for your own reminder.")
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                OutlinedButton(onClick = onFillExample, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                Text("DEMO only · review before saving. A saved sample is a private manual note, not proof of payment.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedTextField(title, onTitle, label = { Text("Record title") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                AmountField("Amount (KES)", amount, onAmount)
                ChoiceField("Category", category, listOf("rent", "utilities", "internet", "transport", "household", "debt", "expense", "other", "deposit", "moving", "furniture", "receipt"), onCategory)
                ChoiceField("How did you pay? (record only)", paymentMethod, listOf("not_recorded", "mpesa", "bank_transfer", "cash", "card", "other"), onMethod)
                OutlinedTextField(reference, onReference, label = { Text("Payment reference (optional; manual note)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                HomeScoutDateField(recordDate, onDate, "Record date · DD-MM-YYYY", Modifier.fillMaxWidth())
                HomeScoutDateField(dueDate, onDueDate, "Upcoming due date · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                Text("An upcoming date is a reminder only. It will not count as recorded spending or a confirmed payment.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedTextField(notes, onNotes, label = { Text("Notes (optional)") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                Text("Attach a private receipt", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                OutlinedButton(onClick = onUpload, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text("Upload or manage receipts") }
                val documents = data.receiptDocuments
                if (documents.length() == 0) Text("No private receipts uploaded yet.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                for (i in 0 until documents.length()) {
                    val document = documents.optJSONObject(i) ?: continue
                    val id = document.optString("id")
                    Row(Modifier.fillMaxWidth().clickable { onReceipt(if (receiptId == id) "" else id) }, verticalAlignment = Alignment.CenterVertically) {
                        RadioButton(selected = receiptId == id, onClick = { onReceipt(if (receiptId == id) "" else id) })
                        Text(document.optString("original_filename"), style = MaterialTheme.typography.bodySmall)
                    }
                }
                Text("Manual record only. A reference or receipt does not mean HomeScout processed or confirmed the payment.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = onSave, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(if (dueDate.isBlank()) "Save private record" else "Save expense reminder") }
            }
        }
        Text("Saved records · ${data.records.length()}", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        for (i in 0 until data.records.length()) {
            val row = data.records.optJSONObject(i) ?: continue
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(row.optString("title"), fontWeight = FontWeight.SemiBold)
                    Text("${row.optString("category").replaceFirstChar(Char::uppercase)} · ${ksh(row.optString("amount"))} · ${row.optString("evidence")}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    row.optString("due_date").takeUnless { it.isBlank() || it == "null" }?.let { Text("Reminder · due $it", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary) }
                    Text("${row.optString("payment_status").replace('_', ' ')} · ${row.optString("payment_method", "not_recorded").replace('_', ' ')}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurface)
                    row.optString("notes").takeUnless { it.isBlank() || it == "null" }?.let { Text(it, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    TextButton(onClick = { onDelete(row.optString("id")) }, modifier = Modifier.align(Alignment.End)) { Text("Remove") }
                }
            }
        }
    }
}

@Composable
private fun leaseContent(
    data: SmartRentSnapshot, title: String, rent: String, deposit: String, note: String,
    leaseStart: String, leaseEnd: String, clauseTitle: String, clauseSummary: String, clauseQuestion: String,
    editingId: String?, onTitle: (String) -> Unit, onRent: (String) -> Unit, onDeposit: (String) -> Unit,
    onNote: (String) -> Unit, onStart: (String) -> Unit, onEnd: (String) -> Unit,
    onClauseTitle: (String) -> Unit, onClauseSummary: (String) -> Unit, onClauseQuestion: (String) -> Unit,
    onFillExample: () -> Unit,
    onSave: () -> Unit, onEdit: (String, JSONObject) -> Unit, onCancel: () -> Unit,
    onDelete: (String) -> Unit
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeading("Lease & deposit guardian", "Organize your dates, figures, obligations, and questions. This is a private organizer, not legal advice.")
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                Text(if (editingId == null) "Add lease details" else "Edit lease details", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                if (editingId == null) {
                    OutlinedButton(onClick = onFillExample, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                    Text("DEMO figures and wording · edit them to match your real agreement before saving.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                OutlinedTextField(title, onTitle, label = { Text("Lease or deposit note") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                HomeScoutDateField(leaseStart, onStart, "Lease start · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                HomeScoutDateField(leaseEnd, onEnd, "Lease end · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                AmountField("Monthly rent (KES)", rent, onRent)
                AmountField("Deposit amount (KES)", deposit, onDeposit)
                Text("One obligation to clarify", style = MaterialTheme.typography.labelLarge)
                OutlinedTextField(clauseTitle, onClauseTitle, label = { Text("Obligation, e.g. water bill") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                OutlinedTextField(clauseSummary, onClauseSummary, label = { Text("My plain-language summary (optional)") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                OutlinedTextField(clauseQuestion, onClauseQuestion, label = { Text("Question I want to ask (optional)") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                OutlinedTextField(note, onNote, label = { Text("Additional private notes") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                Button(onClick = onSave, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text(if (editingId == null) "Save private lease note" else "Update private lease note") }
                if (editingId != null) TextButton(onClick = onCancel, modifier = Modifier.align(Alignment.End)) { Text("Cancel edit") }
            }
        }
        for (i in 0 until data.leases.length()) {
            val lease = data.leases.optJSONObject(i) ?: continue
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Column(Modifier.weight(1f)) {
                            Text(lease.optString("title"), fontWeight = FontWeight.SemiBold)
                            Text("Rent ${ksh(lease.optString("monthly_rent"))} · deposit ${ksh(lease.optString("deposit_amount"))}", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        IconButton(onClick = { onEdit(lease.optString("id"), lease) }) { Icon(Icons.Filled.Edit, "Edit lease note") }
                        IconButton(onClick = { onDelete(lease.optString("id")) }) { Icon(Icons.Filled.DeleteOutline, "Delete lease note") }
                    }
                    val start = lease.optString("lease_start").takeUnless { it.isBlank() || it == "null" }
                    val end = lease.optString("lease_end").takeUnless { it.isBlank() || it == "null" }
                    if (start != null || end != null) Text("Lease dates: ${start ?: "not set"} – ${end ?: "not set"}", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    val obligations = lease.optJSONArray("obligations")
                    if (obligations != null) for (j in 0 until obligations.length()) {
                        val obligation = obligations.optJSONObject(j) ?: continue
                        Text(obligation.optString("title"), style = MaterialTheme.typography.labelLarge)
                        obligation.optString("plain_language_note").takeUnless { it.isBlank() || it == "null" }?.let { Text("Your summary: $it", style = MaterialTheme.typography.bodySmall) }
                        obligation.optString("user_question").takeUnless { it.isBlank() || it == "null" }?.let { Text("Question to raise: $it", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                    }
                    lease.optString("private_notes").takeUnless { it.isBlank() || it == "null" }?.let { Text(it, style = MaterialTheme.typography.bodySmall) }
                }
            }
        }
        if (data.leases.length() == 0) EmptyStateCard("No lease notes yet", "Keep your own rent, deposit, and written questions together.", null, null)
    }
}

@Composable
private fun alertsContent(data: SmartRentSnapshot, token: String, api: SmartRentApi, runRequest: (() -> Unit, String) -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeading("Housing cost alerts", "Alerts are stored in HomeScout only; push and email delivery are not configured.")
        if (data.alerts.length() == 0) EmptyStateCard("You're all caught up", "Budget, goal, and compared-listing alerts will appear here.", null, null)
        for (i in 0 until data.alerts.length()) {
            val alert = data.alerts.optJSONObject(i) ?: continue
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(alert.optString("title"), fontWeight = FontWeight.SemiBold)
                    Text(alert.optString("message"), color = MaterialTheme.colorScheme.onSurfaceVariant)
                    if (!alert.optBoolean("is_read")) TextButton(onClick = { runRequest({ api.send("alerts/${alert.optString("id")}/read", token) }, "Alert marked as read.") }) { Text("Mark read") }
                    else Text("Read", style = MaterialTheme.typography.labelSmall, color = homeScoutSuccessTextColor())
                }
            }
        }
    }
}

@Composable
private fun aiContent(coach: JSONObject?, onAsk: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeading("HomeScout Assistant", "Ask about affordability, move-in costs or your budget. Account context is optional.")
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Icon(Icons.Filled.AutoAwesome, null, tint = MaterialTheme.colorScheme.primary, modifier = Modifier.size(30.dp))
                Text("Budget tips preview", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
                Text("Your figures stay in HomeScout unless you select the SmartRent summary for a message.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                Button(onClick = onAsk, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) { Text("Open HomeScout Assistant") }
                coach?.optJSONArray("messages")?.let { list -> for (i in 0 until list.length()) Text("• ${list.optString(i)}") }
                Surface(color = MaterialTheme.colorScheme.tertiaryContainer, shape = MaterialTheme.shapes.medium) {
                    Text("AI replies require a configured provider and your consent. Not legal, credit or lending decisions.", Modifier.padding(12.dp), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurface)
                }
            }
        }
    }
}

@Composable
internal fun SectionHeading(title: String, subtitle: String) {
    Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
        Text(title, style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.onSurface)
        Text(subtitle, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
    }
}

@Composable
private fun AmountField(label: String, value: String, onValue: (String) -> Unit) {
    OutlinedTextField(value, onValue, label = { Text(label) }, leadingIcon = { Text("KSh", style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant) }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth(), singleLine = true)
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun ChoiceField(label: String, value: String, options: List<String>, onValue: (String) -> Unit) {
    var expanded by remember { mutableStateOf(false) }
    ExposedDropdownMenuBox(expanded = expanded, onExpandedChange = { expanded = it }) {
        OutlinedTextField(value.replace('_', ' '), { }, label = { Text(label) }, readOnly = true, trailingIcon = { ExposedDropdownMenuDefaults.TrailingIcon(expanded) }, modifier = Modifier.menuAnchor().fillMaxWidth())
        ExposedDropdownMenu(expanded = expanded, onDismissRequest = { expanded = false }) {
            options.forEach { option -> DropdownMenuItem(text = { Text(option.replace('_', ' ')) }, onClick = { onValue(option); expanded = false }) }
        }
    }
}

@Composable
private fun EmptyStateCard(title: String, detail: String, actionLabel: String?, onAction: (() -> Unit)?) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.fillMaxWidth().padding(20.dp), horizontalAlignment = Alignment.CenterHorizontally, verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Icon(Icons.Filled.Info, null, tint = MaterialTheme.colorScheme.primary)
            Text(title, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Text(detail, style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            if (actionLabel != null && onAction != null) OutlinedButton(onClick = onAction, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text(actionLabel) }
        }
    }
}

@Composable
private fun ErrorCard(
    message: String,
    onRetry: () -> Unit,
    title: String = "Could not update SmartRent"
) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text(title, fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.error)
            Text(message, style = MaterialTheme.typography.bodySmall)
            TextButton(onClick = onRetry) { Text("Try again") }
        }
    }
}

internal fun ksh(value: String): String {
    val amount = value.toDoubleOrNull() ?: return "KSh 0"
    return "KSh " + java.text.NumberFormat.getNumberInstance(java.util.Locale("en", "KE")).format(amount)
}
