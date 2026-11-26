package ke.co.homescout.features.home

data class DemoProperty(
    val title: String,
    val area: String,
    val price: Int,
    val beds: Int,
    val type: String,
    val photo: String,
    val featured: Boolean = false
)

private const val unsplash = "https://images.unsplash.com/"

val demoProperties = listOf(
    DemoProperty("Sunlit two-bedroom apartment", "Kilimani, Nairobi", 68_000, 2, "Apartment", unsplash + "photo-1600607687939-ce8a6c25118c?auto=format&fit=crop&w=1200&q=82", true),
    DemoProperty("Quiet garden bedsitter", "Lavington, Nairobi", 32_000, 1, "Bedsitter", unsplash + "photo-1600566753086-00f18fb6b3ea?auto=format&fit=crop&w=1200&q=82"),
    DemoProperty("Modern family townhouse", "Ruaka, Kiambu", 95_000, 3, "Townhouse", unsplash + "photo-1600585154340-be6161a56a0c?auto=format&fit=crop&w=1200&q=82")
)

val popularAreas = listOf(
    "Kilimani", "Westlands", "Kileleshwa", "Lavington", "Parklands", "Karen",
    "Ruaka", "Ruiru", "Syokimau", "South B", "South C", "Kasarani", "Nyali",
    "Nakuru", "Kisumu", "Eldoret", "Ngong"
)
