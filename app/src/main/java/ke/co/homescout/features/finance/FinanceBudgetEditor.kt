package ke.co.homescout.features.finance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.layout.width
import androidx.compose.foundation.shape.RoundedCornerShape
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.AccountBalanceWallet
import androidx.compose.material3.Button
import androidx.compose.material3.Card
import androidx.compose.material3.CardDefaults
import androidx.compose.material3.HorizontalDivider
import androidx.compose.material3.Icon
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
import androidx.compose.runtime.Composable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.draw.clip
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import ke.co.homescout.ui.components.HomeScoutCard
import org.json.JSONArray
import org.json.JSONObject

internal val financeBudgetCategories = listOf(
    "rent" to "Rent",
    "utilities" to "Utilities",
    "internet" to "Internet",
    "transport" to "Transport",
    "household" to "Household",
    "debt" to "Debt repayments",
    "expense" to "General expenses",
    "other" to "Other"
)

@Composable
internal fun FinanceBudgetEditor(
    values: Map<String, String>,
    dashboardBudget: JSONObject?,
    working: Boolean,
    onValueChange: (String, String) -> Unit,
    onFillExample: () -> Unit,
    onSave: () -> Unit
) {
    val actual = dashboardBudget?.optJSONArray("categories") ?: JSONArray()
    val actualByCategory = (0 until actual.length()).mapNotNull { index ->
        actual.optJSONObject(index)?.let { it.optString("category") to it }
    }.toMap()

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        SectionHeading(
            "Monthly category limits",
            "Set your own KES limits. Recorded entries are compared with each matching category; reminders and receipts are excluded."
        )
        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(13.dp)) {
                TextButton(onClick = onFillExample, enabled = !working, modifier = Modifier.fillMaxWidth()) {
                    Text("Fill new random sample · KES")
                }
                Text("Fresh fictional amounts fill the fields each time. Review or edit them, then choose Save monthly limits to store them.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                financeBudgetCategories.forEachIndexed { index, (category, label) ->
                    if (index > 0) HorizontalDivider(color = MaterialTheme.colorScheme.outlineVariant.copy(alpha = 0.55f))
                    val summary = actualByCategory[category]
                    Column(verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Icon(Icons.Filled.AccountBalanceWallet, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                            Spacer(Modifier.width(8.dp))
                            Text(label, Modifier.weight(1f), fontWeight = FontWeight.Medium)
                            if (summary != null) {
                                Text(
                                    "${ksh(summary.optString("recorded_this_month"))} recorded",
                                    style = MaterialTheme.typography.labelSmall,
                                    color = if (summary.optBoolean("over_limit")) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
                                )
                            }
                        }
                        OutlinedTextField(
                            value = values[category].orEmpty(),
                            onValueChange = { onValueChange(category, it.filter(Char::isDigit).take(12)) },
                            label = { Text("Monthly limit · KES") },
                            modifier = Modifier.fillMaxWidth(),
                            singleLine = true,
                            keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Number),
                            shape = RoundedCornerShape(14.dp)
                        )
                        if (summary != null) {
                            val limit = summary.optString("monthly_limit").toDoubleOrNull() ?: 0.0
                            val spent = summary.optString("recorded_this_month").toDoubleOrNull()?.coerceAtLeast(0.0) ?: 0.0
                            val progress = if (limit > 0.0) (spent / limit).toFloat().coerceIn(0f, 1f) else if (spent > 0) 1f else 0f
                            LinearProgressIndicator(
                                progress = { progress },
                                modifier = Modifier.fillMaxWidth().heightIn(min = 5.dp).clip(RoundedCornerShape(50)),
                                color = if (summary.optBoolean("over_limit")) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary,
                                trackColor = MaterialTheme.colorScheme.surfaceVariant
                            )
                            Text(
                                if (summary.optBoolean("over_limit")) "Over limit by ${ksh(kshNumber(summary.optString("remaining")))}" else "${ksh(summary.optString("remaining"))} remaining this month",
                                style = MaterialTheme.typography.labelSmall,
                                color = if (summary.optBoolean("over_limit")) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.onSurfaceVariant
                            )
                        }
                    }
                }
                Text(
                    "Only amounts you explicitly record appear as spending. This screen does not import bank or M-Pesa activity.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
                Button(onClick = onSave, enabled = !working, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Text("Save monthly limits")
                }
            }
        }
    }
}

private fun kshNumber(value: String): String = value.toDoubleOrNull()?.let { kotlin.math.abs(it).toString() } ?: "0"
