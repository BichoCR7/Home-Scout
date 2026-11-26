package ke.co.homescout.features.finance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Box
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.size
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.CompareArrows
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material.icons.automirrored.filled.ArrowForward
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.EventNote
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Savings
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Surface
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.semantics.contentDescription
import androidx.compose.ui.semantics.semantics
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.style.TextOverflow
import androidx.compose.ui.unit.dp
import androidx.compose.ui.unit.sp
import ke.co.homescout.ui.components.HomeScoutCard
import org.json.JSONArray
import org.json.JSONObject
import java.time.YearMonth
import java.time.ZoneId
import java.time.format.TextStyle
import java.util.Locale
import java.math.BigDecimal
import java.math.RoundingMode

private val homeScoutNavy = Color(0xFF10243A)
private val homeScoutGreen = Color(0xFF16A34A)

@Composable
internal fun FinanceOverviewContent(
    data: SmartRentSnapshot,
    preview: JSONObject?,
    previewIsExample: Boolean,
    assessmentUnavailable: Boolean,
    savingsUnavailable: Boolean,
    onBudget: () -> Unit,
    onPayments: () -> Unit,
    onSavings: () -> Unit,
    onCompare: () -> Unit,
    onRecords: () -> Unit
) {
    val configured = data.profile.optBoolean("is_configured")
    val assessment = preview ?: data.assessment
    val hasAssessment = preview != null ||
        (configured && !assessmentUnavailable && assessment.has("suggested_monthly_budget"))
    val cashflow = remember(data.dashboard, assessment) {
        if (preview == null) data.dashboard.optJSONObject("financial_overview")
        else previewCashflow(assessment)
    }
    val records = remember(data.records) { recentHousingRecords(data.records) }
    val chartPoints = remember(data.records) { housingCostHistory(data.records) }
    val goals = data.goals
    val activeGoals = (0 until goals.length())
        .mapNotNull(goals::optJSONObject)
        .filter { it.optString("status") != "archived" && it.optString("status") != "completed" }
        .take(3)

    Column(verticalArrangement = Arrangement.spacedBy(18.dp)) {
        if (hasAssessment && cashflow != null) {
            FinanceCashflowSummary(cashflow, preview != null)
        }

        MonthlyHousingHero(
            assessment = assessment,
            hasAssessment = hasAssessment,
            preview = preview != null,
            previewIsExample = previewIsExample,
            onBudget = onBudget
        )

        if (hasAssessment) {
            HousingSummaryCards(assessment)
            HousingIncomeAllocation(assessment)
        }

        if (configured && preview == null) {
            FinanceBudgetOverview(data.dashboard.optJSONObject("monthly_budget"), onBudget)
        }

        FinanceUpcomingExpenses(data.dashboard.optJSONArray("upcoming_expenses") ?: JSONArray(), onRecords)

        HousingCostHistory(points = chartPoints)

        HousingRecentRecords(records = records, onRecords = onRecords)

        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically) {
                    Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                        Text("Housing goals", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text("Your targets and progress", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    androidx.compose.material3.Icon(
                        Icons.Filled.Savings,
                        contentDescription = null,
                        tint = MaterialTheme.colorScheme.primary
                    )
                }
                when {
                    savingsUnavailable -> Text(
                        "Your savings goal could not be refreshed. Open Savings to retry.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    activeGoals.isNotEmpty() -> {
                        activeGoals.forEachIndexed { index, goal ->
                            if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))
                            val progressPercent = goal.optInt("progress_percent").coerceIn(0, 100)
                            val progress = progressPercent / 100f
                            Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                                Row(verticalAlignment = Alignment.CenterVertically) {
                                    Text(goal.optString("title", "Savings goal"), Modifier.weight(1f), fontWeight = FontWeight.Medium)
                                    Text("$progressPercent%", fontWeight = FontWeight.SemiBold, color = MaterialTheme.colorScheme.primary)
                                }
                                LinearProgressIndicator(progress = { progress }, modifier = Modifier.fillMaxWidth())
                                Text(
                                    "${ksh(goal.optString("current_amount"))} of ${ksh(goal.optString("target_amount"))} saved · ${ksh(goal.optString("remaining_amount"))} remaining",
                                    style = MaterialTheme.typography.bodySmall,
                                    color = MaterialTheme.colorScheme.onSurfaceVariant
                                )
                                val targetDate = goal.optString("target_date").takeIf { it.isNotBlank() && it != "null" }
                                val monthlyPlan = goal.optString("planned_monthly_contribution").takeIf { it.isNotBlank() && it != "null" }
                                val completionDate = goal.optString("estimated_completion_date").takeIf { it.isNotBlank() && it != "null" }
                                val objectiveDetails = listOfNotNull(
                                    targetDate?.let { "Target $it" },
                                    monthlyPlan?.let { "Plan ${ksh(it)}/month" },
                                    completionDate?.let { "At this pace: $it" }
                                )
                                if (objectiveDetails.isNotEmpty()) {
                                    Text(objectiveDetails.joinToString(" · "), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                }
                            }
                        }
                        Text("Progress is a private plan; HomeScout does not hold or move this money.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    }
                    else -> Text(
                        "No active goal yet. Create one for your deposit or moving costs.",
                        style = MaterialTheme.typography.bodyMedium,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                }
                TextButton(onClick = onSavings) {
                    Text(if (activeGoals.isEmpty()) "Create a savings goal" else "Manage housing goals")
                    Spacer(Modifier.width(4.dp))
                    androidx.compose.material3.Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(16.dp))
                }
            }
        }

        val insightItems = if (preview == null) {
            data.dashboard.optJSONArray("insights") ?: JSONArray()
        } else {
            assessment.optJSONArray("suggestions") ?: JSONArray()
        }
        if (hasAssessment && insightItems.length() > 0) {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                    Text("Housing finance insights", style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                    for (index in 0 until minOf(3, insightItems.length())) {
                        Row(horizontalArrangement = Arrangement.spacedBy(9.dp), verticalAlignment = Alignment.Top) {
                            Surface(shape = RoundedCornerShape(50), color = MaterialTheme.colorScheme.primaryContainer) {
                                Text("${index + 1}", Modifier.padding(horizontal = 8.dp, vertical = 3.dp), style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onPrimaryContainer, fontWeight = FontWeight.SemiBold)
                            }
                            Text(insightItems.optString(index), Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
        }

        Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
            Text("Quick access", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                FinanceQuickAction("Budget", Icons.Filled.AccountBalanceWallet, onBudget, Modifier.weight(1f))
                FinanceQuickAction("Payments", Icons.Filled.Payments, onPayments, Modifier.weight(1f))
            }
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(9.dp)) {
                FinanceQuickAction("Savings", Icons.Filled.Savings, onSavings, Modifier.weight(1f))
                FinanceQuickAction("Compare", Icons.AutoMirrored.Filled.CompareArrows, onCompare, Modifier.weight(1f))
            }
        }

        Text(
            "All figures are private planning estimates or notes you entered. A budget or manual record does not confirm that rent was paid.",
            style = MaterialTheme.typography.bodySmall,
            color = MaterialTheme.colorScheme.onSurfaceVariant
        )
    }
}

@Composable
private fun MonthlyHousingHero(
    assessment: JSONObject,
    hasAssessment: Boolean,
    preview: Boolean,
    previewIsExample: Boolean,
    onBudget: () -> Unit
) {
    val label = when {
        preview && previewIsExample -> "ILLUSTRATIVE PREVIEW · NOT SAVED"
        preview -> "UNSAVED BUDGET PREVIEW"
        hasAssessment -> "YOUR PRIVATE MONTHLY PLAN"
        else -> "YOUR HOUSING SNAPSHOT"
    }

    Card(
        modifier = Modifier.fillMaxWidth(),
        shape = RoundedCornerShape(24.dp),
        colors = CardDefaults.cardColors(containerColor = homeScoutNavy)
    ) {
        Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(14.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(4.dp)) {
                    Text(label, style = MaterialTheme.typography.labelMedium, color = Color(0xFFB9C8DA), fontWeight = FontWeight.SemiBold, letterSpacing = 0.8.sp)
                    Text("Monthly housing snapshot", style = MaterialTheme.typography.titleLarge, color = Color.White, fontWeight = FontWeight.SemiBold)
                }
                Surface(shape = RoundedCornerShape(15.dp), color = Color.White.copy(alpha = 0.10f)) {
                    androidx.compose.material3.Icon(
                        Icons.Filled.CalendarMonth,
                        contentDescription = "Monthly finance overview",
                        modifier = Modifier.padding(12.dp).size(22.dp),
                        tint = Color.White
                    )
                }
            }
            if (hasAssessment) {
                Text(ksh(assessment.optString("suggested_monthly_budget")), fontSize = 31.sp, lineHeight = 36.sp, fontWeight = FontWeight.Bold, color = Color.White)
                Text("Suggested rent budget · KES per month", style = MaterialTheme.typography.bodyMedium, color = Color(0xFFCFD9E6))
                HorizontalDivider(color = Color.White.copy(alpha = 0.20f))
                Row(horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                    HeroMetric(
                        title = "Total housing",
                        value = summaryAmount(assessment, "total_monthly_housing_cost"),
                        modifier = Modifier.weight(1f)
                    )
                    HeroMetric(
                        title = "Monthly headroom",
                        value = summaryAmount(assessment, "monthly_surplus_or_deficit"),
                        modifier = Modifier.weight(1f),
                        positive = assessment.optString("monthly_surplus_or_deficit").toDoubleOrNull()?.let { it >= 0.0 }
                    )
                }
                Text(
                    "Planning estimate only · not a credit score or rental approval",
                    style = MaterialTheme.typography.labelSmall,
                    color = Color(0xFFB9C8DA)
                )
            } else {
                Text("Enter your own numbers to see a clear monthly plan.", style = MaterialTheme.typography.bodyLarge, color = Color(0xFFECF2F8))
                Button(onClick = onBudget, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text("Set up my housing budget")
                    Spacer(Modifier.width(8.dp))
                    androidx.compose.material3.Icon(Icons.AutoMirrored.Filled.ArrowForward, contentDescription = null, modifier = Modifier.size(18.dp))
                }
            }
        }
    }
}

