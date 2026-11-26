package ke.co.homescout.features.finance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxSize
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.lazy.LazyColumn
import androidx.compose.foundation.lazy.items
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.automirrored.filled.ArrowBack
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.LaunchedEffect
import androidx.compose.runtime.getValue
import androidx.compose.runtime.mutableIntStateOf
import androidx.compose.runtime.mutableStateOf
import androidx.compose.runtime.remember
import androidx.compose.runtime.rememberCoroutineScope
import androidx.compose.runtime.setValue
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.PaymentsApi
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.components.homeScoutSuccessTextColor
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.text.NumberFormat
import java.util.Locale

@Composable
fun PaymentsScreen(
    accessToken: String?,
    onBack: () -> Unit,
    onSignIn: () -> Unit
) {
    val api = remember { PaymentsApi() }
    val scope = rememberCoroutineScope()
    var configuration by remember { mutableStateOf<JSONObject?>(null) }
    var history by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var refreshingId by remember { mutableStateOf<String?>(null) }
    var error by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }

    LaunchedEffect(accessToken, reload, ApiConfiguration.isConfigured) {
        loading = true
        error = null
        if (!ApiConfiguration.isConfigured) {
            error = "Connect HOMESCOUT_API_BASE_URL to load payment records."
            loading = false
        } else {
            val result = withContext(Dispatchers.IO) {
                runCatching {
                    api.configuration() to (accessToken?.let(api::history) ?: emptyList())
                }
            }
            result.onSuccess { (config, payments) ->
                configuration = config
                history = payments
            }.onFailure { error = it.message ?: "Payment information could not be loaded." }
            loading = false
        }
    }

    LazyColumn(
        modifier = Modifier.fillMaxSize(),
        contentPadding = androidx.compose.foundation.layout.PaddingValues(
            start = 18.dp, end = 18.dp, top = 10.dp, bottom = 30.dp
        ),
        verticalArrangement = Arrangement.spacedBy(14.dp)
    ) {
        item {
            Row(verticalAlignment = Alignment.CenterVertically) {
                IconButton(onClick = onBack) {
                    Icon(Icons.AutoMirrored.Filled.ArrowBack, contentDescription = "Back to finance")
                }
                Column(Modifier.weight(1f)) {
                    Text("Rent & payments", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
                    Text("Private rent tracking and service payment history", color = MaterialTheme.colorScheme.onSurfaceVariant)
                }
                IconButton(onClick = { reload++ }, enabled = !loading) {
                    Icon(Icons.Filled.Refresh, contentDescription = "Refresh payment status")
                }
            }
        }
        item {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Row(
                    Modifier.padding(16.dp),
                    horizontalArrangement = Arrangement.spacedBy(12.dp),
                    verticalAlignment = Alignment.CenterVertically
                ) {
                    Icon(Icons.Filled.Payments, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Column(verticalArrangement = Arrangement.spacedBy(4.dp)) {
                        val mode = configuration?.optString("mode", "disabled") ?: "unavailable"
                        Text("M-Pesa · ${mode.replaceFirstChar(Char::uppercase)}", fontWeight = FontWeight.SemiBold)
                        Text(
                            configuration?.optString("message")
                                ?: "Payment configuration status is not available.",
                            style = MaterialTheme.typography.bodySmall,
                            color = MaterialTheme.colorScheme.onSurfaceVariant
                        )
                    }
                }
            }
        }
        item { RentPaymentsSection(accessToken) }
        item {
            configuration?.optJSONArray("methods")?.let { methods ->
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        Text("Payment method availability", fontWeight = FontWeight.SemiBold)
                        for (index in 0 until methods.length()) {
                            val method = methods.optJSONObject(index) ?: continue
                            val state = when (method.optString("status")) {
                                "service_only" -> "Service bookings only"
                                "manual_record_only" -> "External record only"
                                else -> "Not configured"
                            }
                            Column(verticalArrangement = Arrangement.spacedBy(2.dp)) {
                                Text("${method.optString("label")} · $state", style = MaterialTheme.typography.bodyMedium, fontWeight = FontWeight.Medium)
                                Text(method.optString("message"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                        }
                    }
                }
            }
        }
        if (accessToken == null) {
            item {
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("Sign in to see payment history", fontWeight = FontWeight.SemiBold)
                        Text("Only payment records for your account are shown.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Button(onClick = onSignIn) { Text("Sign in") }
                    }
                }
            }
        } else {
            item { Text("Service booking payment history", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold) }
            if (loading) item { LinearProgressIndicator(Modifier.fillMaxWidth()) }
            error?.let { message ->
                item {
                    HomeScoutCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                            Text("Payments could not load", fontWeight = FontWeight.SemiBold)
                            Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            OutlinedButton(onClick = { reload++ }) { Text("Try again") }
                        }
                    }
                }
            }
            if (!loading && error == null && history.isEmpty()) {
                item {
                    HomeScoutCard(Modifier.fillMaxWidth()) {
                        Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                            Text("No payment requests", fontWeight = FontWeight.SemiBold)
                            Text("Requests for accepted fixed-price service bookings will appear here.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                        }
                    }
                }
            }
            items(history, key = { it.optString("id") }) { record ->
                val status = record.optString("status", "pending")
                val transactionId = record.optString("id")
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        Row(verticalAlignment = Alignment.CenterVertically) {
                            Column(Modifier.weight(1f)) {
                                Text("${kes(record.optString("amount_kes"))} · Service booking", fontWeight = FontWeight.SemiBold)
                                Text(record.optString("phone_masked"), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                            }
                            Text(status.replace('_', ' ').replaceFirstChar(Char::uppercase), color = statusColor(status), fontWeight = FontWeight.SemiBold)
                        }
                        Text("Reference ${record.optString("reference")}", style = MaterialTheme.typography.bodySmall)
                        if (status == "successful") {
                            Text(
                                record.optString("receipt_number").takeIf(String::isNotBlank)?.let { "M-Pesa receipt $it" }
                                    ?: "Confirmed by Daraja; receipt details are not available yet.",
                                style = MaterialTheme.typography.bodySmall,
                                color = homeScoutSuccessTextColor()
                            )
                        }
                        if (status == "pending") {
                            Text(
                                "Still waiting for Daraja confirmation. Do not treat this request as paid yet.",
                                style = MaterialTheme.typography.bodySmall,
                                color = MaterialTheme.colorScheme.onSurfaceVariant
                            )
                            OutlinedButton(
                                enabled = refreshingId != transactionId && record.optBoolean("can_reconcile"),
                                onClick = {
                                    scope.launch {
                                        refreshingId = transactionId
                                        val outcome = withContext(Dispatchers.IO) {
                                            runCatching { api.reconcile(accessToken, transactionId) }
                                        }
                                        outcome.onSuccess { updated ->
                                            history = history.map { if (it.optString("id") == transactionId) updated else it }
                                        }.onFailure { error = it.message ?: "Status could not be checked." }
                                        refreshingId = null
                                    }
                                }
                            ) {
                                if (refreshingId == transactionId) CircularProgressIndicator(Modifier.height(16.dp), strokeWidth = 2.dp)
                                else Text("Check status")
                            }
                        }
                    }
                }
            }
        }
        item { Spacer(Modifier.height(4.dp)) }
    }
}

private fun kes(value: String): String {
    val amount = value.toDoubleOrNull() ?: 0.0
    val formatted = NumberFormat.getNumberInstance(Locale.forLanguageTag("en-KE")).format(amount)
    return "KSh $formatted"
}

@Composable
private fun statusColor(status: String) = when (status) {
    "successful" -> homeScoutSuccessTextColor()
    "failed", "cancelled", "expired", "reversed" -> MaterialTheme.colorScheme.error
    else -> MaterialTheme.colorScheme.onSurface
}
