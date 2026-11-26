package ke.co.homescout.features.finance

import androidx.compose.foundation.layout.Arrangement
import androidx.compose.foundation.layout.Column
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Spacer
import androidx.compose.foundation.layout.fillMaxWidth
import androidx.compose.foundation.layout.height
import androidx.compose.foundation.layout.heightIn
import androidx.compose.foundation.layout.padding
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.Add
import androidx.compose.material.icons.filled.Lock
import androidx.compose.material.icons.filled.Payments
import androidx.compose.material.icons.filled.Refresh
import androidx.compose.material3.Button
import androidx.compose.material3.CircularProgressIndicator
import androidx.compose.material3.DropdownMenu
import androidx.compose.material3.DropdownMenuItem
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.LinearProgressIndicator
import androidx.compose.material3.MaterialTheme
import androidx.compose.material3.OutlinedButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.material3.TextButton
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
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.ApiConfiguration
import ke.co.homescout.data.remote.PaymentsApi
import ke.co.homescout.ui.components.HomeScoutCard
import ke.co.homescout.ui.components.HomeScoutDateField
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.time.LocalDate
import java.util.UUID

private val rentPaymentMethods = listOf(
    "mpesa" to "M-Pesa",
    "bank_transfer" to "Bank transfer",
    "cash" to "Cash",
    "card" to "Card",
    "paypal" to "PayPal",
    "other" to "Other"
)

