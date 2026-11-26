package ke.co.homescout.features.services

import androidx.compose.foundation.horizontalScroll
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.foundation.text.KeyboardOptions
import androidx.compose.ui.text.font.FontWeight
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import ke.co.homescout.data.remote.*
import ke.co.homescout.ui.components.*
import ke.co.homescout.ui.theme.HomeScoutColors
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.launch
import kotlinx.coroutines.withContext
import org.json.JSONObject
import androidx.compose.ui.platform.LocalContext
import androidx.activity.compose.rememberLauncherForActivityResult
import androidx.activity.result.contract.ActivityResultContracts
import android.net.Uri
import java.time.LocalDate
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.format.DateTimeFormatter
import java.util.UUID

private val serviceCategories = listOf(
    "All services" to null,
    "Movers" to "movers",
    "Cleaners" to "cleaners",
    "Plumbers" to "plumbers",
    "Electricians" to "electricians",
    "Internet" to "internet_providers",
    "Furniture" to "furniture_providers",
    "Handymen" to "handymen",
    "Maintenance" to "home_maintenance",
    "Other" to "other"
)

private fun categoryLabel(value: String): String =
    serviceCategories.firstOrNull { it.second == value }?.first ?: value.replace('_', ' ')

private fun statusLabel(value: String): String = value.replace('_', ' ').replaceFirstChar { it.uppercase() }

@Composable
@OptIn(ExperimentalMaterial3Api::class)
fun ServicesScreen(
    accessToken: String?,
    userId: String?,
    onSignIn: () -> Unit,
    onPayments: () -> Unit = {},
    initialTab: String = ""
) {
    val tabs = listOf("Explore", "Bookings", "Move plan", "Maintenance", "Provider")
    var selectedTab by rememberSaveable(initialTab) {
        mutableIntStateOf(tabs.indexOf(initialTab).takeIf { it >= 0 } ?: 0)
    }
    Column(Modifier.fillMaxSize()) {
        Column(Modifier.fillMaxWidth().padding(horizontal = 20.dp, vertical = 10.dp)) {
            Text("Services for your home", style = MaterialTheme.typography.headlineSmall, fontWeight = FontWeight.Bold)
            Text(
                "Find local help for moving, setup and everyday home needs.",
                style = MaterialTheme.typography.bodyMedium,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
        }
        PrimaryScrollableTabRow(selectedTabIndex = selectedTab, edgePadding = 16.dp) {
            tabs.forEachIndexed { index, title -> Tab(
                selected = selectedTab == index,
                onClick = { selectedTab = index },
                text = { Text(title) }
            ) }
        }
        when (selectedTab) {
            0 -> ServiceDiscoveryPanel(accessToken = accessToken, onSignIn = onSignIn)
            1 -> ServiceBookingsPanel(accessToken = accessToken, onSignIn = onSignIn, onPayments = onPayments)
            2 -> MovingPlanPanel(accessToken = accessToken, onSignIn = onSignIn)
            3 -> MaintenancePanel(accessToken = accessToken, userId = userId, onSignIn = onSignIn)
            else -> ProviderPanel(accessToken = accessToken, onSignIn = onSignIn)
        }
    }
}

@Composable
private fun ServiceDiscoveryPanel(accessToken: String?, onSignIn: () -> Unit) {
    val scope = rememberCoroutineScope()
    var query by remember { mutableStateOf("") }
    var category by remember { mutableStateOf<String?>(null) }
    var categoryMenu by remember { mutableStateOf(false) }
    var minPrice by remember { mutableStateOf("") }
    var maxPrice by remember { mutableStateOf("") }
    var counties by remember { mutableStateOf<List<ServiceLocation>>(emptyList()) }
    var selectedCounty by remember { mutableStateOf<ServiceLocation?>(null) }
    var countyMenu by remember { mutableStateOf(false) }
    var verifiedOnly by remember { mutableStateOf(false) }
    var services by remember { mutableStateOf<List<ServiceOffering>>(emptyList()) }
    var compareIds by remember { mutableStateOf<Set<String>>(emptySet()) }
    var comparison by remember { mutableStateOf<List<ServiceOffering>?>(null) }
    var loading by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    var selectedBooking by remember { mutableStateOf<ServiceOffering?>(null) }
    var selectedProvider by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }

    LaunchedEffect(Unit) {
        withContext(Dispatchers.IO) { runCatching { ServicesApi().counties() }.getOrNull() }
            ?.let { counties = it }
    }
    LaunchedEffect(query, category, minPrice, maxPrice, verifiedOnly, selectedCounty?.id, reload) {
        delay(300)
        loading = true
        error = null
        val response = withContext(Dispatchers.IO) {
            runCatching {
                ServicesApi().search(
                    query, category, minPrice, maxPrice,
                    countyId = selectedCounty?.id, verifiedOnly = verifiedOnly
                )
            }
        }
        response.onSuccess { services = it }.onFailure {
            services = emptyList()
            error = it.message ?: "Services could not be loaded."
        }
        loading = false
    }

    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(horizontal = 20.dp)) {
        Spacer(Modifier.height(16.dp))
        HomeScoutSearchField(query, { query = it }, "Search movers, cleaners, plumbers…", Modifier.fillMaxWidth())
        Spacer(Modifier.height(10.dp))
        Box {
            OutlinedButton(onClick = { categoryMenu = true }) {
                Text(serviceCategories.firstOrNull { it.second == category }?.first ?: "All services")
            }
            DropdownMenu(expanded = categoryMenu, onDismissRequest = { categoryMenu = false }) {
                serviceCategories.forEach { (label, value) -> DropdownMenuItem(
                    text = { Text(label) }, onClick = { category = value; categoryMenu = false }
                ) }
            }
        }
        Box {
            OutlinedButton(onClick = { countyMenu = true }) {
                Text(selectedCounty?.name ?: "All Kenya")
            }
            DropdownMenu(countyMenu, { countyMenu = false }) {
                DropdownMenuItem(text = { Text("All Kenya") }, onClick = { selectedCounty = null; countyMenu = false })
                counties.forEach { item -> DropdownMenuItem(
                    text = { Text(item.name) }, onClick = { selectedCounty = item; countyMenu = false }
                ) }
            }
        }
        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.spacedBy(8.dp)) {
            OutlinedTextField(minPrice, { minPrice = it.filter(Char::isDigit) }, label = { Text("From KES") }, modifier = Modifier.weight(1f), singleLine = true)
            OutlinedTextField(maxPrice, { maxPrice = it.filter(Char::isDigit) }, label = { Text("To KES") }, modifier = Modifier.weight(1f), singleLine = true)
        }
        Row(verticalAlignment = Alignment.CenterVertically) {
            Checkbox(verifiedOnly, { verifiedOnly = it })
            Text("Show providers with current approval records", style = MaterialTheme.typography.bodySmall)
        }
        Spacer(Modifier.height(6.dp))
        if (compareIds.size >= 2) {
            HomeScoutPrimaryButton("Compare ${compareIds.size} services", Modifier.fillMaxWidth()) {
                scope.launch {
                    loading = true
                    val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().compare(compareIds.toList()) } }
                    comparison = result.getOrNull()
                    error = result.exceptionOrNull()?.message
                    loading = false
                }
            }
        }
        comparison?.let { compared ->
            HomeScoutCard(Modifier.fillMaxWidth().padding(top = 10.dp)) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    SectionHeading("Service comparison", action = "Close", onAction = { comparison = null })
                    compared.forEach { Text("${it.title} · ${it.priceKes?.let { price -> "KSh $price" } ?: "Quote"} · ${categoryLabel(it.category)}") }
                }
            }
        }
        Spacer(Modifier.height(10.dp))
        when {
            loading -> LoadingState("Finding available provider services")
            error != null -> ErrorState("Services unavailable", error!!, onRetry = { reload++ })
            services.isEmpty() -> EmptyState(
                "No matching services yet",
                "Try a different category or search. Provider listings appear after a provider publishes an active service."
            )
            else -> services.forEach { offering ->
                ServiceOfferingCard(
                    offering = offering,
                    compared = offering.id in compareIds,
                    onCompare = {
                        compareIds = if (offering.id in compareIds) compareIds - offering.id
                        else if (compareIds.size < 5) compareIds + offering.id else compareIds
                        comparison = null
                    },
                    onBook = { selectedBooking = offering },
                    onProviderProfile = { selectedProvider = offering.providerId },
                    canBook = accessToken != null,
                    onSignIn = onSignIn
                )
            }
        }
    }
    selectedBooking?.let { offering ->
        ServiceBookingDialog(
            offering = offering,
            token = accessToken,
            onDismiss = { selectedBooking = null },
            onSubmitted = { reload++; selectedBooking = null }
        )
    }
    selectedProvider?.let { providerId -> ProviderProfileDialog(providerId) { selectedProvider = null } }
}

