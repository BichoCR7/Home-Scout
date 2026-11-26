package ke.co.homescout.ui.components

import android.app.DatePickerDialog
import android.app.TimePickerDialog
import androidx.compose.foundation.layout.Row
import androidx.compose.foundation.layout.Arrangement
import androidx.compose.material.icons.Icons
import androidx.compose.material.icons.filled.CalendarMonth
import androidx.compose.material.icons.filled.Close
import androidx.compose.material3.Icon
import androidx.compose.material3.IconButton
import androidx.compose.material3.OutlinedTextField
import androidx.compose.material3.Text
import androidx.compose.runtime.Composable
import androidx.compose.runtime.remember
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.platform.LocalContext
import java.time.LocalDate
import java.time.LocalDateTime
import java.time.OffsetDateTime
import java.time.ZoneId
import java.time.ZonedDateTime
import java.time.format.DateTimeFormatter

private val homeScoutDateZone: ZoneId = ZoneId.of("Africa/Nairobi")
private val dateInputFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("dd-MM-yyyy")
private val dateTimeInputFormatter: DateTimeFormatter = DateTimeFormatter.ofPattern("dd-MM-yyyy · HH:mm")

/** Date values stay ISO (yyyy-MM-dd) for the API; users see day-month-year. */
@Composable
fun HomeScoutDateField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    allowClear: Boolean = false,
    enabled: Boolean = true,
) {
    val context = LocalContext.current
    val date = remember(value) { parseLocalDate(value) }
    val displayValue = date?.format(dateInputFormatter).orEmpty()

    OutlinedTextField(
        value = displayValue,
        onValueChange = {},
        modifier = modifier,
        label = { Text(label) },
        readOnly = true,
        enabled = enabled,
        singleLine = true,
        trailingIcon = {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.End) {
                if (allowClear && value.isNotBlank()) {
                    IconButton(onClick = { onValueChange("") }, enabled = enabled) {
                        Icon(Icons.Filled.Close, contentDescription = "Clear date")
                    }
                }
                IconButton(
                    onClick = {
                        val initial = date ?: LocalDate.now(homeScoutDateZone)
                        DatePickerDialog(
                            context,
                            { _, year, month, day ->
                                onValueChange(LocalDate.of(year, month + 1, day).toString())
                            },
                            initial.year,
                            initial.monthValue - 1,
                            initial.dayOfMonth,
                        ).show()
                    },
                    enabled = enabled,
                ) {
                    Icon(Icons.Filled.CalendarMonth, contentDescription = "Choose date")
                }
            }
        },
    )
}

/** Date-time values stay ISO-8601 with the Nairobi offset for the API. */
@Composable
fun HomeScoutDateTimeField(
    value: String,
    onValueChange: (String) -> Unit,
    label: String,
    modifier: Modifier = Modifier,
    allowClear: Boolean = false,
    enabled: Boolean = true,
) {
    val context = LocalContext.current
    val dateTime = remember(value) { parseDateTime(value) }
    val displayValue = dateTime?.format(dateTimeInputFormatter).orEmpty()

    OutlinedTextField(
        value = displayValue,
        onValueChange = {},
        modifier = modifier,
        label = { Text(label) },
        readOnly = true,
        enabled = enabled,
        singleLine = true,
        trailingIcon = {
            Row(verticalAlignment = Alignment.CenterVertically, horizontalArrangement = Arrangement.End) {
                if (allowClear && value.isNotBlank()) {
                    IconButton(onClick = { onValueChange("") }, enabled = enabled) {
                        Icon(Icons.Filled.Close, contentDescription = "Clear date and time")
                    }
                }
                IconButton(
                    onClick = {
                        val initial = dateTime ?: LocalDateTime.now(homeScoutDateZone)
                            .plusDays(1).withHour(10).withMinute(0).withSecond(0).withNano(0)
                        DatePickerDialog(
                            context,
                            { _, year, month, day ->
                                val pickedDate = LocalDate.of(year, month + 1, day)
                                TimePickerDialog(
                                    context,
                                    { _, hour, minute ->
                                        onValueChange(
                                            pickedDate.atTime(hour, minute)
                                                .atZone(homeScoutDateZone)
                                                .toOffsetDateTime()
                                                .withSecond(0)
                                                .withNano(0)
                                                .format(DateTimeFormatter.ISO_OFFSET_DATE_TIME),
                                        )
                                    },
                                    initial.hour,
                                    initial.minute,
                                    true,
                                ).show()
                            },
                            initial.year,
                            initial.monthValue - 1,
                            initial.dayOfMonth,
                        ).show()
                    },
                    enabled = enabled,
                ) {
                    Icon(Icons.Filled.CalendarMonth, contentDescription = "Choose date and time")
                }
            }
        },
    )
}

private fun parseLocalDate(value: String): LocalDate? = runCatching {
    LocalDate.parse(value.take(10))
}.getOrNull()

private fun parseDateTime(value: String): LocalDateTime? = runCatching {
    OffsetDateTime.parse(value).atZoneSameInstant(homeScoutDateZone).toLocalDateTime()
}.recoverCatching {
    ZonedDateTime.parse(value).withZoneSameInstant(homeScoutDateZone).toLocalDateTime()
}.recoverCatching {
    LocalDateTime.parse(value).atZone(homeScoutDateZone).toLocalDateTime()
}.getOrNull()