private fun previewCashflow(assessment: JSONObject): JSONObject? {
    val income = decimal(assessment.optString("conservative_monthly_income")) ?: return null
    val remaining = decimal(assessment.optString("monthly_surplus_or_deficit")) ?: return null
    val housing = decimal(assessment.optString("total_monthly_housing_cost")) ?: return null
    return JSONObject()
        .put("estimated_monthly_income", income.toPlainString())
        .put("estimated_monthly_expenses", (income - remaining).setScale(2, RoundingMode.HALF_UP).toPlainString())
        .put("estimated_monthly_housing_expenditure", housing.toPlainString())
        .put("estimated_monthly_remaining_balance", remaining.toPlainString())
        .put("affordability", assessment.optString("affordability"))
}

private fun decimal(value: String): BigDecimal? =
    value.toBigDecimalOrNull()?.takeIf { it.scale() <= 2 || it.stripTrailingZeros().scale() <= 2 }

@Composable
private fun FinanceCashflowSummary(data: JSONObject, isPreview: Boolean) {
    val remaining = data.optString("estimated_monthly_remaining_balance")
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text(if (isPreview) "Budget preview" else "Monthly cash flow", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text(if (isPreview) "Unsaved figures · KES" else "Saved planning figures · KES", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                androidx.compose.material3.Icon(Icons.Filled.AccountBalanceWallet, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            }
            Text(ksh(remaining), style = MaterialTheme.typography.headlineMedium, fontWeight = FontWeight.Bold, color = if ((remaining.toDoubleOrNull() ?: 0.0) < 0) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
            Text("Estimated money remaining after entered monthly costs", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant)
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                CashflowMetric("Income", data.optString("estimated_monthly_income"), Modifier.weight(1f))
                CashflowMetric("Expenses", data.optString("estimated_monthly_expenses"), Modifier.weight(1f))
                CashflowMetric("Housing", data.optString("estimated_monthly_housing_expenditure"), Modifier.weight(1f))
            }
            val affordability = data.optString("affordability").takeIf { it.isNotBlank() && it != "null" }
            if (affordability != null) {
                Text("RentScore guide · ${affordability.replace('_', ' ').replaceFirstChar { it.uppercase() }} · not a credit decision", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun CashflowMetric(title: String, amount: String, modifier: Modifier) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(3.dp)) {
        Text(title, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant, maxLines = 1)
        Text(ksh(amount), style = MaterialTheme.typography.labelLarge, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
    }
}

@Composable
private fun FinanceBudgetOverview(monthlyBudget: JSONObject?, onManage: () -> Unit) {
    val categories = monthlyBudget?.optJSONArray("categories") ?: JSONArray()
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text("Monthly budget", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text("Recorded spending against your limits", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = onManage) { Text("Edit") }
            }
            if (categories.length() == 0) {
                Text("Set category limits to track what you record each month.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedButton(onClick = onManage, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text("Set monthly limits") }
            } else {
                for (index in 0 until categories.length()) {
                    val category = categories.optJSONObject(index) ?: continue
                    val limit = category.optString("monthly_limit")
                    val spent = category.optString("recorded_this_month")
                    val limitValue = limit.toDoubleOrNull()?.takeIf { it > 0.0 } ?: 0.0
                    val spentValue = spent.toDoubleOrNull()?.coerceAtLeast(0.0) ?: 0.0
                    val overLimit = category.optBoolean("over_limit")
                    Column(verticalArrangement = Arrangement.spacedBy(6.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Text(category.optString("category").replace('_', ' ').replaceFirstChar { it.uppercase() }, Modifier.weight(1f), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                            Text("${ksh(spent)} / ${ksh(limit)}", style = MaterialTheme.typography.labelMedium, color = if (overLimit) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        LinearProgressIndicator(
                            progress = { if (limitValue > 0) (spentValue / limitValue).toFloat().coerceIn(0f, 1f) else if (spentValue > 0) 1f else 0f },
                            modifier = Modifier.fillMaxWidth().height(7.dp).clip(RoundedCornerShape(50)),
                            color = if (overLimit) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                            trackColor = MaterialTheme.colorScheme.surfaceVariant
                        )
                    }
                }
                Text("Recorded entries only · upcoming reminders and receipt copies are excluded.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun FinanceUpcomingExpenses(expenses: JSONArray, onManage: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                androidx.compose.material3.Icon(Icons.Filled.EventNote, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                Spacer(Modifier.width(9.dp))
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                    Text("Upcoming expenses", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text("Dates and amounts you entered", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = onManage) { Text("Manage") }
            }
            if (expenses.length() == 0) {
                Text("No upcoming expense dates saved. Add a due date in Records to see it here.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                for (index in 0 until minOf(expenses.length(), 3)) {
                    val item = expenses.optJSONObject(index) ?: continue
                    if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))
                    Row(Modifier.padding(vertical = 4.dp), verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(10.dp)) {
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(2.dp)) {
                            Text(item.optString("title"), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text("${item.optString("category").replace('_', ' ').replaceFirstChar { it.uppercase() }} · Due ${item.optString("due_date")}", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                        Text(ksh(item.optString("amount")), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                    }
                }
                Text("These are reminders only. HomeScout has not paid or confirmed them.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (expenses.length() == 0) {
                OutlinedButton(onClick = onManage, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text("Add an upcoming expense") }
            }
        }
    }
}

@Composable
private fun HeroMetric(
    title: String,
    value: String,
    modifier: Modifier = Modifier,
    positive: Boolean? = null
) {
    Column(modifier, verticalArrangement = Arrangement.spacedBy(4.dp)) {
        Text(title, style = MaterialTheme.typography.labelMedium, color = Color(0xFFB9C8DA))
        Text(
            value,
            style = MaterialTheme.typography.titleMedium,
            fontWeight = FontWeight.SemiBold,
            color = when (positive) {
                true -> Color(0xFF86E6A4)
                false -> Color(0xFFFFB4AB)
                null -> Color.White
            },
            maxLines = 1,
            overflow = TextOverflow.Ellipsis
        )
    }
}

@Composable
private fun HousingSummaryCards(assessment: JSONObject) {
    Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
        Text("Monthly breakdown", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
            SummaryTile("Rent", summaryAmount(assessment, "target_monthly_rent"), Modifier.weight(1f), MaterialTheme.colorScheme.primary)
            SummaryTile("Other housing", summaryAmount(assessment, "housing_costs_excluding_rent"), Modifier.weight(1f), MaterialTheme.colorScheme.secondary)
        }
        Row(horizontalArrangement = Arrangement.spacedBy(9.dp)) {
            SummaryTile("Living costs", summaryAmount(assessment, "non_housing_committed_costs"), Modifier.weight(1f), MaterialTheme.colorScheme.tertiary)
            SummaryTile("Income", summaryAmount(assessment, "recurring_monthly_income"), Modifier.weight(1f), MaterialTheme.colorScheme.primary)
        }
    }
}

@Composable
private fun SummaryTile(title: String, value: String, modifier: Modifier, accent: Color) {
    Surface(
        modifier = modifier,
        shape = RoundedCornerShape(18.dp),
        color = MaterialTheme.colorScheme.surfaceVariant.copy(alpha = 0.55f)
    ) {
        Column(Modifier.padding(horizontal = 14.dp, vertical = 15.dp), verticalArrangement = Arrangement.spacedBy(5.dp)) {
            Surface(Modifier.width(28.dp).height(3.dp), color = accent, shape = RoundedCornerShape(50)) {}
            Text(title, style = MaterialTheme.typography.labelMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(value, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold, maxLines = 1, overflow = TextOverflow.Ellipsis)
        }
    }
}

@Composable
private fun HousingIncomeAllocation(assessment: JSONObject) {
    val rentShare = assessment.optString("rent_to_income_percent").toDoubleOrNull()
    val housingShare = assessment.optString("housing_to_income_percent").toDoubleOrNull()
    val ratio = (rentShare ?: housingShare)?.coerceAtLeast(0.0)

    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(11.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text("Income allocation", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text("Rent compared with monthly income", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                androidx.compose.material3.Icon(Icons.Filled.AccountBalanceWallet, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
            }
            if (ratio != null) {
                LinearProgressIndicator(
                    progress = { (ratio / 100.0).toFloat().coerceIn(0f, 1f) },
                    modifier = Modifier.fillMaxWidth().height(10.dp).clip(RoundedCornerShape(50)),
                    color = MaterialTheme.colorScheme.primary,
                    trackColor = MaterialTheme.colorScheme.surfaceVariant
                )
                Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                    Text("Rent share", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Text("${String.format(Locale.US, "%.1f", ratio)}%", fontWeight = FontWeight.SemiBold)
                }
                if (housingShare != null && housingShare != rentShare) {
                    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                        Text("All housing costs", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Text("${String.format(Locale.US, "%.1f", housingShare)}%", fontWeight = FontWeight.Medium)
                    }
                }
            } else {
                Text("Add income and rent figures to view your allocation.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

@Composable
private fun HousingCostHistory(points: List<HousingCostPoint>) {
    val primary = MaterialTheme.colorScheme.primary
    val track = MaterialTheme.colorScheme.outlineVariant
    val maxAmount = points.maxOfOrNull { it.amount }?.takeIf { it > 0.0 } ?: 1.0
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Column(verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text("Housing costs trend", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                Text("Your recorded housing costs by month · KES", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            if (points.none { it.amount > 0.0 }) {
                Text("Your chart will fill as you add rent, deposit, utility, or moving records.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
            } else {
                val description = points.joinToString(separator = "; ") { "${it.label}: ${ksh(it.amount.toString())}" }
                Row(
                    Modifier.fillMaxWidth().semantics {
                        contentDescription = "Six-month recorded housing cost chart. $description"
                    },
                    horizontalArrangement = Arrangement.SpaceBetween,
                    verticalAlignment = Alignment.Bottom
                ) {
                    points.forEach { point ->
                        Column(
                            modifier = Modifier.weight(1f),
                            horizontalAlignment = Alignment.CenterHorizontally,
                            verticalArrangement = Arrangement.spacedBy(5.dp)
                        ) {
                            Text(
                                compactKsh(point.amount),
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant,
                                maxLines = 1
                            )
                            Box(Modifier.width(30.dp).height(86.dp), contentAlignment = Alignment.BottomCenter) {
                                val barHeight = if (point.amount > 0.0) (point.amount / maxAmount * 76.0).toFloat().coerceAtLeast(5f) else 3f
                                Surface(
                                    Modifier.width(21.dp).height(barHeight.dp),
                                    shape = RoundedCornerShape(topStart = 7.dp, topEnd = 7.dp),
                                    color = if (point.amount > 0.0) primary else track.copy(alpha = 0.45f)
                                ) {}
                            }
                            Text(point.label, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
                Text("Zero means no record was added for that month. Manual entries are not payment confirmations.", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        }
    }
}

private fun compactKsh(amount: Double): String = when {
    amount >= 1_000_000 -> "${String.format(Locale.US, "%.1f", amount / 1_000_000)}m"
    amount >= 10_000 -> "${(amount / 1_000).toInt()}k"
    amount >= 1_000 -> "${String.format(Locale.US, "%.1f", amount / 1_000)}k"
    else -> amount.toInt().toString()
}

@Composable
private fun HousingRecentRecords(records: List<JSONObject>, onRecords: () -> Unit) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                    Text("Recent housing records", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    Text("Private notes saved to your account", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                TextButton(onClick = onRecords) { Text("View all") }
            }
            if (records.isEmpty()) {
                Text("No housing costs recorded yet. Add a rent, deposit, utility, or moving note in Records.", style = MaterialTheme.typography.bodyMedium, color = MaterialTheme.colorScheme.onSurfaceVariant)
                OutlinedButton(onClick = onRecords, modifier = Modifier.fillMaxWidth().heightIn(min = 46.dp)) { Text("Add a housing record") }
            } else {
                records.forEachIndexed { index, record ->
                    if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))
                    Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(12.dp)) {
                        Surface(shape = RoundedCornerShape(13.dp), color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.65f)) {
                            androidx.compose.material3.Icon(Icons.Filled.AccountBalanceWallet, contentDescription = null, modifier = Modifier.padding(10.dp).size(19.dp), tint = MaterialTheme.colorScheme.primary)
                        }
                        Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                            Text(record.optString("title", "Housing cost"), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium, maxLines = 1, overflow = TextOverflow.Ellipsis)
                            Text(
                                "${record.optString("category").replace('_', ' ').replaceFirstChar { it.uppercase() }} · ${record.optString("record_date").take(10)}",
                                style = MaterialTheme.typography.labelSmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                        Text(ksh(record.optString("amount")), style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.SemiBold)
                    }
                }
            }
        }
    }
}

@Composable
internal fun FinancePaymentsContent(onOpenPaymentHistory: () -> Unit) {
    Column(verticalArrangement = Arrangement.spacedBy(16.dp)) {
        Card(
            modifier = Modifier.fillMaxWidth(),
            shape = RoundedCornerShape(24.dp),
            colors = CardDefaults.cardColors(containerColor = homeScoutNavy)
        ) {
            Column(Modifier.padding(20.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Payments", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.SemiBold, color = Color.White)
                Text("Payment status in one clear place", style = MaterialTheme.typography.bodyLarge, color = Color(0xFFCFD9E6))
                Text("HomeScout only records provider-confirmed payments for eligible service bookings. It does not collect rent or hold money.", style = MaterialTheme.typography.bodySmall, color = Color(0xFFB9C8DA))
            }
        }

        Text("Payment methods", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
        PaymentMethodInfo(
            title = "M-Pesa",
            detail = "Daraja status is available for accepted, eligible service bookings.",
            status = "Service bookings",
            icon = Icons.Filled.Payments
        )
        PaymentMethodInfo(
            title = "Bank transfer",
            detail = "You can keep a private manual note in Records. HomeScout does not initiate or verify a transfer.",
            status = "Manual record",
            icon = Icons.Filled.AccountBalanceWallet
        )
        PaymentMethodInfo(
            title = "Cash or card",
            detail = "Record these as private notes only. They do not create a payment or receipt.",
            status = "Manual record",
            icon = Icons.Filled.AccountBalanceWallet
        )

        Button(onClick = onOpenPaymentHistory, modifier = Modifier.fillMaxWidth().heightIn(min = 52.dp)) {
            androidx.compose.material3.Icon(Icons.Filled.Payments, contentDescription = null)
            Spacer(Modifier.width(9.dp))
            Text("View payment history and M-Pesa status")
        }
    }
}

@Composable
private fun PaymentMethodInfo(
    title: String,
    detail: String,
    status: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector
) {
    HomeScoutCard(Modifier.fillMaxWidth()) {
        Row(Modifier.padding(16.dp), horizontalArrangement = Arrangement.spacedBy(12.dp), verticalAlignment = Alignment.CenterVertically) {
            Surface(shape = RoundedCornerShape(14.dp), color = MaterialTheme.colorScheme.primaryContainer.copy(alpha = 0.65f)) {
                androidx.compose.material3.Icon(icon, contentDescription = null, modifier = Modifier.padding(11.dp).size(21.dp), tint = MaterialTheme.colorScheme.primary)
            }
            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                Text(title, style = MaterialTheme.typography.titleSmall, fontWeight = FontWeight.SemiBold)
                Text(detail, style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
            Text(status, style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.primary, fontWeight = FontWeight.SemiBold)
        }
    }
}

@Composable
private fun FinanceQuickAction(
    label: String,
    icon: androidx.compose.ui.graphics.vector.ImageVector,
    onClick: () -> Unit,
    modifier: Modifier = Modifier
) {
    OutlinedButton(onClick = onClick, modifier = modifier.heightIn(min = 52.dp)) {
        androidx.compose.material3.Icon(icon, contentDescription = null, modifier = Modifier.padding(end = 6.dp))
        Text(label, style = MaterialTheme.typography.labelLarge)
    }
}

private data class HousingCostPoint(val label: String, val amount: Double)

private fun hasUpcomingDate(record: JSONObject): Boolean =
    record.optString("due_date").let { it.isNotBlank() && it != "null" }

private fun recentHousingRecords(records: JSONArray): List<JSONObject> =
    (0 until records.length())
        .mapNotNull(records::optJSONObject)
        .filter { it.optString("category") != "receipt" && !hasUpcomingDate(it) }
        .sortedByDescending { it.optString("record_date") }
        .take(3)

private fun housingCostHistory(records: JSONArray): List<HousingCostPoint> {
    val now = YearMonth.now(ZoneId.of("Africa/Nairobi"))
    val totals = mutableMapOf<YearMonth, Double>()
    (0 until records.length()).mapNotNull(records::optJSONObject)
        .filter { it.optString("category") != "receipt" && !hasUpcomingDate(it) }
        .forEach { record ->
            val month = runCatching { YearMonth.parse(record.optString("record_date").take(7)) }.getOrNull()
            val amount = record.optString("amount").toDoubleOrNull()?.takeIf { it >= 0.0 }
            if (month != null && amount != null && !month.isAfter(now)) {
                totals[month] = (totals[month] ?: 0.0) + amount
            }
        }
    return (5 downTo 0).map { offset ->
        val month = now.minusMonths(offset.toLong())
        HousingCostPoint(month.month.getDisplayName(TextStyle.SHORT, Locale.ENGLISH), totals[month] ?: 0.0)
    }
}

private fun summaryAmount(json: JSONObject, key: String): String =
    if (json.has(key) && !json.isNull(key)) ksh(json.optString(key)) else "Not set"
