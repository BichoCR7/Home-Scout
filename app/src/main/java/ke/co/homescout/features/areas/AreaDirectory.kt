package ke.co.homescout.features.areas

/** Local reference fallback for area browsing when the HomeScout API is unavailable. */
internal object AreaDirectory {
    data class County(val code: String, val name: String, val headquarters: String, val extraTowns: List<String> = emptyList())
    data class Town(val name: String, val neighbourhoods: List<String> = emptyList())
    data class Path(val name: String, val county: County, val town: String? = null, val neighbourhood: String? = null)

    val counties = listOf(
        County("01", "Mombasa", "Mombasa City"),
        County("02", "Kwale", "Kwale"),
        County("03", "Kilifi", "Kilifi"),
        County("04", "Tana River", "Hola"),
        County("05", "Lamu", "Lamu"),
        County("06", "Taita-Taveta", "Mwatate"),
        County("07", "Garissa", "Garissa"),
        County("08", "Wajir", "Wajir"),
        County("09", "Mandera", "Mandera"),
        County("10", "Marsabit", "Marsabit"),
        County("11", "Isiolo", "Isiolo"),
        County("12", "Meru", "Meru"),
        County("13", "Tharaka-Nithi", "Kathwana"),
        County("14", "Embu", "Embu"),
        County("15", "Kitui", "Kitui"),
        County("16", "Machakos", "Machakos Town", listOf("Athi River", "Mlolongo", "Syokimau")),
        County("17", "Makueni", "Wote"),
        County("18", "Nyandarua", "Ol Kalou"),
        County("19", "Nyeri", "Nyeri"),
        County("20", "Kirinyaga", "Kerugoya", listOf("Kutus")),
        County("21", "Murang'a", "Murang'a"),
        County("22", "Kiambu", "Kiambu Town", listOf("Ruiru", "Thika", "Juja", "Kikuyu", "Limuru", "Githunguri", "Ruaka", "Ndenderu")),
        County("23", "Turkana", "Lodwar"),
        County("24", "West Pokot", "Kapenguria"),
        County("25", "Samburu", "Maralal"),
        County("26", "Trans Nzoia", "Kitale"),
        County("27", "Uasin Gishu", "Eldoret", listOf("Kapseret")),
        County("28", "Elgeyo-Marakwet", "Iten"),
        County("29", "Nandi", "Kapsabet"),
        County("30", "Baringo", "Kabarnet"),
        County("31", "Laikipia", "Nanyuki"),
        County("32", "Nakuru", "Nakuru", listOf("Naivasha", "Gilgil")),
        County("33", "Narok", "Narok"),
        County("34", "Kajiado", "Kajiado", listOf("Kitengela", "Ngong", "Kiserian", "Ongata Rongai")),
        County("35", "Kericho", "Kericho"),
        County("36", "Bomet", "Bomet"),
        County("37", "Kakamega", "Kakamega"),
        County("38", "Vihiga", "Vihiga"),
        County("39", "Bungoma", "Bungoma"),
        County("40", "Busia", "Busia"),
        County("41", "Siaya", "Siaya"),
        County("42", "Kisumu", "Kisumu City"),
        County("43", "Homa Bay", "Homa Bay"),
        County("44", "Migori", "Migori"),
        County("45", "Kisii", "Kisii"),
        County("46", "Nyamira", "Nyamira"),
        County("47", "Nairobi City", "Nairobi", listOf("Nairobi"))
    )

    fun towns(county: County): List<Town> {
        val names = listOf(county.headquarters) + county.extraTowns
        return names.distinct().map { name -> Town(name, neighbourhoods(county.code, name)) }
    }

    fun search(query: String): List<Path> {
        val needle = query.trim().lowercase()
        if (needle.length < 2) return emptyList()
        return counties.flatMap { county ->
            towns(county).flatMap { town ->
                buildList {
                    if (listOf(town.name, county.name).any { it.contains(needle) }) {
                        add(Path(town.name, county, town.name))
                    }
                    town.neighbourhoods.filter { it.contains(needle, ignoreCase = true) }.forEach { area ->
                        add(Path(area, county, town.name, area))
                    }
                }
            }
        }.distinctBy { listOf(it.county.code, it.town.orEmpty(), it.neighbourhood.orEmpty()) }
    }

    private fun neighbourhoods(countyCode: String, town: String): List<String> = when {
        countyCode == "47" -> listOf(
            "Westlands", "Kilimani", "Kileleshwa", "Lavington", "Karen", "Runda", "Parklands", "Ngara",
            "South C", "South B", "Langata", "Kasarani", "Roysambu", "Embakasi", "Umoja", "Donholm",
            "Upper Hill", "Hurlingham", "Gigiri", "Ridgeways", "Eastleigh", "Kawangware", "Imara Daima"
        )
        countyCode == "01" -> listOf("Nyali", "Bamburi", "Mombasa Island", "Tudor", "Shanzu", "Likoni")
        countyCode == "42" -> listOf("Milimani", "Mamboleo")
        countyCode == "32" && town == "Nakuru" -> listOf("Milimani", "Section 58", "London")
        countyCode == "27" && town == "Eldoret" -> listOf("Elgon View", "Langas", "Huruma", "Kapsoya", "Pioneer")
        countyCode == "34" && town == "Ngong" -> listOf("Oloolua", "Olkeri")
        countyCode == "22" && town == "Ruiru" -> listOf("Kahawa Sukari", "Mwihoko")
        countyCode == "22" && town == "Thika" -> listOf("Kamenu", "Township")
        countyCode == "34" && town == "Kitengela" -> listOf("Acacia Estate")
        else -> emptyList()
    }
}