@Composable
internal fun RentPaymentsSection(accessToken: String?) {
    val api = remember { PaymentsApi() }
    val scope = rememberCoroutineScope()
    var items by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var loading by remember { mutableStateOf(false) }
    var saving by remember { mutableStateOf(false) }
    var loadError by remember { mutableStateOf<String?>(null) }
    var actionMessage by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }
    var showCreate by remember { mutableStateOf(false) }
    var title by remember { mutableStateOf("") }
    var amount by remember { mutableStateOf("") }
    var dueDate by remember { mutableStateOf(LocalDate.now().toString()) }
    var propertyReference by remember { mutableStateOf("") }
    var reportFor by remember { mutableStateOf<String?>(null) }
    var reportAmount by remember { mutableStateOf("") }
    var reportDate by remember { mutableStateOf(LocalDate.now().toString()) }
    var reportReference by remember { mutableStateOf("") }
    var reportNotes by remember { mutableStateOf("") }
    var reportMethod by remember { mutableStateOf("mpesa") }
    var methodMenu by remember { mutableStateOf(false) }

    LaunchedEffect(accessToken, reload, ApiConfiguration.isConfigured) {
        val token = accessToken
        if (token == null || !ApiConfiguration.isConfigured) {
            items = emptyList()
            loadError = if (token == null) null else "Connect the HomeScout API to load your private rent records."
            return@LaunchedEffect
        }
        loading = true
        loadError = null
        runCatching { withContext(Dispatchers.IO) { api.rentObligations(token) } }
            .onSuccess { items = it }
            .onFailure { loadError = it.message ?: "Rent records could not be loaded." }
        loading = false
    }

    fun perform(action: suspend () -> JSONObject, success: String) {
        if (saving) return
        saving = true
        actionMessage = null
        scope.launch {
            runCatching { withContext(Dispatchers.IO) { action() } }
                .onSuccess { updated ->
                    val id = updated.optString("id")
                    items = if (items.any { it.optString("id") == id }) {
                        items.map { if (it.optString("id") == id) updated else it }
                    } else listOf(updated) + items
                    actionMessage = success
                    showCreate = false
                    reportFor = null
                    title = ""; amount = ""; propertyReference = ""
                    reportAmount = ""; reportReference = ""; reportNotes = ""
                }
                .onFailure { actionMessage = it.message ?: "HomeScout could not save this change." }
            saving = false
        }
    }

    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Row(verticalAlignment = Alignment.CenterVertically) {
            Column(Modifier.weight(1f)) {
                Text("Rent & payment tracker", style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.Bold)
                Text("Private reminders and records for payments you make outside HomeScout.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
            }
            IconButton(onClick = { reload++ }, enabled = !loading && accessToken != null) {
                Icon(Icons.Filled.Refresh, contentDescription = "Refresh rent records")
            }
        }

        HomeScoutCard(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                    Icon(Icons.Filled.Lock, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                    Text("Your rent records are private", fontWeight = FontWeight.SemiBold)
                }
                Text(
                    "HomeScout does not collect rent or verify landlord receipts. Any amount you record is marked as reported by you.",
                    style = MaterialTheme.typography.bodySmall,
                    color = MaterialTheme.colorScheme.onSurfaceVariant
                )
            }
        }

        if (accessToken == null) {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Text("Sign in to manage private rent reminders and reports.", Modifier.padding(16.dp), color = MaterialTheme.colorScheme.onSurfaceVariant)
            }
        } else {
            if (loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            loadError?.let { message ->
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text("Rent records could not load", color = MaterialTheme.colorScheme.error, fontWeight = FontWeight.SemiBold)
                        Text(message, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        OutlinedButton(onClick = { reload++ }) { Text("Try again") }
                    }
                }
            }
            if (!showCreate) {
                Button(onClick = { showCreate = true }, modifier = Modifier.fillMaxWidth().heightIn(min = 48.dp)) {
                    Icon(Icons.Filled.Add, contentDescription = null)
                    Text("  Add a rent reminder")
                }
            }
            if (showCreate) {
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp).verticalScroll(rememberScrollState()), verticalArrangement = Arrangement.spacedBy(10.dp)) {
                        Text("New rent reminder", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                        OutlinedButton(onClick = {
                            val amountSample = kotlin.random.Random.nextInt(16, 46) * 1_000
                            title = "DEMO · ${listOf("Monthly rent", "Studio rent", "Room rent", "Deposit reminder").random()}"
                            amount = amountSample.toString()
                            dueDate = LocalDate.now(java.time.ZoneId.of("Africa/Nairobi")).plusDays(kotlin.random.Random.nextLong(3, 31)).toString()
                            propertyReference = "DEMO · ${listOf("Kilimani", "Ruaka", "Ruiru", "Nyali").random()} example"
                        }, enabled = !saving, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                        Text("DEMO only · review before saving this personal reminder.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        OutlinedTextField(title, { title = it }, label = { Text("What is this for?") }, placeholder = { Text("e.g. December rent") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                        OutlinedTextField(amount, { amount = it }, label = { Text("Amount (KES)") }, leadingIcon = { Text("KSh") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth(), singleLine = true)
                        HomeScoutDateField(dueDate, { dueDate = it }, "Due date · DD-MM-YYYY", Modifier.fillMaxWidth())
                        OutlinedTextField(propertyReference, { propertyReference = it }, label = { Text("Property or landlord note (optional)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                        Text("This is your personal reminder, not a verified lease or landlord claim.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                        Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                            OutlinedButton(onClick = { showCreate = false }, enabled = !saving, modifier = Modifier.weight(1f)) { Text("Cancel") }
                            Button(
                                onClick = {
                                    val parsed = amount.trim().replace(",", "").toBigDecimalOrNull()
                                    if (title.isBlank() || parsed == null || parsed <= java.math.BigDecimal.ZERO || runCatching { LocalDate.parse(dueDate) }.isFailure) {
                                        actionMessage = "Enter a title, a positive KES amount, and a valid due date."
                                    } else {
                                        perform({ api.createRentObligation(accessToken, JSONObject().put("title", title.trim()).put("amount_kes", parsed.toPlainString()).put("due_date", dueDate.trim()).put("property_reference", propertyReference.trim())) }, "Rent reminder saved to your account.")
                                    }
                                }, enabled = !saving, modifier = Modifier.weight(1f)
                            ) { if (saving) CircularProgressIndicator(Modifier.height(18.dp), strokeWidth = 2.dp) else Text("Save reminder") }
                        }
                    }
                }
            }

            actionMessage?.let { Text(it, color = if (it.contains("could not", true) || it.startsWith("Enter")) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary, style = MaterialTheme.typography.bodySmall) }

            if (!loading && loadError == null && items.isEmpty()) {
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(18.dp), verticalArrangement = Arrangement.spacedBy(6.dp), horizontalAlignment = Alignment.CenterHorizontally) {
                        Icon(Icons.Filled.Payments, contentDescription = null, tint = MaterialTheme.colorScheme.primary)
                        Text("No rent reminders yet", fontWeight = FontWeight.SemiBold)
                        Text("Add a due date and amount to keep your housing costs organized.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            items.forEach { obligation ->
                val id = obligation.optString("id")
                val amountDue = obligation.optString("amount_kes", "0")
                val remaining = obligation.optString("remaining_based_on_reports_kes", amountDue)
                val status = obligation.optString("status", "open")
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(9.dp)) {
                        Row(verticalAlignment = Alignment.Top) {
                            Column(Modifier.weight(1f), verticalArrangement = Arrangement.spacedBy(3.dp)) {
                                Text(obligation.optString("title"), style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.Bold)
                                Text(obligation.optString("property_reference").takeIf(String::isNotBlank) ?: "Personal rent reminder", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                            }
                            Text("KSh ${formatKes(amountDue)}", fontWeight = FontWeight.Bold, color = MaterialTheme.colorScheme.primary)
                        }
                        Text("Due ${obligation.optString("due_date")}  ·  ${status.replaceFirstChar(Char::uppercase)}", style = MaterialTheme.typography.bodySmall)
                        Text("Reported by you: KSh ${formatKes(obligation.optString("reported_total_kes", "0"))}  ·  Balance from reports: KSh ${formatKes(remaining)}", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.Medium)
                        Text("A full reported amount is still not verified by HomeScout.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)

                        val payments = obligation.optJSONArray("payments")
                        if (payments != null) for (index in 0 until payments.length()) {
                            val entry = payments.optJSONObject(index) ?: continue
                            Row(verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text("KSh ${formatKes(entry.optString("amount_kes"))} · ${rentPaymentMethods.firstOrNull { it.first == entry.optString("payment_method") }?.second ?: "Other"}", style = MaterialTheme.typography.bodySmall, fontWeight = FontWeight.SemiBold)
                                    Text("Reported ${entry.optString("paid_on")} · not provider-confirmed", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                                    entry.optString("reference").takeIf(String::isNotBlank)?.let { Text("Reference: $it", style = MaterialTheme.typography.labelSmall, color = MaterialTheme.colorScheme.onSurfaceVariant) }
                                }
                                TextButton(enabled = !saving, onClick = {
                                    saving = true
                                    scope.launch {
                                        runCatching { withContext(Dispatchers.IO) { api.deleteRentPayment(accessToken, entry.optString("id")); api.rentObligations(accessToken) } }
                                            .onSuccess { items = it; actionMessage = "Your payment note was removed." }
                                            .onFailure { actionMessage = it.message ?: "The payment note could not be removed." }
                                        saving = false
                                    }
                                }) { Text("Remove") }
                            }
                        }

                        if (reportFor == id) {
                            Column(verticalArrangement = Arrangement.spacedBy(9.dp)) {
                                OutlinedTextField(reportAmount, { reportAmount = it }, label = { Text("Amount you paid (KES)") }, keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal), modifier = Modifier.fillMaxWidth(), singleLine = true)
                                HomeScoutDateField(reportDate, { reportDate = it }, "Date paid · DD-MM-YYYY", Modifier.fillMaxWidth())
                                OutlinedButton(onClick = { methodMenu = true }, modifier = Modifier.fillMaxWidth()) { Text("Method: ${rentPaymentMethods.first { it.first == reportMethod }.second}") }
                                DropdownMenu(expanded = methodMenu, onDismissRequest = { methodMenu = false }) {
                                    rentPaymentMethods.forEach { (code, label) -> DropdownMenuItem(text = { Text(label) }, onClick = { reportMethod = code; methodMenu = false }) }
                                }
                                OutlinedTextField(reportReference, { reportReference = it }, label = { Text("Reference (optional)") }, modifier = Modifier.fillMaxWidth(), singleLine = true)
                                OutlinedTextField(reportNotes, { reportNotes = it }, label = { Text("Private note (optional)") }, modifier = Modifier.fillMaxWidth(), minLines = 2)
                                Text("This saves a note about an external payment. It does not start checkout or confirm receipt.", color = MaterialTheme.colorScheme.onSurfaceVariant, style = MaterialTheme.typography.bodySmall)
                                Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                                    OutlinedButton(onClick = { reportFor = null }, enabled = !saving, modifier = Modifier.weight(1f)) { Text("Cancel") }
                                    Button(onClick = {
                                        val parsed = reportAmount.trim().replace(",", "").toBigDecimalOrNull()
                                        if (parsed == null || parsed <= java.math.BigDecimal.ZERO || runCatching { LocalDate.parse(reportDate) }.isFailure) {
                                            actionMessage = "Enter a positive KES amount and valid payment date."
                                        } else {
                                            perform({ api.reportRentPayment(accessToken, id, JSONObject().put("amount_kes", parsed.toPlainString()).put("payment_method", reportMethod).put("paid_on", reportDate.trim()).put("reference", reportReference.trim()).put("notes", reportNotes.trim()).put("request_id", UUID.randomUUID().toString())) }, "Your payment was saved as a private report, not a confirmed payment.")
                                        }
                                    }, enabled = !saving, modifier = Modifier.weight(1f)) { if (saving) CircularProgressIndicator(Modifier.height(18.dp), strokeWidth = 2.dp) else Text("Save report") }
                                }
                            }
                        } else if (status == "open" && remaining.toBigDecimalOrNull()?.let { it > java.math.BigDecimal.ZERO } == true) {
                            OutlinedButton(onClick = { reportFor = id; reportAmount = ""; reportDate = LocalDate.now().toString(); reportReference = ""; reportNotes = "" }, modifier = Modifier.fillMaxWidth().heightIn(min = 44.dp)) {
                                Text("Record an external payment")
                            }
                        }
                        TextButton(enabled = !saving, onClick = {
                            val targetStatus = if (status == "open") "cancelled" else "open"
                            val body = JSONObject()
                                .put("title", obligation.optString("title"))
                                .put("amount_kes", amountDue)
                                .put("due_date", obligation.optString("due_date"))
                                .put("property_reference", obligation.optString("property_reference"))
                                .put("notes", obligation.optString("notes"))
                                .put("status", targetStatus)
                            perform({ api.updateRentObligation(accessToken, id, body) }, if (targetStatus == "open") "Rent reminder reopened." else "Rent reminder cancelled.")
                        }) { Text(if (status == "open") "Cancel reminder" else "Reopen reminder") }
                    }
                }
            }
        }
    }
}

private fun formatKes(value: String): String {
    val number = value.toBigDecimalOrNull() ?: java.math.BigDecimal.ZERO
    return java.text.NumberFormat.getNumberInstance(java.util.Locale.forLanguageTag("en-KE")).format(number)
}