@Composable
private fun ServiceOfferingCard(
    offering: ServiceOffering,
    compared: Boolean,
    onCompare: () -> Unit,
    onBook: () -> Unit,
    onProviderProfile: () -> Unit,
    canBook: Boolean,
    onSignIn: () -> Unit
) {
    HomeScoutCard(Modifier.fillMaxWidth().padding(vertical = 6.dp)) {
        Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                HomeScoutBadge(categoryLabel(offering.category), color = HomeScoutColors.navy, background = HomeScoutColors.paleBlue)
                VerificationBadge(offering.verification)
            }
            Text(offering.title, style = MaterialTheme.typography.titleLarge, fontWeight = FontWeight.SemiBold)
            Text(offering.providerName, color = MaterialTheme.colorScheme.onSurfaceVariant)
            TextButton(onClick = onProviderProfile, contentPadding = PaddingValues(0.dp)) {
                Text("View provider profile")
            }
            Text(offering.description, style = MaterialTheme.typography.bodyMedium)
            Text(offering.priceKes?.let { "KSh $it · ${offering.pricingModel}" } ?: "Request a quote", color = HomeScoutColors.navy, fontWeight = FontWeight.Bold)
            Text(offering.areas.ifEmpty { listOf("Service area not listed") }.joinToString(" · "), style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            Text(
                if (offering.availableDays.isEmpty()) "Availability times not listed · confirm with provider"
                else "Listed days: ${offering.availableDays.joinToString()}",
                style = MaterialTheme.typography.bodySmall,
                color = MaterialTheme.colorScheme.onSurfaceVariant
            )
            Text(
                offering.rating?.let { "%.1f ★ · %d completed-service reviews".format(it, offering.reviewCount) }
                    ?: "No completed-service reviews yet",
                style = MaterialTheme.typography.bodySmall
            )
            Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                OutlinedButton(onClick = onCompare, modifier = Modifier.weight(1f)) { Text(if (compared) "Remove compare" else "Compare") }
                Button(onClick = if (canBook) onBook else onSignIn, modifier = Modifier.weight(1f)) {
                    Text(if (canBook) "Request service" else "Sign in to request")
                }
            }
        }
    }
}

@Composable
private fun ProviderProfileDialog(providerId: String, onDismiss: () -> Unit) {
    var profile by remember(providerId) { mutableStateOf<JSONObject?>(null) }
    var error by remember(providerId) { mutableStateOf<String?>(null) }
    LaunchedEffect(providerId) {
        val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().publicProvider(providerId) } }
        result.onSuccess { profile = it }.onFailure { error = it.message }
    }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text(profile?.optString("public_name") ?: "Service provider") },
        text = {
            when {
                error != null -> Text(error!!, color = MaterialTheme.colorScheme.error)
                profile == null -> LoadingState("Loading provider profile")
                else -> Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text(profile?.optString("description").orEmpty())
                    Text("Approval record: ${statusLabel(profile?.optString("verification_status") ?: "not_submitted")}")
                    profile?.optString("availability_note")?.takeIf(String::isNotBlank)?.let {
                        Text("Availability: $it")
                    }
                    val areas = profile?.optJSONArray("service_areas")
                    if (areas != null) for (index in 0 until areas.length()) {
                        val area = areas.optJSONObject(index) ?: continue
                        val name = listOf(area.optString("town_name"), area.optString("county_name"))
                            .filter(String::isNotBlank).distinct().joinToString(", ")
                        if (name.isNotBlank()) Text(name)
                    }
                    val reviewCount = profile?.optInt("review_count") ?: 0
                    val average = if (profile?.isNull("average_rating") == true) null
                    else profile?.optDouble("average_rating")
                    Text(
                        average?.let { "%.1f average · %d completed-service reviews".format(it, reviewCount) }
                            ?: "No completed-service reviews yet"
                    )
                }
            }
        },
        confirmButton = { TextButton(onClick = onDismiss) { Text("Done") } }
    )
}

@Composable
private fun VerificationBadge(status: String) {
    val (label, color, background) = when (status) {
        "verified" -> Triple("Provider approved", HomeScoutColors.greenText, HomeScoutColors.paleGreen)
        "pending" -> Triple("Approval pending", HomeScoutColors.navy, HomeScoutColors.paleBlue)
        "expired" -> Triple("Approval expired", HomeScoutColors.red, HomeScoutColors.paleRed)
        "rejected" -> Triple("Not approved", HomeScoutColors.red, HomeScoutColors.paleRed)
        else -> Triple("Not verified", HomeScoutColors.muted, HomeScoutColors.background)
    }
    HomeScoutBadge(label, color = color, background = background)
}

@Composable
private fun ServiceBookingDialog(
    offering: ServiceOffering,
    token: String?,
    onDismiss: () -> Unit,
    onSubmitted: () -> Unit
) {
    val scope = rememberCoroutineScope()
    var dateTime by remember {
        mutableStateOf(
            OffsetDateTime.now(ZoneId.of("Africa/Nairobi")).plusDays(1)
                .withMinute(0).withSecond(0).withNano(0).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
        )
    }
    var details by remember { mutableStateOf("") }
    var busy by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Request ${offering.title}") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(10.dp)) {
                Text("Your request stays pending until the provider responds. Times use the Africa/Nairobi timezone.")
                OutlinedButton(onClick = {
                    dateTime = OffsetDateTime.now(ZoneId.of("Africa/Nairobi"))
                        .plusDays(kotlin.random.Random.nextLong(2, 15))
                        .withHour(listOf(9, 11, 14, 16).random()).withMinute(0).withSecond(0).withNano(0)
                        .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
                    details = "DEMO · ${listOf("Please help move a one-bedroom home and protect fragile boxes.", "Please quote a deep clean for a small apartment before move-in.", "Please check a leaking kitchen tap and share an estimate.").random()}"
                }, enabled = !busy, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                Text("DEMO only · submitting below sends a real pending request to this provider, so review and edit first.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                HomeScoutDateTimeField(dateTime, { dateTime = it }, "Requested date and time · DD-MM-YYYY", Modifier.fillMaxWidth())
                OutlinedTextField(details, { details = it }, label = { Text("What do you need?") }, minLines = 3)
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = {
            TextButton(enabled = !busy && details.trim().length >= 10, onClick = {
                scope.launch {
                    busy = true; error = null
                    val result = withContext(Dispatchers.IO) {
                        runCatching { ServicesApi().createBooking(token!!, offering.id, dateTime, details.trim()) }
                    }
                    result.onSuccess { onSubmitted() }.onFailure { error = it.message ?: "Request could not be sent." }
                    busy = false
                }
            }) { Text(if (busy) "Sending…" else "Send request") }
        },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun ServiceBookingsPanel(accessToken: String?, onSignIn: () -> Unit, onPayments: () -> Unit) {
    if (accessToken == null) return SignInPrompt(onSignIn, "Sign in to see service requests and orders.")
    val scope = rememberCoroutineScope()
    var bookings by remember { mutableStateOf<List<ServiceBooking>>(emptyList()) }
    var orders by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var loading by remember { mutableStateOf(true) }
    var error by remember { mutableStateOf<String?>(null) }
    var actionError by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }
    var reviewBooking by remember { mutableStateOf<ServiceBooking?>(null) }
    var rescheduleBooking by remember { mutableStateOf<ServiceBooking?>(null) }
    var payBooking by remember { mutableStateOf<ServiceBooking?>(null) }
    LaunchedEffect(accessToken, reload) {
        loading = true
        val response = withContext(Dispatchers.IO) {
            runCatching { ServicesApi().bookings(accessToken) to ServicesApi().orders(accessToken) }
        }
        response.onSuccess { (items, orderItems) -> bookings = items; orders = orderItems }
            .onFailure { error = it.message ?: "Bookings could not be loaded." }
        loading = false
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionHeading("Service requests")
        Text("Requests are not confirmed until the provider accepts them.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        actionError?.let { Text(it, color = MaterialTheme.colorScheme.error) }
        when {
            loading -> LoadingState("Loading your bookings")
            error != null -> ErrorState("Bookings unavailable", error!!, onRetry = { reload++ })
            bookings.isEmpty() -> EmptyState("No service requests", "Your service booking history will appear here.")
            else -> bookings.forEach { booking ->
                HomeScoutCard(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                        Text(booking.offeringTitle, style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                        Text(if (booking.customer) "Provider: ${booking.providerName}" else "Customer request", style = MaterialTheme.typography.bodySmall)
                        Text("${statusLabel(booking.status)} · ${booking.requestedAt}", color = HomeScoutColors.navy)
                        booking.proposedAt?.let { Text("Proposed time: $it") }
                        Text(booking.details)
                        booking.estimatedAmount?.let { Text("Listed fixed price at request: KSh $it (not charged)", style = MaterialTheme.typography.bodySmall) }
                        Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                            if (!booking.customer && booking.status == "pending") {
                                BookingActionButton("Accept", booking, "accept", accessToken, { reload++ }) { actionError = it }
                                BookingActionButton("Decline", booking, "reject", accessToken, { reload++ }) { actionError = it }
                            }
                            if (booking.customer && booking.status == "reschedule_proposed") {
                                BookingActionButton("Accept time", booking, "accept_reschedule", accessToken, { reload++ }) { actionError = it }
                                BookingActionButton("Decline time", booking, "decline_reschedule", accessToken, { reload++ }) { actionError = it }
                            }
                            if (booking.customer && booking.status in setOf("pending", "accepted", "rescheduled")) {
                                BookingActionButton("Cancel request", booking, "cancel", accessToken, { reload++ }) { actionError = it }
                            }
                            if (!booking.customer && booking.status in setOf("accepted", "rescheduled")) {
                                TextButton(onClick = { rescheduleBooking = booking }) { Text("Suggest another time") }
                                BookingActionButton("Complete", booking, "complete", accessToken, { reload++ }) { actionError = it }
                            }
                            if (booking.customer && booking.status == "completed") {
                                TextButton(onClick = { reviewBooking = booking }) { Text("Review service") }
                            }
                            if (booking.customer && booking.status == "accepted" &&
                                booking.estimatedAmount != null && booking.orderId != null &&
                                orders.any { order ->
                                    order.optString("id") == booking.orderId &&
                                        order.optString("pricing_model_snapshot") == "fixed"
                                }
                            ) {
                                OutlinedButton(onClick = { payBooking = booking }) {
                                    Text("Request KSh ${booking.estimatedAmount} M-Pesa")
                                }
                            }
                        }
                    }
                }
            }
        }
        if (orders.isNotEmpty()) {
            SectionHeading("Service order records")
            Text("These records track requests and listed estimates. HomeScout does not collect service payments in this phase.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
            orders.forEach { order ->
                Text("${order.optString("offering_title_snapshot")} · ${statusLabel(order.optString("status"))} · ${order.optString("estimated_amount_kes").takeIf(String::isNotBlank)?.let { "KSh $it estimated" } ?: "Quote not set"}")
            }
        }
    }
    reviewBooking?.let { booking -> ReviewDialog(booking.id, accessToken, { reviewBooking = null }) { reload++ } }
    rescheduleBooking?.let { booking ->
        RescheduleDialog(booking.id, accessToken, { rescheduleBooking = null }) { reload++ }
    }
    payBooking?.let { booking ->
        ServicePaymentDialog(
                        booking = booking,
            token = accessToken,
            onDismiss = { payBooking = null },
            onViewHistory = {
                payBooking = null
                onPayments()
            }
        )
    }
}

@Composable
private fun ServicePaymentDialog(
    booking: ServiceBooking,
    token: String,
    onDismiss: () -> Unit,
    onViewHistory: () -> Unit
) {
    val scope = rememberCoroutineScope()
    val requestKey = remember(booking.id) { UUID.randomUUID().toString() }
    var configuration by remember { mutableStateOf<JSONObject?>(null) }
    var phoneNumber by remember { mutableStateOf("") }
    var transaction by remember { mutableStateOf<JSONObject?>(null) }
    var loadingConfiguration by remember { mutableStateOf(true) }
    var working by remember { mutableStateOf(false) }
    var error by remember { mutableStateOf<String?>(null) }

    LaunchedEffect(booking.id) {
        val response = withContext(Dispatchers.IO) {
            runCatching { PaymentsApi().configuration() }
        }
        response.onSuccess { configuration = it }
            .onFailure { error = it.message ?: "M-Pesa configuration could not be checked." }
        loadingConfiguration = false
    }

    val enabled = configuration?.optBoolean("enabled") == true
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Service booking payment") },
        text = {
            Column(
                Modifier.fillMaxWidth().heightIn(max = 420.dp).verticalScroll(rememberScrollState()),
                verticalArrangement = Arrangement.spacedBy(10.dp)
            ) {
                Text(booking.offeringTitle, fontWeight = FontWeight.SemiBold)
                Text("Fixed booking amount · KSh ${booking.estimatedAmount}")
                when {
                    loadingConfiguration -> LinearProgressIndicator(Modifier.fillMaxWidth())
                    enabled -> Text(
                        configuration?.optString("message").orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        color = HomeScoutColors.muted
                    )
                    configuration != null -> Text(
                        configuration?.optString("message").orEmpty(),
                        style = MaterialTheme.typography.bodySmall,
                        color = HomeScoutColors.muted
                    )
                }
                if (transaction == null) {
                    OutlinedTextField(
                        value = phoneNumber,
                        onValueChange = { phoneNumber = it.take(16) },
                        modifier = Modifier.fillMaxWidth(),
                        label = { Text("M-Pesa phone number") },
                        placeholder = { Text("07… or +254…") },
                        singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Phone),
                        enabled = enabled && !working
                    )
                    Text(
                        "HomeScout will request an STK prompt for this accepted service booking. " +
                            "The server checks Daraja before showing a payment as successful.",
                        style = MaterialTheme.typography.bodySmall,
                        color = MaterialTheme.colorScheme.onSurfaceVariant
                    )
                } else {
                    val status = transaction?.optString("status", "pending").orEmpty()
                    Text(
                        when (status) {
                            "successful" -> "Daraja confirmed this payment."
                            "failed" -> "Daraja did not complete this payment request."
                            "cancelled" -> "The payment request was cancelled."
                            "expired" -> "The payment request expired."
                            else -> "The request is pending. Check your phone for the M-Pesa prompt, then wait for server confirmation."
                        },
                        color = if (status == "successful") homeScoutSuccessTextColor() else MaterialTheme.colorScheme.onSurfaceVariant
                    )
                    Text("Status: ${statusLabel(status)}", fontWeight = FontWeight.SemiBold)
                    transaction?.optString("phone_masked")?.takeIf(String::isNotBlank)?.let { Text("Sent to $it") }
                    transaction?.optString("receipt_number")?.takeIf(String::isNotBlank)?.let {
                        Text("M-Pesa receipt: $it")
                    }
                }
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = {
            if (transaction != null) {
                TextButton(onClick = onViewHistory) { Text("View payment history") }
            } else {
                Button(
                    enabled = enabled && !loadingConfiguration && !working && phoneNumber.isNotBlank(),
                    onClick = {
                        scope.launch {
                            working = true
                            error = null
                            val response = withContext(Dispatchers.IO) {
                                runCatching {
                                    PaymentsApi().requestServicePayment(
                                        token = token,
                                        serviceOrderId = booking.orderId.orEmpty(),
                                        phoneNumber = phoneNumber,
                                        idempotencyKey = requestKey
                                    )
                                }
                            }
                            response.onSuccess { transaction = it }
                                .onFailure { error = it.message ?: "The payment request could not be sent." }
                            working = false
                        }
                    }
                ) {
                    if (working) CircularProgressIndicator(Modifier.size(18.dp), strokeWidth = 2.dp)
                    else Text("Request STK Push")
                }
            }
        },
        dismissButton = {
            TextButton(onClick = onDismiss, enabled = !working) { Text("Close") }
        }
    )
}

@Composable
private fun BookingActionButton(
    label: String,
    booking: ServiceBooking,
    action: String,
    token: String,
    onUpdated: () -> Unit,
    onError: (String) -> Unit
) {
    val scope = rememberCoroutineScope()
    var busy by remember { mutableStateOf(false) }
    OutlinedButton(enabled = !busy, onClick = {
        scope.launch {
            busy = true
            val response = withContext(Dispatchers.IO) {
                runCatching { ServicesApi().bookingAction(token, booking.id, action) }
            }
            response.onSuccess { onUpdated() }.onFailure { onError(it.message ?: "The request could not be updated.") }
            busy = false
        }
    }) { Text(if (busy) "Updating…" else label) }
}

@Composable
private fun RescheduleDialog(bookingId: String, token: String, onDismiss: () -> Unit, onSaved: () -> Unit) {
    val scope = rememberCoroutineScope()
    var proposedAt by remember {
        mutableStateOf(
            OffsetDateTime.now(ZoneId.of("Africa/Nairobi")).plusDays(2)
                .withMinute(0).withSecond(0).withNano(0).format(DateTimeFormatter.ISO_OFFSET_DATE_TIME)
        )
    }
    var error by remember { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Suggest another time") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("The customer must accept this proposed time before the request is rescheduled.")
                HomeScoutDateTimeField(proposedAt, { proposedAt = it }, "Proposed date and time · DD-MM-YYYY", Modifier.fillMaxWidth())
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = { TextButton(onClick = {
            scope.launch {
                val result = withContext(Dispatchers.IO) {
                    runCatching { ServicesApi().proposeReschedule(token, bookingId, proposedAt) }
                }
                result.onSuccess { onSaved(); onDismiss() }.onFailure { error = it.message }
            }
        }) { Text("Send proposal") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
private fun ReviewDialog(bookingId: String, token: String, onDismiss: () -> Unit, onSaved: () -> Unit) {
    val scope = rememberCoroutineScope()
    var review by remember { mutableStateOf("") }
    var rating by remember { mutableIntStateOf(5) }
    var error by remember { mutableStateOf<String?>(null) }
    AlertDialog(
        onDismissRequest = onDismiss,
        title = { Text("Review completed service") },
        text = {
            Column(verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("Rating: $rating / 5")
                Slider(value = rating.toFloat(), onValueChange = { rating = it.toInt().coerceIn(1, 5) }, valueRange = 1f..5f, steps = 3)
                OutlinedTextField(review, { review = it }, label = { Text("Review (optional)") }, minLines = 2)
                error?.let { Text(it, color = MaterialTheme.colorScheme.error) }
            }
        },
        confirmButton = { TextButton(onClick = {
            scope.launch {
                val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().review(token, bookingId, rating, review) } }
                result.onSuccess { onSaved(); onDismiss() }.onFailure { error = it.message }
            }
        }) { Text("Submit") } },
        dismissButton = { TextButton(onClick = onDismiss) { Text("Cancel") } }
    )
}

@Composable
@OptIn(ExperimentalMaterial3Api::class)
private fun MovingPlanPanel(accessToken: String?, onSignIn: () -> Unit) {
    if (accessToken == null) return SignInPrompt(onSignIn, "Sign in to keep a private moving checklist and budget.")
    val scope = rememberCoroutineScope()
    var plans by remember { mutableStateOf<List<MovePlanSummary>>(emptyList()) }
    var tasks by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var budgets by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var roomItems by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var selectedPlan by remember { mutableStateOf<MovePlanSummary?>(null) }
    var title by remember { mutableStateOf("") }
    var newTask by remember { mutableStateOf("") }
    var dueDate by remember { mutableStateOf("") }
    var taskCategory by remember { mutableStateOf("packing") }
    var budgetTitle by remember { mutableStateOf("") }
    var budgetAmount by remember { mutableStateOf("") }
    var room by remember { mutableStateOf("") }
    var furniture by remember { mutableStateOf("") }
    var message by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }
    var section by remember { mutableIntStateOf(0) }
    var calendarTasks by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    LaunchedEffect(accessToken, reload) {
        val response = withContext(Dispatchers.IO) { runCatching { ServicesApi().plans(accessToken) } }
        response.onSuccess { plans = it; if (selectedPlan == null) selectedPlan = it.firstOrNull() }
            .onFailure { message = it.message }
    }
    LaunchedEffect(accessToken, selectedPlan?.id, reload) {
        val plan = selectedPlan ?: return@LaunchedEffect
        withContext(Dispatchers.IO) {
            tasks = runCatching { ServicesApi().tasks(accessToken, plan.id) }.getOrDefault(emptyList())
            budgets = runCatching { ServicesApi().budgets(accessToken, plan.id) }.getOrDefault(emptyList())
            roomItems = runCatching { ServicesApi().roomSetup(accessToken, plan.id) }.getOrDefault(emptyList())
            val today = LocalDate.now(ZoneId.of("Africa/Nairobi"))
            calendarTasks = runCatching {
                ServicesApi().calendar(accessToken, today.toString(), today.plusDays(60).toString())
            }.getOrDefault(emptyList())
        }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionHeading("Moving plan")
        Text("Private to your account. Add packing, utilities, cleaning and moving day tasks.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (plans.isEmpty()) {
            OutlinedTextField(title, { title = it }, label = { Text("Plan name") }, modifier = Modifier.fillMaxWidth())
            Button(onClick = {
                scope.launch {
                    val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().createPlan(accessToken, title.ifBlank { "My move" }, null, null) } }
                    result.onSuccess { selectedPlan = it; title = ""; reload++ }.onFailure { message = it.message }
                }
            }) { Text("Create moving plan") }
        } else {
            var planMenu by remember { mutableStateOf(false) }
            OutlinedButton(onClick = { planMenu = true }) { Text(selectedPlan?.title ?: "Choose a moving plan") }
            DropdownMenu(planMenu, { planMenu = false }) { plans.forEach { plan -> DropdownMenuItem(
                text = { Text(plan.title) }, onClick = { selectedPlan = plan; planMenu = false }
            ) } }
            PrimaryScrollableTabRow(selectedTabIndex = section, edgePadding = 0.dp) {
                listOf("Checklist", "Budget", "Room setup").forEachIndexed { index, label -> Tab(
                    selected = section == index, onClick = { section = index }, text = { Text(label) }
                ) }
            }
            when (section) {
                0 -> {
                    OutlinedButton(onClick = {
                        newTask = "DEMO · ${listOf("Pack kitchen items", "Confirm moving van", "Set up internet", "Collect keys").random()}"
                        dueDate = LocalDate.now(ZoneId.of("Africa/Nairobi")).plusDays(kotlin.random.Random.nextLong(2, 18)).toString()
                        taskCategory = listOf("packing", "moving_day", "internet_setup", "utilities").random()
                    }, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                    Text("DEMO task · save it to this moving plan only if you want the sample kept.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedTextField(newTask, { newTask = it }, label = { Text("Task") }, modifier = Modifier.fillMaxWidth())
                    HomeScoutDateField(dueDate, { dueDate = it }, "Deadline · DD-MM-YYYY (optional)", Modifier.fillMaxWidth(), allowClear = true)
                    var taskMenu by remember { mutableStateOf(false) }
                    Box {
                        OutlinedButton(onClick = { taskMenu = true }) { Text(categoryLabel(taskCategory)) }
                        DropdownMenu(taskMenu, { taskMenu = false }) {
                            listOf("packing", "moving_day", "utilities", "internet_setup", "cleaning", "furniture", "post_move", "other").forEach { value ->
                                DropdownMenuItem(text = { Text(categoryLabel(value)) }, onClick = { taskCategory = value; taskMenu = false })
                            }
                        }
                    }
                    HomeScoutPrimaryButton("Add checklist task", Modifier.fillMaxWidth()) {
                        scope.launch {
                            val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().addTask(accessToken, selectedPlan!!.id, newTask, taskCategory, dueDate.ifBlank { null }) } }
                            result.onSuccess { newTask = ""; reload++ }.onFailure { message = it.message }
                        }
                    }
                    tasks.forEach { task ->
                        HomeScoutCard(Modifier.fillMaxWidth()) {
                            Row(Modifier.fillMaxWidth().padding(12.dp), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                                Column(Modifier.weight(1f)) {
                                    Text(task.optString("title"), fontWeight = FontWeight.Medium)
                                    Text("${categoryLabel(task.optString("category"))} · ${task.optString("due_date", "No deadline")}", style = MaterialTheme.typography.bodySmall)
                                }
                                if (task.optString("status") == "open") TextButton(onClick = {
                                    scope.launch { withContext(Dispatchers.IO) { ServicesApi().updateTask(accessToken, task.optString("id"), "completed") }; reload++ }
                                }) { Text("Done") }
                            }
                        }
                    }
                    SectionHeading("Calendar · next 60 days")
                    if (calendarTasks.isEmpty()) {
                        Text("No dated move tasks in the next 60 days.", color = MaterialTheme.colorScheme.onSurfaceVariant)
                    } else calendarTasks.forEach { task ->
                        Text("${task.optString("due_date")} · ${task.optString("title")} · ${categoryLabel(task.optString("category"))}")
                    }
                }
                1 -> {
                    OutlinedButton(onClick = {
                        budgetTitle = "DEMO · ${listOf("Moving van", "Cleaning", "Packing supplies", "Internet setup").random()}"
                        budgetAmount = (kotlin.random.Random.nextInt(2, 16) * 1_000).toString()
                    }, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                    Text("DEMO cost · review before adding it to your moving budget.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        OutlinedTextField(budgetTitle, { budgetTitle = it }, label = { Text("Moving cost") }, modifier = Modifier.weight(1f))
                        OutlinedTextField(budgetAmount, { budgetAmount = it.filter { ch -> ch.isDigit() || ch == '.' } }, label = { Text("KES") }, modifier = Modifier.weight(1f))
                    }
                    HomeScoutPrimaryButton("Add budget item", Modifier.fillMaxWidth()) {
                        scope.launch { val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().addBudget(accessToken, selectedPlan!!.id, budgetTitle, budgetAmount) } }; result.onSuccess { budgetTitle = ""; budgetAmount = ""; reload++ }.onFailure { message = it.message } }
                    }
                    val total = budgets.sumOf { it.optString("amount_kes").toDoubleOrNull() ?: 0.0 }
                    Text("Planned service and moving costs: KSh ${"%.2f".format(total)}", fontWeight = FontWeight.Bold)
                    budgets.forEach { Text("${it.optString("title")} · KSh ${it.optString("amount_kes")}") }
                }
                else -> {
                    OutlinedButton(onClick = {
                        val sample = listOf("Bedroom" to "Bedside table", "Kitchen" to "Kettle", "Living room" to "Floor lamp", "Study" to "Desk chair").random()
                        room = "DEMO · ${sample.first}"
                        furniture = "DEMO · ${sample.second}"
                    }, modifier = Modifier.fillMaxWidth()) { Text("Fill a new random example") }
                    Text("DEMO room item · add it to this plan only if you want the sample saved.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    OutlinedTextField(room, { room = it }, label = { Text("Room") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(furniture, { furniture = it }, label = { Text("Furniture or item") }, modifier = Modifier.fillMaxWidth())
                    HomeScoutPrimaryButton("Add room item", Modifier.fillMaxWidth()) {
                        scope.launch { val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().addRoomItem(accessToken, selectedPlan!!.id, room, furniture, 1) } }; result.onSuccess { furniture = ""; reload++ }.onFailure { message = it.message } }
                    }
                    roomItems.forEach { item ->
                        Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
                            Text("${item.optString("room_name")} · ${item.optInt("quantity")} × ${item.optString("item_name")} · ${statusLabel(item.optString("status"))}", Modifier.weight(1f))
                            if (item.optString("status") == "planned") TextButton(onClick = {
                                scope.launch {
                                    withContext(Dispatchers.IO) {
                                        ServicesApi().updateRoomItem(accessToken, item.optString("id"), "purchased")
                                    }
                                    reload++
                                }
                            }) { Text("Purchased") }
                        }
                    }
                }
            }
        }
        message?.let { Text(it, color = MaterialTheme.colorScheme.error) }
    }
}

@Composable
private fun MaintenancePanel(accessToken: String?, userId: String?, onSignIn: () -> Unit) {
    if (accessToken == null) return SignInPrompt(onSignIn, "Sign in to submit or manage property maintenance requests.")
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var properties by remember { mutableStateOf<List<ResidentProperty>>(emptyList()) }
    var requests by remember { mutableStateOf<List<JSONObject>>(emptyList()) }
    var selectedProperty by remember { mutableStateOf<ResidentProperty?>(null) }
    var propertyMenu by remember { mutableStateOf(false) }
    var category by remember { mutableStateOf("plumbing") }
    var description by remember { mutableStateOf("") }
    var photoIds by remember { mutableStateOf<List<String>>(emptyList()) }
    var error by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }
    val photoPicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let { selectedUri ->
            scope.launch {
                val result = withContext(Dispatchers.IO) {
                    runCatching {
                        val filename = selectedUri.lastPathSegment?.substringAfterLast('/') ?: "maintenance-photo"
                        val bytes = context.contentResolver.openInputStream(selectedUri)?.use {
                            it.readNBytes(10 * 1024 * 1024 + 1)
                        } ?: throw ServicesApiException("The selected photo could not be read.")
                        if (bytes.size > 10 * 1024 * 1024) {
                            throw ServicesApiException("Choose a photo smaller than 10 MB.")
                        }
                        val response = PersonalHubApi().upload(
                            "hub/documents?category=other&filename=${PersonalHubApi.query(filename)}",
                            accessToken,
                            bytes
                        )
                        JSONObject(response).optString("id")
                    }
                }
                result.onSuccess { photoIds = photoIds + it; error = null }
                    .onFailure { error = it.message }
            }
        }
    }
    LaunchedEffect(accessToken, reload) {
        withContext(Dispatchers.IO) {
            runCatching { ServicesApi().residentProperties(accessToken) }.onSuccess { properties = it; if (selectedProperty == null) selectedProperty = it.firstOrNull() }
                .onFailure { error = it.message }
            runCatching { ServicesApi().maintenance(accessToken) }.onSuccess { requests = it }
                .onFailure { error = it.message }
        }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionHeading("Property maintenance")
        Text("Only properties whose owner or manager granted your account access appear here.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        Text("Photos are shared with the assigned property manager and service provider on this request.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (properties.isEmpty()) {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Text("No resident property access is recorded for this account. Ask your property manager to grant HomeScout access before submitting a request.", Modifier.padding(16.dp))
            }
        } else {
            Box {
                OutlinedButton(onClick = { propertyMenu = true }) { Text(selectedProperty?.let { "${it.title} · ${it.location}" } ?: "Choose property") }
                DropdownMenu(propertyMenu, { propertyMenu = false }) { properties.forEach { property -> DropdownMenuItem(
                    text = { Text("${property.title} · ${property.location}") }, onClick = { selectedProperty = property; propertyMenu = false }
                ) } }
            }
            var categoryMenu by remember { mutableStateOf(false) }
            Box {
                OutlinedButton(onClick = { categoryMenu = true }) { Text(categoryLabel(category)) }
                DropdownMenu(categoryMenu, { categoryMenu = false }) {
                    listOf("plumbing", "electrical", "cleaning", "internet", "appliance", "structural", "other").forEach { value ->
                        DropdownMenuItem(text = { Text(categoryLabel(value)) }, onClick = { category = value; categoryMenu = false })
                    }
                }
            }
            OutlinedTextField(description, { description = it }, label = { Text("Describe the issue") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
            OutlinedButton(enabled = photoIds.size < 8, onClick = { photoPicker.launch("image/*") }) {
                Text("Attach photo · ${photoIds.size}/8")
            }
            HomeScoutPrimaryButton("Submit maintenance request", Modifier.fillMaxWidth(), enabled = description.trim().length >= 10) {
                scope.launch {
                    val result = withContext(Dispatchers.IO) {
                        runCatching {
                            ServicesApi().createMaintenance(
                                accessToken, selectedProperty!!.id, category, description.trim(), photoIds
                            )
                        }
                    }
                    result.onSuccess { description = ""; photoIds = emptyList(); reload++ }
                        .onFailure { error = it.message }
                }
            }
        }
        error?.let { ErrorState("Maintenance update", it) }
        requests.forEach { item ->
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text(item.optString("property_title"), style = MaterialTheme.typography.titleSmall)
                    Text("${categoryLabel(item.optString("category"))} · ${statusLabel(item.optString("status"))} · ${item.optString("priority")}")
                    Text(item.optString("description"))
                    val status = item.optString("status")
                    val assigned = item.optString("assigned_provider_user_id") == userId
                    Row(horizontalArrangement = Arrangement.spacedBy(8.dp)) {
                        if (status == "submitted" && item.optString("resident_user_id") == userId) {
                            MaintenanceActionButton("Cancel", item.optString("id"), "cancel", accessToken, onDone = { reload++ }, onError = { error = it })
                        }
                        if (assigned && status == "assigned") MaintenanceActionButton("Start", item.optString("id"), "start", accessToken, onDone = { reload++ }, onError = { error = it })
                        if (assigned && status in setOf("assigned", "in_progress")) MaintenanceActionButton("Complete", item.optString("id"), "complete", accessToken, "Work completed by assigned provider.", onDone = { reload++ }, onError = { error = it })
                    }
                }
            }
        }
    }
}

@Composable
private fun MaintenanceActionButton(
    label: String,
    id: String,
    action: String,
    token: String,
    note: String? = null,
    onDone: () -> Unit,
    onError: (String) -> Unit
) {
    val scope = rememberCoroutineScope()
    OutlinedButton(onClick = {
        scope.launch {
            val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().maintenanceAction(token, id, action, note) } }
            result.onSuccess { onDone() }.onFailure { onError(it.message ?: "The request could not be updated.") }
        }
    }) { Text(label) }
}

@Composable
private fun ProviderPanel(accessToken: String?, onSignIn: () -> Unit) {
    if (accessToken == null) return SignInPrompt(onSignIn, "Sign in with an approved service-provider account to manage services and customer requests.")
    val scope = rememberCoroutineScope()
    val context = LocalContext.current
    var loaded by remember { mutableStateOf(false) }
    var profileName by remember { mutableStateOf("") }
    var profileDescription by remember { mutableStateOf("") }
    var published by remember { mutableStateOf(false) }
    var verificationStatus by remember { mutableStateOf("not_submitted") }
    var offeringTitle by remember { mutableStateOf("") }
    var offeringDescription by remember { mutableStateOf("") }
    var price by remember { mutableStateOf("") }
    var category by remember { mutableStateOf("movers") }
    var categoryMenu by remember { mutableStateOf(false) }
    var counties by remember { mutableStateOf<List<ServiceLocation>>(emptyList()) }
    var county by remember { mutableStateOf<ServiceLocation?>(null) }
    var countyMenu by remember { mutableStateOf(false) }
    var offerings by remember { mutableStateOf<List<ServiceOffering>>(emptyList()) }
    var bookings by remember { mutableStateOf<List<ServiceBooking>>(emptyList()) }
    var imageCount by remember { mutableIntStateOf(0) }
    var error by remember { mutableStateOf<String?>(null) }
    var reload by remember { mutableIntStateOf(0) }
    LaunchedEffect(accessToken, reload) {
        val data = withContext(Dispatchers.IO) {
            runCatching {
                val api = ServicesApi()
                Triple(api.providerProfile(accessToken), api.myOfferings(accessToken), api.bookings(accessToken)) to api.counties()
            }
        }
        data.onSuccess { (result, countyData) ->
            val (profile, myServices, myBookings) = result
            profileName = profile.optString("public_name")
            profileDescription = profile.optString("description")
            published = profile.optBoolean("is_published")
            verificationStatus = profile.optString("verification_status", "not_submitted")
            imageCount = profile.optJSONArray("image_ids")?.length() ?: 0
            offerings = myServices
            bookings = myBookings.filter { !it.customer }
            counties = countyData
            if (county == null) county = countyData.firstOrNull { it.name == "Nairobi" } ?: countyData.firstOrNull()
            loaded = true; error = null
        }.onFailure { error = it.message ?: "Provider access is unavailable."; loaded = true }
    }
    val imagePicker = rememberLauncherForActivityResult(ActivityResultContracts.GetContent()) { uri: Uri? ->
        uri?.let { selectedUri ->
            scope.launch {
                val result = withContext(Dispatchers.IO) {
                    runCatching {
                        val mime = context.contentResolver.getType(selectedUri)
                            ?: throw ServicesApiException("Choose a JPEG, PNG, or WebP image.")
                        val bytes = context.contentResolver.openInputStream(selectedUri)?.use {
                            it.readNBytes(10 * 1024 * 1024 + 1)
                        } ?: throw ServicesApiException("The selected image could not be read.")
                        if (bytes.size > 10 * 1024 * 1024) {
                            throw ServicesApiException("Choose an image smaller than 10 MB.")
                        }
                        ServicesApi().uploadProviderImage(
                            accessToken,
                            selectedUri.lastPathSegment?.substringAfterLast('/') ?: "provider-image",
                            mime,
                            bytes
                        )
                    }
                }
                result.onSuccess { imageCount++; error = null }.onFailure { error = it.message }
            }
        }
    }
    Column(Modifier.fillMaxSize().verticalScroll(rememberScrollState()).padding(20.dp), verticalArrangement = Arrangement.spacedBy(10.dp)) {
        SectionHeading("Provider workspace")
        Text("Provider approval status comes from the HomeScout review record. Profile publication does not mean the provider has been verified.", color = MaterialTheme.colorScheme.onSurfaceVariant)
        if (!loaded && error == null) LoadingState("Loading provider workspace")
        error?.let { ErrorState("Provider access unavailable", it, onRetry = { reload++ }) }
        if (loaded && error == null) {
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Public provider profile", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    OutlinedTextField(profileName, { profileName = it }, label = { Text("Business or provider name") }, modifier = Modifier.fillMaxWidth())
                    OutlinedTextField(profileDescription, { profileDescription = it }, label = { Text("About your services") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                    Row(verticalAlignment = Alignment.CenterVertically) {
                        Switch(published, { published = it })
                        Spacer(Modifier.width(8.dp)); Text("Publish profile")
                    }
                    Text("Verification record: ${statusLabel(verificationStatus)}", style = MaterialTheme.typography.bodySmall)
                    Button(onClick = {
                        scope.launch {
                            val result = withContext(Dispatchers.IO) { runCatching { ServicesApi().saveProviderProfile(accessToken, profileName, profileDescription, published) } }
                            result.onSuccess { reload++ }.onFailure { error = it.message }
                        }
                    }) { Text("Save profile") }
                    OutlinedButton(onClick = { imagePicker.launch("image/*") }) {
                        Text("Add profile photo · $imageCount saved")
                    }
                }
            }
            HomeScoutCard(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(16.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("Add a service", style = MaterialTheme.typography.titleMedium, fontWeight = FontWeight.SemiBold)
                    OutlinedTextField(offeringTitle, { offeringTitle = it }, label = { Text("Service title") }, modifier = Modifier.fillMaxWidth())
                    Box {
                        OutlinedButton(onClick = { categoryMenu = true }) { Text(categoryLabel(category)) }
                        DropdownMenu(categoryMenu, { categoryMenu = false }) { serviceCategories.drop(1).forEach { (label, value) ->
                            DropdownMenuItem(text = { Text(label) }, onClick = { category = value!!; categoryMenu = false })
                        } }
                    }
                    OutlinedTextField(offeringDescription, { offeringDescription = it }, label = { Text("Service description") }, modifier = Modifier.fillMaxWidth(), minLines = 3)
                    OutlinedTextField(price, { price = it.filter { ch -> ch.isDigit() || ch == '.' } }, label = { Text("Starting price · KES") }, modifier = Modifier.fillMaxWidth())
                    Box {
                        OutlinedButton(onClick = { countyMenu = true }) { Text(county?.name ?: "Choose county") }
                        DropdownMenu(countyMenu, { countyMenu = false }) { counties.forEach { item -> DropdownMenuItem(
                            text = { Text(item.name) }, onClick = { county = item; countyMenu = false }
                        ) } }
                    }
                    Text("A starting price is shown as indicative. You can also manage quote-based services through the API.", style = MaterialTheme.typography.bodySmall, color = MaterialTheme.colorScheme.onSurfaceVariant)
                    Button(enabled = county != null && price.toBigDecimalOrNull() != null && offeringDescription.trim().length >= 10,
                        onClick = {
                            scope.launch {
                                val result = withContext(Dispatchers.IO) { runCatching {
                                    ServicesApi().saveOffering(accessToken, offeringTitle, category, offeringDescription, price, county!!.id)
                                } }
                                result.onSuccess { offeringTitle = ""; offeringDescription = ""; price = ""; reload++ }.onFailure { error = it.message }
                            }
                        }) { Text("Save service") }
                }
            }
            if (offerings.isNotEmpty()) {
                SectionHeading("Your services")
                offerings.forEach { Text("${it.title} · ${if (it.active) "Active" else "Paused"} · ${it.priceKes?.let { p -> "KSh $p" } ?: "Quote"}") }
            }
            SectionHeading("Incoming customer requests")
            if (bookings.isEmpty()) Text("No requests have arrived.", color = MaterialTheme.colorScheme.onSurfaceVariant)
            bookings.forEach { booking -> Text("${booking.offeringTitle} · Customer request · ${statusLabel(booking.status)}") }
        }
    }
}

@Composable
private fun SignInPrompt(onSignIn: () -> Unit, text: String) {
    Column(Modifier.fillMaxWidth().padding(24.dp), verticalArrangement = Arrangement.spacedBy(12.dp), horizontalAlignment = Alignment.CenterHorizontally) {
        Text(text, style = MaterialTheme.typography.bodyLarge, color = MaterialTheme.colorScheme.onSurfaceVariant)
        Button(onClick = onSignIn) { Text("Go to Profile") }
    }
}
